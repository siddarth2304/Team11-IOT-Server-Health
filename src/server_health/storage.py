"""SQLite persistence used by the processor and dashboard."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS readings (
 id INTEGER PRIMARY KEY AUTOINCREMENT, event_time TEXT NOT NULL, received_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 server_id TEXT NOT NULL, cpu_pct REAL, memory_pct REAL, disk_pct REAL, net_in_mbps REAL,
 net_out_mbps REAL, temperature_c REAL, power_w REAL, load_1m REAL, response_ms REAL,
 error_rate_pct REAL, service_up INTEGER, active_sessions INTEGER,
 predicted_condition TEXT NOT NULL, confidence REAL NOT NULL,
 predicted_cpu_15m REAL, predicted_memory_15m REAL, action TEXT NOT NULL, reason TEXT NOT NULL,
 health_score REAL, risk_level TEXT, capacity_headroom_pct REAL, explanation_json TEXT,
 drift_score REAL, drift_status TEXT, drift_metric TEXT,
 source TEXT NOT NULL DEFAULT 'synthetic_replay', raw_json TEXT NOT NULL,
 UNIQUE(event_time, server_id)
);
CREATE INDEX IF NOT EXISTS idx_readings_time ON readings(event_time DESC);
CREATE INDEX IF NOT EXISTS idx_readings_server_time ON readings(server_id, event_time DESC);
CREATE TABLE IF NOT EXISTS action_log (
 command_id TEXT PRIMARY KEY, event_time TEXT NOT NULL, server_id TEXT NOT NULL, action TEXT NOT NULL,
 reason TEXT NOT NULL, severity TEXT NOT NULL, requires_operator_approval INTEGER NOT NULL,
 status TEXT NOT NULL DEFAULT 'simulated', command_json TEXT NOT NULL
);
"""


class Storage:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        existing = {row[1] for row in self.connection.execute("PRAGMA table_info(readings)")}
        migrations = {
            "health_score": "REAL", "risk_level": "TEXT", "capacity_headroom_pct": "REAL",
            "explanation_json": "TEXT", "drift_score": "REAL", "drift_status": "TEXT", "drift_metric": "TEXT",
        }
        for column, sql_type in migrations.items():
            if column not in existing:
                self.connection.execute(f"ALTER TABLE readings ADD COLUMN {column} {sql_type}")
        self.connection.commit()

    def store(self, telemetry: dict[str, object], result: dict[str, object], command: dict[str, object]) -> None:
        columns = ["cpu_pct", "memory_pct", "disk_pct", "net_in_mbps", "net_out_mbps", "temperature_c", "power_w", "load_1m", "response_ms", "error_rate_pct", "service_up", "active_sessions"]
        values = [
            telemetry["timestamp"], telemetry["server_id"], *[telemetry[c] for c in columns],
            result["condition"], result["confidence"], result["cpu_15m"], result["memory_15m"],
            command["action"], command["reason"], result["health_score"], result["risk_level"],
            result["capacity_headroom_pct"], json.dumps(result["explanations"], separators=(",", ":")),
            result["drift"]["score"], result["drift"]["status"], result["drift"]["metric"],
            json.dumps(telemetry, separators=(",", ":")),
        ]
        inserted_columns = [
            "event_time", "server_id", *columns, "predicted_condition", "confidence",
            "predicted_cpu_15m", "predicted_memory_15m", "action", "reason", "health_score",
            "risk_level", "capacity_headroom_pct", "explanation_json", "drift_score", "drift_status",
            "drift_metric", "raw_json",
        ]
        self.connection.execute(
            f"INSERT OR REPLACE INTO readings ({','.join(inserted_columns)}) VALUES ({','.join('?' for _ in values)})",
            values,
        )
        if command["action"] != "none":
            self.connection.execute(
                "INSERT OR IGNORE INTO action_log (command_id,event_time,server_id,action,reason,severity,requires_operator_approval,command_json) VALUES (?,?,?,?,?,?,?,?)",
                [command["command_id"], telemetry["timestamp"], telemetry["server_id"], command["action"], command["reason"], command["severity"], int(command["requires_operator_approval"]), json.dumps(command, separators=(",", ":"))],
            )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
