from __future__ import annotations

from datetime import datetime

from .advanced import DriftMonitor, operational_assessment
from .model import ServerHealthModel
from .policy import decide
from .storage import Storage


class MonitoringEngine:
    def __init__(self, model: ServerHealthModel, storage: Storage):
        self.model, self.storage = model, storage
        self.last_action: dict[tuple[str, str], datetime] = {}
        self.drift_monitor = DriftMonitor()

    def process(self, telemetry: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
        condition, confidence, probabilities = self.model.classify(telemetry)
        cpu_15m, memory_15m = self.model.forecast(telemetry)
        result = {"condition": condition, "confidence": confidence, "probabilities": probabilities, "cpu_15m": cpu_15m, "memory_15m": memory_15m}
        result.update(operational_assessment(telemetry, condition, cpu_15m, memory_15m))
        result["drift"] = self.drift_monitor.update(telemetry)
        command = decide(telemetry, condition, confidence)
        if command["action"] != "none":
            key = (str(telemetry["server_id"]), str(command["action"]))
            event_time = datetime.fromisoformat(str(telemetry["timestamp"]).replace("Z", "+00:00"))
            previous = self.last_action.get(key)
            if previous and (event_time - previous).total_seconds() < int(command["cooldown_seconds"]):
                proposed = command["action"]
                command["action"] = "none"
                command["reason"] = f"Cooldown active; suppressed repeated {proposed} command"
                command["severity"] = "info"
                command["requires_operator_approval"] = False
                command["expected_effect"] = "No state change; command suppressed by cooldown"
            else:
                self.last_action[key] = event_time
        self.storage.store(telemetry, result, command)
        return result, command
