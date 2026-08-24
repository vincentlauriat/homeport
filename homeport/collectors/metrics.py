"""Métriques agrégées en quatre échelles, pour l'API v1.

Le contrat exige 24 h @ 1 min, 7 j @ 5 min, 30 j @ 1 h et 1 an @ 1 j. La table `samples` de
`history.py` ne peut pas y répondre : elle garde une seule résolution et sept jours de rétention
par défaut. Trois des quatre plages sont hors de sa portée, et remonter sa rétention à un an à
pleine résolution ferait grossir la base sans borne utile.

D'où des seaux pré-agrégés. Chaque échantillon est versé dans le seau courant des quatre échelles
sous forme de somme et de compte, jamais de moyenne déjà calculée : une moyenne incrémentale se
recalcule sans relire l'historique, et un compte à zéro dit « aucune mesure » sans le confondre
avec une mesure à zéro. Le coût total est borné par construction — 1 440 + 2 016 + 720 + 365 seaux,
soit moins de 4 600 lignes quel que soit le temps écoulé.

Un compte par série, et non un compte global : un Pi sans capteur thermique doit pouvoir servir
trois séries pleines et une série entièrement vide.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

#: échelle -> (pas en secondes, étendue de la fenêtre en secondes)
SCALES: dict[str, tuple[int, int]] = {
    "24h": (60, 24 * 3600),
    "7d": (300, 7 * 86400),
    "30d": (3600, 30 * 86400),
    "1y": (86400, 365 * 86400),
}

#: Les séries du contrat, dans l'ordre où elles se lisent.
SERIES = ("cpu_pct", "mem_pct", "disk_pct", "temp_c")

_COLUMNS = {"cpu_pct": "cpu", "mem_pct": "mem", "disk_pct": "disk", "temp_c": "temp"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS metric_rollups (
    scale TEXT NOT NULL,
    ts INTEGER NOT NULL,
    cpu_sum REAL NOT NULL DEFAULT 0,  cpu_n INTEGER NOT NULL DEFAULT 0,
    mem_sum REAL NOT NULL DEFAULT 0,  mem_n INTEGER NOT NULL DEFAULT 0,
    disk_sum REAL NOT NULL DEFAULT 0, disk_n INTEGER NOT NULL DEFAULT 0,
    temp_sum REAL NOT NULL DEFAULT 0, temp_n INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (scale, ts)
)
"""


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(_SCHEMA)


def _bucket(ts: float, step: int) -> int:
    """Début du seau contenant `ts`, aligné sur le pas."""
    return int(ts) // step * step


def record(path: Path, sample: dict, now: float | None = None) -> None:
    """Verse un échantillon dans le seau courant des quatre échelles.

    `sample` porte les clés de `SERIES`; une valeur absente ou `None` n'incrémente rien, ce qui
    laisse la série vide pour ce seau au lieu d'y injecter un zéro.
    """
    ts = now if now is not None else time.time()
    present = {name: sample.get(name) for name in SERIES}
    present = {name: value for name, value in present.items() if value is not None}

    with sqlite3.connect(path) as conn:
        for scale, (step, _span) in SCALES.items():
            bucket = _bucket(ts, step)
            conn.execute(
                "INSERT INTO metric_rollups (scale, ts) VALUES (?, ?) ON CONFLICT DO NOTHING",
                (scale, bucket),
            )
            for name, value in present.items():
                column = _COLUMNS[name]
                conn.execute(
                    f"UPDATE metric_rollups SET {column}_sum = {column}_sum + ?, "
                    f"{column}_n = {column}_n + 1 WHERE scale = ? AND ts = ?",
                    (float(value), scale, bucket),
                )


def prune(path: Path, now: float | None = None) -> None:
    """Supprime les seaux sortis de la fenêtre de leur échelle. C'est ce qui borne le stockage."""
    ts = now if now is not None else time.time()
    with sqlite3.connect(path) as conn:
        for scale, (_step, span) in SCALES.items():
            conn.execute(
                "DELETE FROM metric_rollups WHERE scale = ? AND ts < ?", (scale, int(ts) - span)
            )


def series(path: Path, scale: str, now: float | None = None) -> dict:
    """La fenêtre complète d'une échelle, prête à être servie.

    `from` et `to` sont alignés sur le pas, donc `(to - from)` en est toujours un multiple exact et
    la longueur des séries n'est jamais ambiguë. Chaque série est un tableau dense où l'instant du
    point d'indice `i` vaut `from + i * step_s` ; un seau sans mesure y apparaît en `None`.
    """
    step, span = SCALES[scale]
    ts = now if now is not None else time.time()
    # `to` exclu : le seau courant est encore en train de se remplir, l'inclure ferait osciller
    # sa valeur d'un appel à l'autre.
    to = _bucket(ts, step)
    start = to - span
    count = span // step

    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            "SELECT ts, cpu_sum, cpu_n, mem_sum, mem_n, disk_sum, disk_n, temp_sum, temp_n "
            "FROM metric_rollups WHERE scale = ? AND ts >= ? AND ts < ?",
            (scale, start, to),
        ).fetchall()

    values: dict[str, list[float | None]] = {name: [None] * count for name in SERIES}
    for row in rows:
        index = (row[0] - start) // step
        if not 0 <= index < count:
            continue
        for offset, name in enumerate(SERIES):
            total, n = row[1 + offset * 2], row[2 + offset * 2]
            if n:
                values[name][index] = round(total / n, 1)

    return {"range": scale, "step_s": step, "from": start, "to": to, "series": values}
