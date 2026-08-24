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


# — API v1 : lecture par curseur —————————————————————————————————————————————
#
# `query` ci-dessus sert le livre de bord du front web : fenêtre en jours, ordre décroissant,
# actions admin fusionnées à la lecture. L'API v1 a besoin de l'inverse — un curseur qui avance,
# donc des identifiants monotones et un ordre croissant — et ne peut pas fusionner les actions :
# elles vivent dans une autre table, avec leur propre séquence d'identifiants. Les mêler ici
# casserait la seule garantie sur laquelle un client construit son curseur.

_SEVERITY_V1 = {"up": "info", "warn": "warning", "down": "critical"}

#: Les trois sévérités du contrat v1, dans l'ordre croissant de gravité.
SEVERITIES_V1 = ("info", "warning", "critical")


def severity_v1(raw: str) -> str:
    """Normalise une sévérité interne vers le vocabulaire du contrat.

    Une valeur sans correspondance devient `warning` : la rabattre sur `info` la rendrait
    invisible, sur `critical` elle réveillerait pour rien. C'est la règle du client, appliquée
    symétriquement côté serveur.
    """
    return _SEVERITY_V1.get(raw, "warning")


def latest_id(path: Path) -> int:
    """Plus grand identifiant existant, indépendamment de tout filtre. `0` si la table est vide.

    C'est le garde-fou du contrat : un client dont le curseur dépasse cette valeur sait que
    l'historique a été remplacé, même sous un epoch qu'il croit connaître.
    """
    with sqlite3.connect(path) as conn:
        row = conn.execute("SELECT MAX(id) FROM events").fetchone()
    return row[0] or 0


def query_since(
    path: Path,
    since_id: int = 0,
    limit: int = 200,
    severities: list[str] | None = None,
) -> list[dict]:
    """Événements d'identifiant strictement supérieur à `since_id`, du plus ancien au plus récent.

    `severities` filtre sur le vocabulaire v1 ; une valeur inconnue y est ignorée plutôt que de
    faire échouer la requête. Le filtre s'applique après normalisation, donc `critical` retrouve
    bien les `down` consignés en interne.
    """
    wanted = None
    if severities:
        retenues = [s for s in severities if s in SEVERITIES_V1]
        if retenues:
            # Traduction inverse : filtrer en SQL sur les valeurs réellement stockées évite de
            # rapatrier toute la table pour n'en garder qu'une part.
            wanted = [raw for raw, v1 in _SEVERITY_V1.items() if v1 in retenues]

    sql = "SELECT id, ts, kind, severity, subject, detail FROM events WHERE id > ?"
    params: list = [max(0, since_id)]
    if wanted is not None:
        sql += " AND severity IN (" + ",".join("?" for _ in wanted) + ")"
        params.extend(wanted)
    sql += " ORDER BY id ASC LIMIT ?"
    params.append(max(1, limit))

    with sqlite3.connect(path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [
        {
            "id": row_id,
            "ts": ts,
            "kind": kind,
            "severity": severity_v1(severity),
            "subject": subject,
            "detail": detail,
        }
        for row_id, ts, kind, severity, subject, detail in rows
    ]
