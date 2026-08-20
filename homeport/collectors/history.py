"""Historique local des métriques machine (CPU, mémoire, températures).

SQLite via la bibliothèque standard : pas de dépendance ajoutée, cohérent avec le reste des
collecteurs. Chaque appel ouvre une connexion courte — les écritures sont espacées de plusieurs
minutes (voir `background.py`), aucune raison de garder une connexion persistante.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS samples (
    ts INTEGER NOT NULL,
    cpu_pct REAL,
    mem_pct REAL,
    temp_c REAL,
    nvme_temp_c REAL
)
"""


def init_db(path: Path) -> None:
    """Crée la table si absente. Rejouable sans effet de bord (`IF NOT EXISTS`)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(_SCHEMA)


def record(path: Path, sample: dict, now: float | None = None) -> None:
    """Insère un échantillon. `sample` : cpu_pct, mem_pct, temp_c, nvme_temp_c (les deux
    derniers peuvent être `None` — un Pi sans capteur NVMe, par exemple)."""
    ts = int(now if now is not None else time.time())
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO samples (ts, cpu_pct, mem_pct, temp_c, nvme_temp_c) VALUES (?, ?, ?, ?, ?)",
            (ts, sample.get("cpu_pct"), sample.get("mem_pct"), sample.get("temp_c"), sample.get("nvme_temp_c")),
        )


def prune(path: Path, retention_days: int, now: float | None = None) -> int:
    """Supprime les échantillons plus vieux que `retention_days`. Renvoie le nombre supprimé."""
    cutoff = int((now if now is not None else time.time()) - retention_days * 86400)
    with sqlite3.connect(path) as conn:
        cursor = conn.execute("DELETE FROM samples WHERE ts < ?", (cutoff,))
        return cursor.rowcount


def query_range(path: Path, hours: float, now: float | None = None) -> list[dict]:
    """Échantillons des `hours` dernières heures, du plus ancien au plus récent."""
    cutoff = int((now if now is not None else time.time()) - hours * 3600)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT ts, cpu_pct, mem_pct, temp_c, nvme_temp_c FROM samples WHERE ts >= ? ORDER BY ts ASC",
            (cutoff,),
        ).fetchall()
    return [dict(row) for row in rows]
