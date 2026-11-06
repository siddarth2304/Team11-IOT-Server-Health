#!/usr/bin/env python3
"""Safe software actuator: acknowledge commands without changing a real server."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from server_health.actuator import simulate_action
from server_health.mqtt import create_client


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    args = parser.parse_args()

    def on_connect(client, userdata, flags, reason_code, properties):
        client.subscribe("team11/servers/+/command")
        print("Software actuator ready")

    def on_message(client, userdata, message):
        command = json.loads(message.payload)
        status, before, after = simulate_action(command)
        acknowledgement = {
            "command_id": command["command_id"], "server_id": command["server_id"],
            "action": command["action"], "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "note": "No physical or production server was modified",
            "pre_action_state": before,
            "post_action_state": after,
            "expected_effect": command.get("expected_effect"),
        }
        client.publish(f"team11/servers/{command['server_id']}/ack", json.dumps(acknowledgement, separators=(",", ":")))
        print(json.dumps(acknowledgement))

    client = create_client("team11-actuator", args.host, args.port)
    client.on_connect, client.on_message = on_connect, on_message
    client.connect(args.host, args.port, 60)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Stopping software actuator")


if __name__ == "__main__":
    main()
