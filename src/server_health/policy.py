"""Auditable safety policy that maps predictions to non-destructive actions."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid


def decide(telemetry: dict[str, object], condition: str, confidence: float) -> dict[str, object]:
    cpu = float(telemetry["cpu_pct"])
    memory = float(telemetry["memory_pct"])
    disk = float(telemetry["disk_pct"])
    temperature = float(telemetry["temperature_c"])
    net_in = float(telemetry["net_in_mbps"])
    errors = float(telemetry["error_rate_pct"])
    service_up = int(telemetry["service_up"])

    action, reason, severity = "none", "Metrics inside operating envelope", "info"
    # Safety-critical sensor rules take priority over a statistical prediction.
    if service_up == 0:
        action, reason, severity = "restart_service", "Service heartbeat is down", "critical"
    elif temperature >= 82:
        action, reason, severity = "increase_cooling_and_alert", f"Temperature is {temperature:.1f}°C", "critical"
    elif disk >= 92:
        action, reason, severity = "clear_disk_and_alert", f"Disk usage is {disk:.1f}%", "critical"
    elif net_in >= 600:
        action, reason, severity = "rate_limit_and_inspect_network", f"Inbound traffic is {net_in:.1f} Mbit/s", "warning"
    elif errors >= 12:
        action, reason, severity = "isolate_process_and_redistribute", f"Error rate is {errors:.1f}%", "critical"
    elif condition == "anomalous":
        action, reason, severity = "inspect_and_redistribute", f"ML anomaly confidence is {confidence:.1%}", "warning"
    elif condition == "overloaded" or cpu >= 85 or memory >= 88:
        action, reason, severity = "redistribute_or_start_standby", f"Resource pressure: CPU {cpu:.1f}%, memory {memory:.1f}%", "warning"
    elif condition == "underutilized" and cpu < 25 and memory < 45:
        action, reason = "candidate_for_consolidation", f"Low usage: CPU {cpu:.1f}%, memory {memory:.1f}%"

    expected_effects = {
        "restart_service": "Restore heartbeat and reduce error rate/latency",
        "increase_cooling_and_alert": "Reduce temperature while alerting an operator",
        "clear_disk_and_alert": "Release simulated disk capacity after approval",
        "rate_limit_and_inspect_network": "Reduce abnormal network throughput",
        "isolate_process_and_redistribute": "Reduce CPU, memory and error pressure",
        "inspect_and_redistribute": "Investigate anomaly and reduce resource pressure",
        "redistribute_or_start_standby": "Reduce utilization and response latency",
        "candidate_for_consolidation": "Potential energy saving after operator approval",
        "none": "No state change",
    }
    return {
        "command_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "server_id": telemetry["server_id"],
        "action": action,
        "reason": reason,
        "severity": severity,
        "requires_operator_approval": action in {"candidate_for_consolidation", "clear_disk_and_alert"},
        "cooldown_seconds": 300,
        "observed_state": {
            key: telemetry[key] for key in (
                "cpu_pct", "memory_pct", "disk_pct", "net_in_mbps",
                "temperature_c", "response_ms", "error_rate_pct", "service_up",
            )
        },
        "expected_effect": expected_effects[action],
    }
