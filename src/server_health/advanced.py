"""Advanced, auditable operational analytics for each telemetry message."""

from __future__ import annotations

from collections import deque
import json
from pathlib import Path

from .config import DRIFT_BASELINE_PATH


DRIFT_METRICS = ("cpu_pct", "memory_pct", "disk_pct", "net_in_mbps", "temperature_c", "response_ms", "error_rate_pct")


def _bounded(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def operational_assessment(
    telemetry: dict[str, object], condition: str, cpu_15m: float, memory_15m: float
) -> dict[str, object]:
    """Return health, capacity and plain-language local explanations.

    The score is intentionally deterministic and documented. It complements
    the classifier; it is not presented as another trained model.
    """

    cpu = float(telemetry["cpu_pct"])
    memory = float(telemetry["memory_pct"])
    disk = float(telemetry["disk_pct"])
    temperature = float(telemetry["temperature_c"])
    response = float(telemetry["response_ms"])
    errors = float(telemetry["error_rate_pct"])
    service_up = int(telemetry["service_up"])

    penalties = {
        "CPU pressure": _bounded((cpu - 55.0) / 45.0) * 22.0,
        "Memory pressure": _bounded((memory - 60.0) / 40.0) * 20.0,
        "Disk pressure": _bounded((disk - 70.0) / 30.0) * 14.0,
        "Thermal pressure": _bounded((temperature - 58.0) / 32.0) * 18.0,
        "Response latency": _bounded((response - 100.0) / 400.0) * 10.0,
        "Error rate": _bounded((errors - 1.0) / 14.0) * 16.0,
        "Service heartbeat": 45.0 if service_up == 0 else 0.0,
    }
    health_score = 100.0 - min(100.0, sum(penalties.values()))
    if condition == "overloaded":
        health_score = min(health_score, 70.0)
    elif condition == "anomalous":
        health_score = min(health_score, 45.0)
    if service_up == 0:
        health_score = min(health_score, 20.0)

    if service_up == 0 or health_score < 35:
        risk_level = "critical"
    elif condition == "anomalous" or health_score < 55:
        risk_level = "high"
    elif condition == "overloaded" or health_score < 78:
        risk_level = "medium"
    else:
        risk_level = "low"

    capacity_headroom = _bounded(100.0 - max(float(cpu_15m), float(memory_15m), disk))
    explanations = []
    factor_values = {
        "CPU pressure": f"{cpu:.1f}% CPU",
        "Memory pressure": f"{memory:.1f}% memory",
        "Disk pressure": f"{disk:.1f}% disk",
        "Thermal pressure": f"{temperature:.1f}°C",
        "Response latency": f"{response:.1f} ms",
        "Error rate": f"{errors:.1f}% errors",
        "Service heartbeat": "service down",
    }
    for factor, penalty in sorted(penalties.items(), key=lambda item: item[1], reverse=True):
        if penalty > 0:
            explanations.append({"factor": factor, "value": factor_values[factor], "impact": round(penalty, 2)})
        if len(explanations) == 3:
            break
    if condition == "underutilized":
        explanations.insert(0, {"factor": "Low resource use", "value": f"CPU {cpu:.1f}%, memory {memory:.1f}%", "impact": 0.0})
    if not explanations:
        explanations.append({"factor": "Stable operating envelope", "value": "No threshold pressure", "impact": 0.0})

    return {
        "health_score": round(health_score, 1),
        "risk_level": risk_level,
        "capacity_headroom_pct": round(capacity_headroom, 1),
        "explanations": explanations[:3],
    }


class DriftMonitor:
    """Detect rolling mean shifts relative to training-only feature baselines."""

    def __init__(self, baseline_path: Path = DRIFT_BASELINE_PATH, window: int = 120, minimum_samples: int = 20):
        self.window = window
        self.minimum_samples = minimum_samples
        self.values = {metric: deque(maxlen=window) for metric in DRIFT_METRICS}
        self.baseline: dict[str, dict[str, float]] = {}
        if baseline_path.exists():
            document = json.loads(baseline_path.read_text(encoding="utf-8"))
            self.baseline = document.get("metrics", {})

    def update(self, telemetry: dict[str, object]) -> dict[str, object]:
        for metric in DRIFT_METRICS:
            self.values[metric].append(float(telemetry[metric]))
        samples = len(self.values[DRIFT_METRICS[0]])
        if not self.baseline or samples < self.minimum_samples:
            return {"score": 0.0, "status": "warming_up", "metric": "none", "samples": samples, "window": self.window}

        scores: dict[str, float] = {}
        for metric in DRIFT_METRICS:
            reference = self.baseline[metric]
            recent_mean = sum(self.values[metric]) / len(self.values[metric])
            scores[metric] = abs(recent_mean - float(reference["mean"])) / max(float(reference["std"]), 1e-6)
        leading_metric = max(scores, key=scores.get)
        score = scores[leading_metric]
        status = "stable" if score < 1.5 else "watch" if score < 2.5 else "drift_detected"
        return {"score": round(score, 3), "status": status, "metric": leading_metric, "samples": samples, "window": self.window}
