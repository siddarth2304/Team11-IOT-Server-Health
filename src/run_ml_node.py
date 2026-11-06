#!/usr/bin/env python3
"""Run the analytics subscriber and network-visible dashboard on Laptop 2."""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
from pathlib import Path

from server_health.mqtt import connection_label

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", required=True, help="IP address of Laptop 1 running Mosquitto")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--dashboard-port", type=int, default=8080)
    parser.add_argument("--database", type=Path, default=ROOT / "output" / "server_health.db")
    args = parser.parse_args()

    try:
        with socket.create_connection((args.broker, args.mqtt_port), timeout=3):
            pass
    except OSError as exc:
        raise SystemExit(
            f"Cannot reach MQTT broker at {args.broker}:{args.mqtt_port}. "
            "Check the broker hostname, internet/network connection and firewall."
        ) from exc

    commands = [
        [sys.executable, str(ROOT / "src" / "mqtt_processor.py"), "--host", args.broker, "--port", str(args.mqtt_port), "--database", str(args.database)],
        [sys.executable, str(ROOT / "src" / "dashboard.py"), "--host", "0.0.0.0", "--port", str(args.dashboard_port), "--database", str(args.database)],
    ]
    processes = [subprocess.Popen(command, cwd=ROOT) for command in commands]
    print(f"ML node connected to {connection_label(args.broker, args.mqtt_port)}")
    print(f"Dashboard available to Laptop 1 at http://<LAPTOP_2_IP>:{args.dashboard_port}")
    print("Press Ctrl+C to stop both services")
    try:
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        failed = next(process for process in processes if process.poll() is not None)
        raise SystemExit(f"A service stopped unexpectedly with exit code {failed.returncode}")
    except KeyboardInterrupt:
        print("Stopping ML node")
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
