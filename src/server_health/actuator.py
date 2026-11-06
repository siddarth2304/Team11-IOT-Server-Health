"""Deterministic digital-twin response for safe closed-loop demonstrations."""

from __future__ import annotations

from copy import deepcopy


def simulate_action(command: dict[str, object]) -> tuple[str, dict[str, object], dict[str, object]]:
    status = "awaiting_operator" if command.get("requires_operator_approval") else "simulated_success"
    before = deepcopy(command.get("observed_state", {}))
    after = deepcopy(before)
    if status != "simulated_success":
        return status, before, after
    action = command["action"]
    if action == "restart_service":
        after.update(service_up=1, error_rate_pct=min(float(after.get("error_rate_pct", 0)), 0.5), response_ms=min(float(after.get("response_ms", 0)), 80))
    elif action == "increase_cooling_and_alert":
        after["temperature_c"] = max(35, float(after.get("temperature_c", 35)) - 20)
    elif action == "clear_disk_and_alert":
        after["disk_pct"] = max(45, float(after.get("disk_pct", 45)) - 25)
    elif action == "rate_limit_and_inspect_network":
        after["net_in_mbps"] = float(after.get("net_in_mbps", 0)) * 0.45
    elif action in {"isolate_process_and_redistribute", "inspect_and_redistribute", "redistribute_or_start_standby"}:
        after["cpu_pct"] = float(after.get("cpu_pct", 0)) * 0.65
        after["memory_pct"] = float(after.get("memory_pct", 0)) * 0.85
        after["response_ms"] = float(after.get("response_ms", 0)) * 0.70
        after["error_rate_pct"] = float(after.get("error_rate_pct", 0)) * 0.40
    return status, before, after
