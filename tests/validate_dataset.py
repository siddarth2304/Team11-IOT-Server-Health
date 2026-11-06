#!/usr/bin/env python3
"""Fail-fast integrity checks for the generated default dataset."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path


DATASET = Path("data/server_health_synthetic.csv")
REQUIRED_CONDITIONS = {"underutilized", "normal", "overloaded", "anomalous"}
REQUIRED_FAULTS = {
    "cpu_stress", "memory_leak", "disk_saturation", "network_storm",
    "cooling_fault", "service_failure",
}


def between(row: dict[str, str], key: str, low: float, high: float) -> None:
    value = float(row[key])
    assert low <= value <= high, f"{key}={value} outside [{low}, {high}]"


def main() -> None:
    assert DATASET.exists(), f"Generate {DATASET} first"
    conditions = Counter()
    conditions_by_split: dict[str, Counter[str]] = defaultdict(Counter)
    faults_by_split: dict[str, set[str]] = defaultdict(set)
    timestamps: dict[str, list[str]] = defaultdict(list)
    count = 0
    with DATASET.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            count += 1
            for key in ("cpu_pct", "memory_pct", "disk_pct", "error_rate_pct"):
                between(row, key, 0, 100)
            between(row, "temperature_c", 20, 110)
            for key in ("net_in_mbps", "net_out_mbps", "power_w", "load_1m", "response_ms"):
                assert float(row[key]) >= 0, f"{key} must be nonnegative"
            assert row["service_up"] in {"0", "1"}
            assert (row["fault_type"] != "none") == (row["condition_label"] == "anomalous")
            conditions[row["condition_label"]] += 1
            conditions_by_split[row["split"]][row["condition_label"]] += 1
            if row["fault_type"] != "none":
                faults_by_split[row["split"]].add(row["fault_type"])
            timestamps[row["server_id"]].append(row["timestamp"])

    assert count > 0
    assert REQUIRED_CONDITIONS <= conditions.keys(), conditions
    # Each class must be large enough to train and evaluate a classroom model.
    for condition in REQUIRED_CONDITIONS:
        assert conditions[condition] >= max(100, count // 100), (condition, conditions[condition])
    for split in ("train", "validation", "test"):
        assert REQUIRED_CONDITIONS <= conditions_by_split[split].keys(), (
            split, conditions_by_split[split]
        )
        assert REQUIRED_FAULTS <= faults_by_split[split], (split, faults_by_split[split])
    for server_id, values in timestamps.items():
        assert values == sorted(values), f"timestamps out of order for {server_id}"
        assert len(values) == len(set(values)), f"duplicate timestamps for {server_id}"

    print(f"Validated {count:,} rows")
    print("Conditions:", dict(conditions))
    print("Fault coverage:", {key: sorted(value) for key, value in faults_by_split.items()})


if __name__ == "__main__":
    main()
