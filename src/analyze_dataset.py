#!/usr/bin/env python3
"""Create reproducible exploratory statistics for workload-pattern analysis."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from server_health.config import DATASET, DRIFT_BASELINE_PATH, ROOT

METRICS = ["cpu_pct", "memory_pct", "temperature_c", "power_w", "response_ms", "net_in_mbps", "active_sessions"]
DRIFT_METRICS = ["cpu_pct", "memory_pct", "disk_pct", "net_in_mbps", "temperature_c", "response_ms", "error_rate_pct"]


def correlation(pairs: list[tuple[float, float]]) -> float:
    n = len(pairs)
    mx = sum(x for x, _ in pairs) / n
    my = sum(y for _, y in pairs) / n
    numerator = sum((x - mx) * (y - my) for x, y in pairs)
    denominator = math.sqrt(sum((x - mx) ** 2 for x, _ in pairs) * sum((y - my) ** 2 for _, y in pairs))
    return numerator / denominator if denominator else 0.0


def main() -> None:
    hourly: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    servers: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    conditions, faults = Counter(), Counter()
    pair_names = [("cpu_pct", "temperature_c"), ("cpu_pct", "power_w"), ("cpu_pct", "response_ms"), ("active_sessions", "net_in_mbps")]
    pairs: dict[tuple[str, str], list[tuple[float, float]]] = {key: [] for key in pair_names}
    drift_values: dict[str, list[float]] = {key: [] for key in DRIFT_METRICS}
    rows = 0
    with DATASET.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows += 1
            hour = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")).hour
            values = {key: float(row[key]) for key in METRICS}
            for key, value in values.items():
                hourly[hour][key].append(value)
                servers[row["server_id"]][key].append(value)
            for key in pair_names:
                pairs[key].append((values[key[0]], values[key[1]]))
            conditions[row["condition_label"]] += 1
            faults[row["fault_type"]] += 1
            if row["split"] == "train":
                for metric in DRIFT_METRICS:
                    drift_values[metric].append(float(row[metric]))

    hourly_rows = []
    for hour in range(24):
        item: dict[str, object] = {"hour_utc": hour, "samples": len(hourly[hour][METRICS[0]])}
        for metric in METRICS:
            values = hourly[hour][metric]
            item[f"avg_{metric}"] = round(sum(values) / len(values), 3)
        hourly_rows.append(item)
    path = ROOT / "output" / "hourly_workload_patterns.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(hourly_rows[0]))
        writer.writeheader(); writer.writerows(hourly_rows)

    profile = {
        "rows": rows,
        "sampling_interval_seconds": 60,
        "condition_distribution": conditions,
        "fault_distribution": faults,
        "correlations": {f"{a}__{b}": round(correlation(value), 4) for (a, b), value in pairs.items()},
        "server_summary": {
            server: {f"mean_{metric}": round(sum(values[metric]) / len(values[metric]), 3) for metric in METRICS}
            for server, values in servers.items()
        },
        "peak_average_cpu_hour_utc": max(hourly_rows, key=lambda item: item["avg_cpu_pct"])["hour_utc"],
        "quietest_average_cpu_hour_utc": min(hourly_rows, key=lambda item: item["avg_cpu_pct"])["hour_utc"],
    }
    out = ROOT / "output" / "dataset_profile.json"
    out.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    drift_baseline = {
        "scope": "chronological training split only",
        "rows": len(drift_values[DRIFT_METRICS[0]]),
        "metrics": {},
    }
    for metric, values in drift_values.items():
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        drift_baseline["metrics"][metric] = {"mean": mean, "std": math.sqrt(variance)}
    DRIFT_BASELINE_PATH.write_text(json.dumps(drift_baseline, indent=2), encoding="utf-8")
    print(f"Saved {out}")
    print(f"Saved {path}")
    print(f"Saved {DRIFT_BASELINE_PATH}")
    print("Peak average CPU hour (UTC):", profile["peak_average_cpu_hour_utc"])
    print("Correlations:", dict(profile["correlations"]))


if __name__ == "__main__":
    main()
