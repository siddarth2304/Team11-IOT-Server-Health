#!/usr/bin/env python3
"""Replay the fixed CSV as live IoT telemetry through local or MQTT mode."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from server_health.config import BEST_CLASSIFIER_PATH, DATABASE, DATASET, MODEL_PATH
from server_health.engine import MonitoringEngine
from server_health.features import telemetry_payload
from server_health.mqtt import create_client
from server_health.runtime_model import load_runtime_model
from server_health.storage import Storage


def source_rows(args):
    """Yield ordinary chronological rows or a class-balanced demo stream."""
    if not args.demo_stream:
        with args.dataset.open(newline="", encoding="utf-8") as handle:
            yield from csv.DictReader(handle)
        return

    buckets = {condition: [] for condition in ("underutilized", "normal", "overloaded", "anomalous")}
    with args.dataset.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if args.split != "all" and row["split"] != args.split:
                continue
            buckets[row["condition_label"]].append(row)
    order = ("normal", "overloaded", "normal", "underutilized", "anomalous")
    positions = {condition: 0 for condition in buckets}
    while any(positions[condition] < len(buckets[condition]) for condition in buckets):
        for condition in order:
            position = positions[condition]
            if position < len(buckets[condition]):
                yield buckets[condition][position]
                positions[condition] += 1


def mqtt_client(host: str, port: int):
    client = create_client("team11-replay", host, port)
    client.connect(host, port, 60)
    client.loop_start()
    return client


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("local", "mqtt"), default="local")
    parser.add_argument("--split", choices=("train", "validation", "test", "all"), default="test")
    parser.add_argument("--limit", type=int, default=1000, help="Maximum rows; 0 means all")
    parser.add_argument("--delay", type=float, default=0.0, help="Wall-clock delay between messages")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--database", type=Path, default=DATABASE)
    parser.add_argument("--verbose-actions", action="store_true")
    parser.add_argument("--baseline-model", action="store_true", help="Ignore the selected ensemble model")
    parser.add_argument("--server", help="Replay only one server ID, for example srv-03")
    parser.add_argument("--condition", choices=("underutilized", "normal", "overloaded", "anomalous"), help="Select a ground-truth scenario class; the label is never published")
    parser.add_argument("--fault", choices=("cpu_stress", "memory_leak", "disk_saturation", "network_storm", "cooling_fault", "service_failure"), help="Select one injected scenario; the fault name is never published")
    parser.add_argument("--demo-mix", action="store_true", help="Publish one genuine dataset row per server: two normal, one overloaded and one underutilized")
    parser.add_argument("--demo-stream", action="store_true", help="Interleave genuine normal, overloaded, underutilized and anomalous rows for a visible live demonstration")
    args = parser.parse_args()

    if (args.demo_mix or args.demo_stream) and (args.server or args.condition or args.fault):
        parser.error("demo sampling cannot be combined with --server, --condition or --fault")
    if args.demo_mix and args.demo_stream:
        parser.error("choose either --demo-mix or --demo-stream")

    storage = Storage(args.database) if args.mode == "local" else None
    engine = MonitoringEngine(load_runtime_model(MODEL_PATH, BEST_CLASSIFIER_PATH, not args.baseline_model), storage) if storage else None
    client = mqtt_client(args.host, args.port) if args.mode == "mqtt" else None
    sent = 0
    demo_targets = {"srv-01": "normal", "srv-02": "overloaded", "srv-03": "underutilized", "srv-04": "normal"}
    demo_servers_sent: set[str] = set()
    try:
        for row in source_rows(args):
            if args.split != "all" and row["split"] != args.split:
                continue
            if args.server and row["server_id"] != args.server:
                continue
            if args.condition and row["condition_label"] != args.condition:
                continue
            if args.fault and row["fault_type"] != args.fault:
                continue
            if args.demo_mix:
                server_id = row["server_id"]
                if server_id in demo_servers_sent or demo_targets.get(server_id) != row["condition_label"]:
                    continue
            telemetry = telemetry_payload(row)
            topic = f"team11/servers/{telemetry['server_id']}/telemetry"
            if client:
                client.publish(topic, json.dumps(telemetry, separators=(",", ":")), qos=0)
            else:
                result, command = engine.process(telemetry)
                if sent < 5 or (args.verbose_actions and command["action"] != "none"):
                    print(json.dumps({"topic": topic, "condition": result["condition"], "confidence": round(result["confidence"], 3), "cpu_15m": round(result["cpu_15m"], 1), "action": command["action"]}))
            sent += 1
            if args.demo_mix:
                demo_servers_sent.add(row["server_id"])
            if args.delay:
                time.sleep(args.delay)
            if args.demo_mix and len(demo_servers_sent) == len(demo_targets):
                break
            if args.limit and sent >= args.limit:
                break
    finally:
        if client:
            client.loop_stop()
            client.disconnect()
        if storage:
            storage.close()
    print(f"Processed {sent:,} telemetry messages in {args.mode} mode")


if __name__ == "__main__":
    main()
