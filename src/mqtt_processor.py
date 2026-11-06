#!/usr/bin/env python3
"""Subscribe to telemetry, run analytics, store results and publish commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from server_health.config import BEST_CLASSIFIER_PATH, DATABASE, MODEL_PATH
from server_health.engine import MonitoringEngine
from server_health.mqtt import create_client
from server_health.runtime_model import load_runtime_model
from server_health.storage import Storage


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--database", type=Path, default=DATABASE)
    parser.add_argument("--baseline-model", action="store_true", help="Use the dependency-free baseline instead of the selected benchmark winner")
    args = parser.parse_args()
    storage = Storage(args.database)
    engine = MonitoringEngine(load_runtime_model(MODEL_PATH, BEST_CLASSIFIER_PATH, not args.baseline_model), storage)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            raise RuntimeError(f"MQTT connection failed: {reason_code}")
        client.subscribe("team11/servers/+/processed")
        print("Subscribed to team11/servers/+/processed (Node-RED output)")

    def on_message(client, userdata, message):
        try:
            telemetry = json.loads(message.payload)
            result, command = engine.process(telemetry)
            server_id = telemetry["server_id"]
            client.publish(f"team11/servers/{server_id}/prediction", json.dumps(result, separators=(",", ":")))
            if command["action"] != "none":
                client.publish(f"team11/servers/{server_id}/command", json.dumps(command, separators=(",", ":")))
                print(f"{server_id}: {result['condition']} -> {command['action']}")
        except Exception as exc:
            print(f"Rejected message on {message.topic}: {exc}", file=sys.stderr)

    client = create_client("team11-analytics", args.host, args.port)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.host, args.port, 60)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Stopping analytics service")
    finally:
        storage.close()


if __name__ == "__main__":
    main()
