#!/usr/bin/env python3
"""Evaluate command effectiveness, delay, stability and energy-saving potential."""

from __future__ import annotations

import csv
import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from server_health.actuator import simulate_action
from server_health.config import BEST_CLASSIFIER_PATH, DATASET, MODEL_PATH, ROOT
from server_health.features import feature_vector, telemetry_payload
from server_health.policy import decide
from server_health.runtime_model import load_runtime_model


def risk(state: dict[str, object]) -> float:
    return max(
        float(state.get("cpu_pct", 0)) / 85,
        float(state.get("memory_pct", 0)) / 88,
        float(state.get("disk_pct", 0)) / 92,
        float(state.get("temperature_c", 0)) / 82,
        float(state.get("error_rate_pct", 0)) / 12,
        1.5 if int(state.get("service_up", 1)) == 0 else 0,
    )


def stamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> None:
    with DATASET.open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["split"] == "test"]
    scenario_start = {}
    for row in rows:
        if row["scenario_id"] != "none":
            scenario_start.setdefault(row["scenario_id"], stamp(row["timestamp"]))

    commands = Counter(); suppressed = 0; unnecessary = 0; approval = 0
    applied = improved = 0; response_times = []; first_action = {}
    energy_saving_wh = 0.0
    model = load_runtime_model(MODEL_PATH, BEST_CLASSIFIER_PATH)
    telemetry_rows = [telemetry_payload(row) for row in rows]
    inference_start = time.perf_counter()
    if hasattr(model, "estimator"):
        probabilities = model.estimator.predict_proba([feature_vector(row) for row in telemetry_rows])
        labels = [str(label) for label in model.estimator.classes_]
        predictions = [
            (labels[max(range(len(values)), key=lambda i: values[i])], float(max(values)))
            for values in probabilities
        ]
    else:
        predictions = [(model.classify(row)[0], model.classify(row)[1]) for row in telemetry_rows]
    inference_ms_per_row = 1000 * (time.perf_counter() - inference_start) / len(rows)
    last_action: dict[tuple[str, str], datetime] = {}
    for row, telemetry, (condition, confidence) in zip(rows, telemetry_rows, predictions):
        start = time.perf_counter()
        command = decide(telemetry, condition, confidence)
        if command["action"] != "none":
            key = (str(telemetry["server_id"]), str(command["action"]))
            event_time = stamp(str(telemetry["timestamp"]))
            previous = last_action.get(key)
            if previous and (event_time - previous).total_seconds() < int(command["cooldown_seconds"]):
                command["reason"] = f"Cooldown active; suppressed repeated {command['action']} command"
                command["action"] = "none"
                command["requires_operator_approval"] = False
            else:
                last_action[key] = event_time
        response_times.append(inference_ms_per_row + 1000 * (time.perf_counter() - start))
        if "Cooldown active" in command["reason"]:
            suppressed += 1
        if row["condition_label"] == "underutilized":
            # Stated planning assumption: consolidation can avoid 35% of
            # one server's one-minute power draw during quiet operation.
            energy_saving_wh += float(row["power_w"]) / 60 * 0.35
        if command["action"] == "none":
            continue
        commands[command["action"]] += 1
        if row["condition_label"] == "normal":
            unnecessary += 1
        if command["requires_operator_approval"]:
            approval += 1
        scenario = row["scenario_id"]
        if scenario != "none":
            first_action.setdefault(scenario, stamp(row["timestamp"]))
        status, before, after = simulate_action(command)
        if status == "simulated_success":
            applied += 1
            if risk(after) < risk(before) or after != before:
                improved += 1

    delays = [
        (first_action[scenario] - start_time).total_seconds() / 60
        for scenario, start_time in scenario_start.items() if scenario in first_action
    ]
    report = {
        "scope": "Untouched chronological test split; software digital-twin actuator only",
        "test_messages": len(rows),
        "commands_issued": sum(commands.values()),
        "commands_per_1000_messages": 1000 * sum(commands.values()) / len(rows),
        "command_distribution": commands,
        "cooldown_suppressions": suppressed,
        "unnecessary_command_rate_on_normal_rows": unnecessary / sum(1 for row in rows if row["condition_label"] == "normal"),
        "operator_approval_commands": approval,
        "simulated_control_effectiveness": improved / applied if applied else 0,
        "mean_decision_latency_ms": sum(response_times) / len(response_times),
        "p95_decision_latency_ms": sorted(response_times)[int(0.95 * len(response_times))],
        "fault_scenarios_detected": len(first_action),
        "fault_scenarios_total": len(scenario_start),
        "mean_fault_response_minutes": sum(delays) / len(delays) if delays else None,
        "estimated_energy_saving_kwh": energy_saving_wh / 1000,
        "energy_assumption": "35% of per-minute server power is avoidable during ground-truth underutilized intervals",
    }
    path = ROOT / "output" / "closed_loop_evaluation.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Saved {path}")


if __name__ == "__main__":
    main()
