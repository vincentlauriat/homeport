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


#: Pas de restitution du graphe, en secondes. Découplé de la fréquence d'échantillonnage : la
#: cadence d'écriture a suivi le besoin de l'API v1 (un point par minute pour l'échelle 24 h),
#: alors que le tracé, lui, n'a pas gagné en lisibilité à recevoir cinq fois plus de points.
#: Sans ce pas, la fenêtre 7 jours du front passerait de 2 016 à 10 080 points par requête.
GRAPH_STEP_S = 300


def query_range(path: Path, hours: float, now: float | None = None) -> list[dict]:
    """Échantillons des `hours` dernières heures, du plus ancien au plus récent.

    Un représentant par tranche de `GRAPH_STEP_S`, et non la totalité des lignes : le tracé garde
    la même densité quelle que soit la cadence d'écriture. Le représentant est le plus ancien
    échantillon de sa tranche — un choix stable, qui ne change pas d'une requête à l'autre pour
    une tranche déjà close.
    """
    cutoff = int((now if now is not None else time.time()) - hours * 3600)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        # `MIN(ts)` fait des autres colonnes des « bare columns » : SQLite garantit alors qu'elles
        # portent les valeurs de la ligne qui réalise ce minimum. Une tranche ne peut donc rendre
        # qu'une ligne, même si deux échantillons partagent la même seconde.
        rows = conn.execute(
            "SELECT MIN(ts) AS ts, cpu_pct, mem_pct, temp_c, nvme_temp_c FROM samples "
            "WHERE ts >= ? GROUP BY ts / ? ORDER BY ts ASC",
            (cutoff, GRAPH_STEP_S),
        ).fetchall()
    return [dict(row) for row in rows]
