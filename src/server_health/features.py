"""Shared feature conversion for training and live inference."""

from __future__ import annotations

import math
from datetime import datetime

from .config import SENSOR_FIELDS

LOG_FIELDS = {"net_in_mbps", "net_out_mbps", "response_ms", "error_rate_pct"}
FEATURE_NAMES = SENSOR_FIELDS + ["hour_sin", "hour_cos", "weekday"]


def feature_vector(row: dict[str, object]) -> list[float]:
    values: list[float] = []
    for name in SENSOR_FIELDS:
        value = float(row[name])
        values.append(math.log1p(max(0.0, value)) if name in LOG_FIELDS else value)
    stamp = datetime.fromisoformat(str(row["timestamp"]).replace("Z", "+00:00"))
    hour = stamp.hour + stamp.minute / 60 + stamp.second / 3600
    angle = 2 * math.pi * hour / 24
    values.extend([math.sin(angle), math.cos(angle), stamp.weekday() / 6])
    return values


def telemetry_payload(row: dict[str, str]) -> dict[str, object]:
    payload: dict[str, object] = {
        "timestamp": row["timestamp"],
        "server_id": row["server_id"],
    }
    for name in SENSOR_FIELDS:
        payload[name] = int(row[name]) if name in {"service_up", "active_sessions"} else float(row[name])
    return payload
