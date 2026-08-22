"""Livre de bord — la mémoire longue du port.

Les échantillons (service_samples, wan_samples) sont purgés au bout de 7 jours : ils
servent aux statistiques, pas au souvenir. Cette table ne garde que les transitions et
faits marquants — un service qui tombe, Internet qui revient, un appareil inconnu — et
les garde un an. Une ligne par événement, jamais d'échantillonnage : elle reste minuscule.

Le vocabulaire des `kind` est hiérarchique (`service.down`, `internet.up`, `device.new`) ;
les familles se filtrent par préfixe. `severity` reprend le vocabulaire d'état du
dashboard (up / warn / down) — la couleur suit l'état, jamais l'inverse.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    kind TEXT NOT NULL,
    severity TEXT NOT NULL,
    subject TEXT NOT NULL,
    detail TEXT
)
"""
_INDEX = "CREATE INDEX IF NOT EXISTS idx_events_ts ON events (ts)"


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(_SCHEMA)
        conn.execute(_INDEX)


def record(
    path: Path,
    kind: str,
    severity: str,
    subject: str,
    detail: str | None = None,
    now: float | None = None,
) -> None:
    ts = int(now if now is not None else time.time())
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO events (ts, kind, severity, subject, detail) VALUES (?, ?, ?, ?, ?)",
            (ts, kind, severity, subject, detail),
        )


def query(
    path: Path,
    days: float = 7.0,
    kinds: list[str] | None = None,
    limit: int = 200,
    now: float | None = None,
) -> list[dict]:
    """Événements de la fenêtre, du plus récent au plus ancien.

    `kinds` filtre par préfixe de famille (« service. » matche service.down, service.up…).
    """
    cutoff = int((now if now is not None else time.time()) - days * 86400)
    sql = "SELECT ts, kind, severity, subject, detail FROM events WHERE ts >= ?"
    params: list = [cutoff]
    if kinds:
        sql += " AND (" + " OR ".join("kind LIKE ?" for _ in kinds) + ")"
        params.extend(f"{prefix}%" for prefix in kinds)
    sql += " ORDER BY ts DESC, id DESC LIMIT ?"
    params.append(max(1, limit))
    with sqlite3.connect(path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [
        {"ts": ts, "kind": kind, "severity": severity, "subject": subject, "detail": detail}
        for ts, kind, severity, subject, detail in rows
    ]


def prune(path: Path, retention_days: int = 365, now: float | None = None) -> None:
    cutoff = int((now if now is not None else time.time()) - retention_days * 86400)
    with sqlite3.connect(path) as conn:
        conn.execute("DELETE FROM events WHERE ts < ?", (cutoff,))
