#!/usr/bin/env python3
"""Serve the Team 11 dashboard and read-only JSON API."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from server_health.config import CLOSED_LOOP_REPORT_PATH, DATABASE, MODEL_COMPARISON_PATH, REPORT_PATH, ROOT


class DashboardHandler(BaseHTTPRequestHandler):
    database = DATABASE
    static_root = ROOT / "dashboard"

    def send_json(self, value: object, status: int = 200) -> None:
        body = json.dumps(value, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def query(self, sql: str, parameters: list[object] | None = None) -> list[dict[str, object]]:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        try:
            return [dict(row) for row in connection.execute(sql, parameters or [])]
        finally:
            connection.close()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            return self.api(parsed.path, parse_qs(parsed.query))
        relative = "index.html" if parsed.path == "/" else parsed.path.lstrip("/")
        path = (self.static_root / relative).resolve()
        if self.static_root.resolve() not in path.parents and path != self.static_root.resolve():
            return self.send_error(403)
        if not path.is_file():
            return self.send_error(404)
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def api(self, path: str, query: dict[str, list[str]]) -> None:
        try:
            if path == "/api/summary":
                latest = self.query("SELECT * FROM readings WHERE id IN (SELECT MAX(id) FROM readings GROUP BY server_id) ORDER BY server_id")
                counts = self.query("SELECT predicted_condition AS condition, COUNT(*) AS count FROM readings GROUP BY predicted_condition")
                total = self.query("SELECT COUNT(*) AS readings, COUNT(DISTINCT server_id) AS servers, MAX(event_time) AS latest_event FROM readings")[0]
                return self.send_json({"latest_servers": latest, "condition_counts": counts, **total})
            if path == "/api/history":
                server = query.get("server", [""])[0]
                limit = min(1000, max(10, int(query.get("limit", ["240"])[0])))
                where, params = ("WHERE server_id=?", [server]) if server else ("", [])
                rows = self.query(f"SELECT event_time,server_id,cpu_pct,memory_pct,disk_pct,temperature_c,response_ms,predicted_condition,predicted_cpu_15m,predicted_memory_15m FROM readings {where} ORDER BY event_time DESC LIMIT ?", params + [limit])
                return self.send_json(list(reversed(rows)))
            if path == "/api/advanced":
                latest = self.query("SELECT * FROM readings WHERE id IN (SELECT MAX(id) FROM readings GROUP BY server_id)")
                fields = ("cpu_pct", "memory_pct", "disk_pct", "temperature_c", "response_ms", "predicted_condition", "confidence")
                present = sum(sum(row.get(field) is not None for field in fields) for row in latest)
                possible = len(latest) * len(fields)
                drifted = [row for row in latest if row.get("drift_status") == "drift_detected"]
                valid_health = [float(row["health_score"]) for row in latest if row.get("health_score") is not None]
                valid_headroom = [float(row["capacity_headroom_pct"]) for row in latest if row.get("capacity_headroom_pct") is not None]
                leading = max(latest, key=lambda row: float(row.get("drift_score") or 0), default={})
                return self.send_json({
                    "fleet_health_score": sum(valid_health) / len(valid_health) if valid_health else None,
                    "average_headroom_pct": sum(valid_headroom) / len(valid_headroom) if valid_headroom else None,
                    "data_completeness": present / possible if possible else 0,
                    "drift_alerts": len(drifted),
                    "drift_status": leading.get("drift_status", "warming_up"),
                    "drift_score": leading.get("drift_score", 0),
                    "drift_metric": leading.get("drift_metric", "none"),
                })
            if path == "/api/actions":
                return self.send_json(self.query("SELECT event_time,server_id,action,reason,severity,requires_operator_approval,status FROM action_log ORDER BY event_time DESC LIMIT 30"))
            if path == "/api/evaluation":
                return self.send_json(json.loads(REPORT_PATH.read_text(encoding="utf-8")))
            if path == "/api/model-comparison":
                return self.send_json(json.loads(MODEL_COMPARISON_PATH.read_text(encoding="utf-8")))
            if path == "/api/closed-loop":
                return self.send_json(json.loads(CLOSED_LOOP_REPORT_PATH.read_text(encoding="utf-8")))
            return self.send_json({"error": "Unknown endpoint"}, 404)
        except (sqlite3.Error, OSError, ValueError) as exc:
            return self.send_json({"error": str(exc)}, 500)

    def log_message(self, format: str, *args: object) -> None:
        # The browser polls four endpoints every five seconds. Suppress standard
        # access logs so the evaluation terminal remains readable.
        return


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--database", type=Path, default=DATABASE)
    args = parser.parse_args()
    DashboardHandler.database = args.database
    try:
        server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    except OSError as exc:
        if exc.errno == 98:
            raise SystemExit(
                f"Port {args.port} is already in use. The dashboard may already be running. "
                f"Open http://127.0.0.1:{args.port} or choose another port with --port {args.port + 1}."
            ) from None
        raise
    print(f"Dashboard: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
