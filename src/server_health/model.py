"""Dependency-free Gaussian classifier and ridge demand forecaster."""

from __future__ import annotations

import json
import math
from pathlib import Path

from .features import feature_vector


class ServerHealthModel:
    def __init__(self, document: dict[str, object]):
        self.document = document
        self.classes = list(document["classifier"]["classes"])

    @classmethod
    def load(cls, path: Path) -> "ServerHealthModel":
        with path.open(encoding="utf-8") as handle:
            return cls(json.load(handle))

    def classify(self, telemetry: dict[str, object]) -> tuple[str, float, dict[str, float]]:
        vector = feature_vector(telemetry)
        classifier = self.document["classifier"]
        scores: dict[str, float] = {}
        for label in self.classes:
            stats = classifier["stats"][label]
            score = math.log(float(classifier["priors"][label]))
            for value, mean, variance in zip(vector, stats["mean"], stats["variance"]):
                variance = max(float(variance), 1e-8)
                score += -0.5 * (math.log(2 * math.pi * variance) + (value - float(mean)) ** 2 / variance)
            scores[label] = score
        peak = max(scores.values())
        probabilities = {key: math.exp(value - peak) for key, value in scores.items()}
        total = sum(probabilities.values())
        probabilities = {key: value / total for key, value in probabilities.items()}
        label = max(probabilities, key=probabilities.get)
        return label, probabilities[label], probabilities

    def forecast(self, telemetry: dict[str, object]) -> tuple[float, float]:
        vector = feature_vector(telemetry)
        result = []
        for target in ("cpu_next_15m_pct", "memory_next_15m_pct"):
            spec = self.document["forecasters"][target]
            standardized = [
                (value - mean) / scale
                for value, mean, scale in zip(vector, spec["feature_mean"], spec["feature_scale"])
            ]
            prediction = spec["intercept"] + sum(
                coefficient * value for coefficient, value in zip(spec["coefficients"], standardized)
            )
            result.append(max(0.0, min(100.0, prediction)))
        return result[0], result[1]
