#!/usr/bin/env python3
"""Train and evaluate dependency-free models using chronological splits."""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from server_health.config import CONDITIONS, DATASET, MODEL_PATH, REPORT_PATH
from server_health.features import FEATURE_NAMES, feature_vector
from server_health.model import ServerHealthModel


def solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Gaussian elimination with pivoting for the small ridge system."""
    augmented = [row[:] + [value] for row, value in zip(matrix, vector)]
    n = len(vector)
    for column in range(n):
        pivot = max(range(column, n), key=lambda row: abs(augmented[row][column]))
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        if abs(divisor) < 1e-12:
            raise ValueError("Singular training matrix")
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(n):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor:
                augmented[row] = [a - factor * b for a, b in zip(augmented[row], augmented[column])]
    return [augmented[row][-1] for row in range(n)]


def moments(vectors: list[list[float]]) -> tuple[list[float], list[float]]:
    count, width = len(vectors), len(vectors[0])
    means = [sum(row[i] for row in vectors) / count for i in range(width)]
    variances = [sum((row[i] - means[i]) ** 2 for row in vectors) / max(1, count - 1) for i in range(width)]
    return means, [max(value, 1e-6) for value in variances]


def train_ridge(rows: list[dict[str, str]], target: str, alpha: float = 2.0) -> dict[str, object]:
    usable = [(feature_vector(row), float(row[target])) for row in rows if row[target]]
    vectors = [item[0] for item in usable]
    means, variances = moments(vectors)
    scales = [math.sqrt(value) for value in variances]
    width = len(means) + 1
    xtx = [[0.0] * width for _ in range(width)]
    xty = [0.0] * width
    for vector, target_value in usable:
        x = [1.0] + [(value - mean) / scale for value, mean, scale in zip(vector, means, scales)]
        for i in range(width):
            xty[i] += x[i] * target_value
            for j in range(i, width):
                xtx[i][j] += x[i] * x[j]
    for i in range(width):
        for j in range(i):
            xtx[i][j] = xtx[j][i]
    for i in range(1, width):
        xtx[i][i] += alpha
    weights = solve(xtx, xty)
    return {"intercept": weights[0], "coefficients": weights[1:], "feature_mean": means, "feature_scale": scales, "training_rows": len(usable), "method": "ridge_linear_regression"}


def metrics_for(actual: list[str], predicted: list[str]) -> dict[str, object]:
    matrix = {label: {other: 0 for other in CONDITIONS} for label in CONDITIONS}
    for truth, guess in zip(actual, predicted):
        matrix[truth][guess] += 1
    per_class = {}
    for label in CONDITIONS:
        tp = matrix[label][label]
        fp = sum(matrix[truth][label] for truth in CONDITIONS if truth != label)
        fn = sum(matrix[label][guess] for guess in CONDITIONS if guess != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0, "support": sum(matrix[label].values())}
    accuracy = sum(matrix[label][label] for label in CONDITIONS) / len(actual)
    macro_f1 = sum(per_class[label]["f1"] for label in CONDITIONS) / len(CONDITIONS)
    normal_total = sum(sum(matrix[label].values()) for label in CONDITIONS if label != "anomalous")
    false_alarms = sum(matrix[label]["anomalous"] for label in CONDITIONS if label != "anomalous")
    return {"accuracy": accuracy, "macro_f1": macro_f1, "anomaly_false_alarm_rate": false_alarms / normal_total, "per_class": per_class, "confusion_matrix": matrix}


def regression_metrics(model: ServerHealthModel, rows: list[dict[str, str]]) -> dict[str, object]:
    errors = {"cpu": [], "memory": []}
    for row in rows:
        if not row["cpu_next_15m_pct"]:
            continue
        cpu, memory = model.forecast(row)
        errors["cpu"].append(cpu - float(row["cpu_next_15m_pct"]))
        errors["memory"].append(memory - float(row["memory_next_15m_pct"]))
    result = {}
    for key, values in errors.items():
        target_name = "cpu_next_15m_pct" if key == "cpu" else "memory_next_15m_pct"
        actual = [float(row[target_name]) for row in rows if row[target_name]]
        mean_actual = sum(actual) / len(actual)
        sse = sum(v * v for v in values)
        sst = sum((value - mean_actual) ** 2 for value in actual)
        result[key] = {"mae": sum(abs(v) for v in values) / len(values), "rmse": math.sqrt(sse / len(values)), "r2": 1 - sse / sst if sst else 0.0, "rows": len(values)}
    return result


def main() -> None:
    with DATASET.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    train = [row for row in rows if row["split"] == "train"]
    grouped: dict[str, list[list[float]]] = defaultdict(list)
    for row in train:
        grouped[row["condition_label"]].append(feature_vector(row))
    stats = {}
    for label in CONDITIONS:
        mean, variance = moments(grouped[label])
        stats[label] = {"mean": mean, "variance": variance, "rows": len(grouped[label])}
    # Equal priors deliberately counter the strong class imbalance. This choice is
    # recorded so that the anomaly and overload classes are not silently ignored.
    document = {
        "schema_version": 1,
        "dataset": str(DATASET.relative_to(DATASET.parents[1])),
        "features": FEATURE_NAMES,
        "classifier": {"method": "gaussian_naive_bayes", "classes": CONDITIONS, "priors": {label: 1 / len(CONDITIONS) for label in CONDITIONS}, "stats": stats},
        "forecasters": {
            "cpu_next_15m_pct": train_ridge(train, "cpu_next_15m_pct"),
            "memory_next_15m_pct": train_ridge(train, "memory_next_15m_pct"),
        },
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.write_text(json.dumps(document, indent=2), encoding="utf-8")
    model = ServerHealthModel(document)
    report: dict[str, object] = {"dataset_rows": len(rows), "train_rows": len(train), "splits": {}, "forecast_test": {}}
    for split in ("validation", "test"):
        split_rows = [row for row in rows if row["split"] == split]
        predicted = [model.classify(row)[0] for row in split_rows]
        report["splits"][split] = metrics_for([row["condition_label"] for row in split_rows], predicted)
    test = [row for row in rows if row["split"] == "test"]
    report["forecast_test"] = regression_metrics(model, test)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved model to {MODEL_PATH}")
    print(f"Saved evaluation to {REPORT_PATH}")
    for split, values in report["splits"].items():
        print(f"{split}: accuracy={values['accuracy']:.3f}, macro_f1={values['macro_f1']:.3f}, false_alarm_rate={values['anomaly_false_alarm_rate']:.3f}")
    print(f"test forecast: CPU MAE={report['forecast_test']['cpu']['mae']:.2f}, memory MAE={report['forecast_test']['memory']['mae']:.2f}")


if __name__ == "__main__":
    main()
