#!/usr/bin/env python3
"""Generate reproducible, causally related server-health telemetry.

This is an educational scenario simulator, not a digital twin of a named server
model or a substitute for validation on real infrastructure.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


FIELDS = [
    "timestamp", "server_id", "split", "cpu_pct", "memory_pct", "disk_pct",
    "net_in_mbps", "net_out_mbps", "temperature_c", "power_w", "load_1m",
    "response_ms", "error_rate_pct", "service_up", "active_sessions",
    "condition_label", "fault_type", "recommended_action", "scenario_id",
    "cpu_next_15m_pct", "memory_next_15m_pct",
]

FAULTS = (
    "cpu_stress", "memory_leak", "disk_saturation", "network_storm",
    "cooling_fault", "service_failure",
)


@dataclass(frozen=True)
class Episode:
    scenario_id: str
    server_id: str
    kind: str
    start_step: int
    end_step: int
    severity: float


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def split_for(step: int, total_steps: int) -> str:
    fraction = step / total_steps
    if fraction < 10 / 14:
        return "train"
    if fraction < 12 / 14:
        return "validation"
    return "test"


def build_episodes(
    rng: random.Random, server_ids: list[str], total_steps: int
) -> list[Episode]:
    """Place every fault type in every temporal split without overlap per server."""
    boundaries = [
        (0.08, 0.68, "train"),
        (0.73, 0.84, "validation"),
        (0.87, 0.97, "test"),
    ]
    episodes: list[Episode] = []
    occupied: dict[str, list[tuple[int, int]]] = {sid: [] for sid in server_ids}
    counter = 1

    for low_f, high_f, _ in boundaries:
        for fault in FAULTS:
            duration = max(20, int(total_steps * rng.uniform(0.002, 0.004)))
            for _attempt in range(500):
                server_id = rng.choice(server_ids)
                low = int(total_steps * low_f)
                high = max(low + 1, int(total_steps * high_f) - duration)
                start = rng.randint(low, high)
                end = start + duration
                if all(end + 10 < a or start - 10 > b for a, b in occupied[server_id]):
                    occupied[server_id].append((start, end))
                    episodes.append(Episode(
                        f"SCN-{counter:03d}", server_id, fault, start, end,
                        rng.uniform(0.82, 1.0),
                    ))
                    counter += 1
                    break
            else:
                raise RuntimeError("Could not place non-overlapping scenarios")
    return episodes


def episode_at(
    episode_index: dict[tuple[str, int], Episode], server_id: str, step: int
) -> Episode | None:
    return episode_index.get((server_id, step))


def classify_no_fault(cpu: float, memory: float, latency: float, sessions: int) -> str:
    # Operational envelopes, not universal hardware limits. They intentionally
    # create learnable quiet and pressure regimes around the simulated baseline.
    if cpu < 30 and memory < 46 and sessions < 145:
        return "underutilized"
    if cpu >= 70 or memory >= 74 or latency >= 150:
        return "overloaded"
    return "normal"


def action_for(condition: str, fault: str) -> str:
    if fault == "service_failure":
        return "restart_service"
    if fault == "cooling_fault":
        return "increase_cooling_and_alert"
    if fault == "disk_saturation":
        return "clear_disk_and_alert"
    if fault == "network_storm":
        return "rate_limit_and_inspect_network"
    if fault in {"cpu_stress", "memory_leak"}:
        return "isolate_process_and_redistribute"
    if condition == "overloaded":
        return "redistribute_or_start_standby"
    if condition == "underutilized":
        return "candidate_for_consolidation"
    return "none"


def generate_rows(
    *, days: int, interval_seconds: int, server_count: int, seed: int,
    start: datetime,
) -> tuple[list[dict[str, object]], list[Episode]]:
    rng = random.Random(seed)
    total_steps = days * 24 * 60 * 60 // interval_seconds
    server_ids = [f"srv-{index:02d}" for index in range(1, server_count + 1)]
    episodes = build_episodes(rng, server_ids, total_steps)
    episode_index: dict[tuple[str, int], Episode] = {}
    for episode in episodes:
        for step in range(episode.start_step, episode.end_step + 1):
            episode_index[(episode.server_id, step)] = episode

    states = {
        sid: {
            "cpu_noise": rng.uniform(-2, 2),
            "mem_noise": rng.uniform(-1, 1),
            "disk": rng.uniform(36, 61),
            "heterogeneity": rng.uniform(0.88, 1.12),
        }
        for sid in server_ids
    }
    rows: list[dict[str, object]] = []

    for step in range(total_steps):
        timestamp = start + timedelta(seconds=step * interval_seconds)
        hour = timestamp.hour + timestamp.minute / 60
        daily = (math.sin(2 * math.pi * (hour - 8) / 24) + 1) / 2
        workday = 1.0 if timestamp.weekday() < 5 else 0.72
        # A repeatable legitimate demand surge occurs twice daily.
        surge = max(0.0, 1 - abs(hour - 11.5) / 1.1) + max(0.0, 1 - abs(hour - 19.0) / 0.8)
        shared_demand = clamp(0.18 + 0.55 * daily * workday + 0.34 * surge, 0, 1.25)

        for server_index, server_id in enumerate(server_ids):
            state = states[server_id]
            state["cpu_noise"] = 0.88 * state["cpu_noise"] + rng.gauss(0, 2.4)
            state["mem_noise"] = 0.96 * state["mem_noise"] + rng.gauss(0, 0.55)
            balance = 0.90 + 0.07 * server_index
            sessions = max(0, round(35 + 390 * shared_demand * balance + rng.gauss(0, 13)))
            cpu = 7 + 68 * shared_demand * balance * state["heterogeneity"] + state["cpu_noise"]
            memory = 25 + 48 * shared_demand * balance + state["mem_noise"]
            net_in = max(0, 8 + sessions * rng.uniform(0.20, 0.31) + rng.gauss(0, 4))
            net_out = max(0, 5 + sessions * rng.uniform(0.09, 0.16) + rng.gauss(0, 2))
            state["disk"] += rng.uniform(0.0001, 0.0007) * interval_seconds / 60
            disk = state["disk"]
            service_up = 1
            error_rate = clamp(rng.lognormvariate(-3.2, 0.45), 0, 2)
            fault = "none"
            scenario_id = "none"

            episode = episode_at(episode_index, server_id, step)
            if episode:
                fault = episode.kind
                scenario_id = episode.scenario_id
                progress = (step - episode.start_step) / max(1, episode.end_step - episode.start_step)
                strength = episode.severity * math.sin(math.pi * clamp(progress, 0, 1)) ** 0.35
                if fault == "cpu_stress":
                    cpu += 62 * strength
                    error_rate += 3.5 * strength
                elif fault == "memory_leak":
                    memory += 67 * episode.severity * progress
                    error_rate += 2.0 * strength
                elif fault == "disk_saturation":
                    disk += 58 * episode.severity * progress
                    error_rate += 2.8 * strength
                elif fault == "network_storm":
                    net_in += 760 * strength
                    net_out += 410 * strength
                    error_rate += 5.0 * strength
                elif fault == "cooling_fault":
                    # Temperature is raised below, after the normal thermal model.
                    pass
                elif fault == "service_failure":
                    service_up = 0 if progress > 0.12 else 1
                    error_rate += 75 * strength

            cpu = clamp(cpu, 0, 100)
            memory = clamp(memory, 0, 100)
            disk = clamp(disk, 0, 100)
            power = clamp(92 + 1.58 * cpu + 0.18 * memory + rng.gauss(0, 3), 75, 285)
            temperature = 32 + 0.40 * cpu + 0.035 * power + rng.gauss(0, 1.2)
            if episode and fault == "cooling_fault":
                progress = (step - episode.start_step) / max(1, episode.end_step - episode.start_step)
                strength = episode.severity * math.sin(math.pi * clamp(progress, 0, 1)) ** 0.35
                temperature += 32 * strength
                error_rate += 2.2 * strength
            temperature = clamp(temperature, 22, 105)
            load_1m = clamp(cpu / 100 * 8 + rng.gauss(0, 0.25), 0, 16)
            resource_pressure = max(0, cpu - 72) ** 1.45 + max(0, memory - 82) ** 1.55
            latency = 28 + 0.10 * sessions + 0.42 * resource_pressure + rng.lognormvariate(1.6, 0.35)
            if not service_up:
                latency = max(latency, 1800 + rng.uniform(0, 700))
            latency = clamp(latency, 1, 5000)
            error_rate = clamp(error_rate, 0, 100)

            condition = "anomalous" if fault != "none" else classify_no_fault(
                cpu, memory, latency, sessions
            )
            rows.append({
                "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
                "server_id": server_id,
                "split": split_for(step, total_steps),
                "cpu_pct": round(cpu, 2),
                "memory_pct": round(memory, 2),
                "disk_pct": round(disk, 2),
                "net_in_mbps": round(net_in, 2),
                "net_out_mbps": round(net_out, 2),
                "temperature_c": round(temperature, 2),
                "power_w": round(power, 2),
                "load_1m": round(load_1m, 2),
                "response_ms": round(latency, 2),
                "error_rate_pct": round(error_rate, 3),
                "service_up": service_up,
                "active_sessions": sessions,
                "condition_label": condition,
                "fault_type": fault,
                "recommended_action": action_for(condition, fault),
                "scenario_id": scenario_id,
                "cpu_next_15m_pct": "",
                "memory_next_15m_pct": "",
            })

    horizon = max(1, round(15 * 60 / interval_seconds))
    by_server: dict[str, list[int]] = {sid: [] for sid in server_ids}
    for index, row in enumerate(rows):
        by_server[str(row["server_id"])].append(index)
    for indices in by_server.values():
        for position, index in enumerate(indices[:-horizon]):
            future = rows[indices[position + horizon]]
            # Do not create a future target across a split boundary.
            if rows[index]["split"] == future["split"]:
                rows[index]["cpu_next_15m_pct"] = future["cpu_pct"]
                rows[index]["memory_next_15m_pct"] = future["memory_pct"]
    return rows, episodes


def write_csv(path: Path, rows: Iterable[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--interval-seconds", type=int, default=60)
    parser.add_argument("--servers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=1107)
    parser.add_argument("--start", default="2026-01-01T00:00:00+00:00")
    parser.add_argument("--output", type=Path, default=Path("data/server_health_synthetic.csv"))
    parser.add_argument("--manifest", type=Path, default=Path("data/scenario_manifest.csv"))
    args = parser.parse_args()
    if args.days < 1 or args.interval_seconds < 1 or args.servers < 2:
        parser.error("days and interval must be positive; at least two servers are required")
    start = datetime.fromisoformat(args.start.replace("Z", "+00:00"))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    rows, episodes = generate_rows(
        days=args.days, interval_seconds=args.interval_seconds,
        server_count=args.servers, seed=args.seed, start=start,
    )
    write_csv(args.output, rows, FIELDS)
    write_csv(args.manifest, (
        {
            "scenario_id": episode.scenario_id,
            "server_id": episode.server_id,
            "fault_type": episode.kind,
            "start_step": episode.start_step,
            "end_step": episode.end_step,
            "severity": round(episode.severity, 4),
        }
        for episode in episodes
    ), ["scenario_id", "server_id", "fault_type", "start_step", "end_step", "severity"])
    print(f"Wrote {len(rows):,} rows to {args.output}")
    print(f"Wrote {len(episodes)} fault episodes to {args.manifest}")


if __name__ == "__main__":
    main()
