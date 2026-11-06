#!/usr/bin/env python3
"""Compare traditional, ensemble and deep-neural classifiers reproducibly."""

from __future__ import annotations

import csv
import json
import os
import random
import resource
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.naive_bayes import GaussianNB
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from server_health.config import BEST_CLASSIFIER_PATH, CONDITIONS, DATASET, MODEL_COMPARISON_PATH
from server_health.features import FEATURE_NAMES, feature_vector


def evaluate(estimator, x: np.ndarray, y: np.ndarray) -> dict[str, object]:
    start = time.perf_counter()
    predicted = estimator.predict(x)
    elapsed = time.perf_counter() - start
    precision, recall, f1, support = precision_recall_fscore_support(
        y, predicted, labels=CONDITIONS, zero_division=0
    )
    matrix = confusion_matrix(y, predicted, labels=CONDITIONS)
    return {
        "accuracy": float(accuracy_score(y, predicted)),
        "macro_precision": float(np.mean(precision)),
        "macro_recall": float(np.mean(recall)),
        "macro_f1": float(np.mean(f1)),
        "inference_ms_per_record": 1000 * elapsed / len(x),
        "per_class": {
            label: {
                "precision": float(precision[i]), "recall": float(recall[i]),
                "f1": float(f1[i]), "support": int(support[i]),
            }
            for i, label in enumerate(CONDITIONS)
        },
        "confusion_matrix": {
            truth: {guess: int(matrix[i, j]) for j, guess in enumerate(CONDITIONS)}
            for i, truth in enumerate(CONDITIONS)
        },
    }


def balanced_neural_sample(x: np.ndarray, y: np.ndarray, per_class: int = 8000) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(1107)
    selected = []
    for label in CONDITIONS:
        candidates = np.flatnonzero(y == label)
        selected.extend(rng.choice(candidates, size=per_class, replace=len(candidates) < per_class))
    selected = np.asarray(selected)
    rng.shuffle(selected)
    return x[selected], y[selected]


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def main() -> None:
    random.seed(1107); np.random.seed(1107)
    with DATASET.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    split_rows = {name: [row for row in rows if row["split"] == name] for name in ("train", "validation", "test")}
    arrays = {
        name: (
            np.asarray([feature_vector(row) for row in values], dtype=np.float64),
            np.asarray([row["condition_label"] for row in values]),
        )
        for name, values in split_rows.items()
    }
    x_train, y_train = arrays["train"]
    x_neural, y_neural = balanced_neural_sample(x_train, y_train)
    models = [
        ("traditional_gaussian_nb", "Traditional machine learning", GaussianNB(priors=[0.25] * 4), x_train, y_train),
        ("ensemble_random_forest", "Ensemble machine learning", RandomForestClassifier(
            n_estimators=160, max_depth=18, min_samples_leaf=2,
            class_weight="balanced_subsample", n_jobs=-1, random_state=1107,
        ), x_train, y_train),
        ("deep_mlp", "Deep learning (three-hidden-layer MLP)", make_pipeline(
            StandardScaler(),
            MLPClassifier(hidden_layer_sizes=(64, 32, 16), batch_size=256,
                          max_iter=80, early_stopping=True, n_iter_no_change=7,
                          random_state=1107),
        ), x_neural, y_neural),
    ]
    results: dict[str, object] = {}
    saved_candidates: dict[str, Path] = {}
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        for name, family, estimator, fit_x, fit_y in models:
            wall_start, cpu_start = time.perf_counter(), time.process_time()
            estimator.fit(fit_x, fit_y)
            wall_seconds = time.perf_counter() - wall_start
            cpu_seconds = time.process_time() - cpu_start
            model_file = temporary / f"{name}.joblib"
            joblib.dump({"model_name": name, "estimator": estimator, "features": FEATURE_NAMES}, model_file, compress=3)
            saved_candidates[name] = model_file
            results[name] = {
                "family": family,
                "training_rows": len(fit_x),
                "computational_performance": {
                    "training_wall_seconds": wall_seconds,
                    "training_cpu_seconds": cpu_seconds,
                    "process_peak_rss_mb": rss_mb(),
                    "serialized_model_mb": model_file.stat().st_size / (1024 * 1024),
                },
                "validation": evaluate(estimator, *arrays["validation"]),
                "test": evaluate(estimator, *arrays["test"]),
            }
            print(f"{name}: validation macro-F1={results[name]['validation']['macro_f1']:.3f}, test macro-F1={results[name]['test']['macro_f1']:.3f}")

        winner = max(results, key=lambda name: results[name]["validation"]["macro_f1"])
        BEST_CLASSIFIER_PATH.parent.mkdir(parents=True, exist_ok=True)
        bundle = joblib.load(saved_candidates[winner])
        joblib.dump(bundle, BEST_CLASSIFIER_PATH, compress=3)

    report = {
        "selection_rule": "Highest validation macro-F1; test data is not used for selection",
        "selected_model": winner,
        "features": FEATURE_NAMES,
        "models": results,
    }
    MODEL_COMPARISON_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODEL_COMPARISON_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Selected {winner}")
    print(f"Saved {BEST_CLASSIFIER_PATH}")
    print(f"Saved {MODEL_COMPARISON_PATH}")


if __name__ == "__main__":
    main()
