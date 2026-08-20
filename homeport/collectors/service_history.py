"""Historique des états de service — la matière première de « 99,8 % sur 7 jours ».

Un échantillon par service par minute (job de fond) ; les statistiques — disponibilité,
incidents, plus longue interruption — sont dérivées des échantillons, jamais stockées :
elles se recalculent, donc ne peuvent pas diverger. Un incident = une suite maximale
d'échantillons non-« up » (warn compte : un service dégradé n'est pas disponible).
"""

from __future__ import annotations

import sqlite3
import statistics
import time
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS service_samples (
    ts INTEGER NOT NULL,
    service_id TEXT NOT NULL,
    state TEXT NOT NULL
)
"""
_INDEX = "CREATE INDEX IF NOT EXISTS idx_service_samples_ts ON service_samples (ts)"


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(_SCHEMA)
        conn.execute(_INDEX)


def record_states(path: Path, states: dict[str, str], now: float | None = None) -> None:
    ts = int(now if now is not None else time.time())
    with sqlite3.connect(path) as conn:
        conn.executemany(
            "INSERT INTO service_samples (ts, service_id, state) VALUES (?, ?, ?)",
            [(ts, service_id, state) for service_id, state in states.items()],
        )


def prune(path: Path, retention_days: int, now: float | None = None) -> None:
    cutoff = int((now if now is not None else time.time()) - retention_days * 86400)
    with sqlite3.connect(path) as conn:
        conn.execute("DELETE FROM service_samples WHERE ts < ?", (cutoff,))


def stats(path: Path, hours: float = 168.0, now: float | None = None) -> dict[str, dict]:
    """{service_id: {uptime_pct, incidents, longest_minutes}} sur la fenêtre demandée."""
    cutoff = int((now if now is not None else time.time()) - hours * 3600)
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            "SELECT service_id, ts, state FROM service_samples WHERE ts >= ?"
            " ORDER BY service_id, ts ASC",
            (cutoff,),
        ).fetchall()
    if not rows:
        return {}

    result: dict[str, dict] = {}
    per_service: dict[str, list[tuple[int, str]]] = {}
    for service_id, ts, state in rows:
        per_service.setdefault(service_id, []).append((ts, state))

    for service_id, samples in per_service.items():
        gaps = [b[0] - a[0] for a, b in zip(samples, samples[1:], strict=False)]
        step = statistics.median(gaps) if gaps else 60
        up = sum(1 for _, state in samples if state == "up")
        incidents, longest = 0, 0
        current = 0
        for _, state in samples:
            if state != "up":
                current += 1
            elif current:
                incidents += 1
                longest = max(longest, current)
                current = 0
        if current:
            incidents += 1
            longest = max(longest, current)
        result[service_id] = {
            "uptime_pct": round(up / len(samples) * 100, 1),
            "incidents": incidents,
            "longest_minutes": round(longest * step / 60),
        }
    return result
