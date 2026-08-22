"""Inventaire persistant des appareils du LAN — clé = adresse MAC.

Même base SQLite et mêmes conventions que `history.py` : stdlib, connexions courtes,
timestamps unix entiers. Les colonnes de présence (`last_seen`, `last_ip`) appartiennent au
job de fond ; les colonnes de méta (`name`, `note`, `category`, `acknowledged`) appartiennent
à Alice via l'API — l'upsert ne les touche jamais, aucun écrasement possible.
"""

from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path

CATEGORIES = frozenset(
    {"computer", "phone", "homeautomation", "iot", "network", "media", "other"}
)

_MAC = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$")
# Modifiables par l'API (`update_meta`) — tout le reste appartient au job de fond.
_META_FIELDS = frozenset({"name", "note", "category", "acknowledged", "mdns_name"})

_SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    mac TEXT PRIMARY KEY,
    name TEXT,
    note TEXT,
    category TEXT,
    first_seen INTEGER NOT NULL,
    last_seen INTEGER NOT NULL,
    last_ip TEXT,
    mdns_name TEXT,
    acknowledged INTEGER NOT NULL DEFAULT 0
)
"""


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(_SCHEMA)


def normalize_mac(mac: str) -> str | None:
    """Forme canonique `aa:bb:cc:dd:ee:ff`, ou None si malformée."""
    cleaned = mac.strip().lower().replace("-", ":")
    return cleaned if _MAC.match(cleaned) else None


def upsert_seen(path: Path, seen: list[dict], now: float | None = None) -> list[dict]:
    """Enregistre un passage du job de fond ; retourne les appareils vus pour la première
    fois (`[{mac, ip}]`), matière du livre de bord.

    Table vide = tout premier passage : les appareils déjà présents sont acquittés d'office,
    sinon les ~50 appareils du jour zéro inonderaient le capteur « nouveaux » de HA — et le
    premier passage ne compte donc jamais comme « nouveaux ».
    """
    ts = int(now if now is not None else time.time())
    created: list[dict] = []
    with sqlite3.connect(path) as conn:
        initial = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0] == 0
        known = {row[0] for row in conn.execute("SELECT mac FROM devices")}
        for device in seen:
            mac = normalize_mac(device.get("mac", ""))
            if mac is None:
                continue
            conn.execute(
                """INSERT INTO devices (mac, first_seen, last_seen, last_ip, acknowledged)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(mac) DO UPDATE SET last_seen = ?, last_ip = ?""",
                (mac, ts, ts, device.get("ip"), 1 if initial else 0, ts, device.get("ip")),
            )
            if not initial and mac not in known:
                created.append({"mac": mac, "ip": device.get("ip")})
            known.add(mac)
    return created


def list_devices(path: Path) -> list[dict]:
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM devices ORDER BY last_seen DESC").fetchall()
    return [dict(row) for row in rows]


def unacknowledged(path: Path) -> list[dict]:
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM devices WHERE acknowledged = 0 ORDER BY first_seen DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def display_name(device: dict, vendor: str | None) -> tuple[str, str]:
    """Le meilleur nom disponible et sa source. Le nom manuel gagne toujours ; à défaut le
    mDNS (l'appareil se nomme lui-même) ; à défaut le fabricant ; sinon la MAC brute."""
    if device.get("name"):
        return device["name"], "manual"
    if device.get("mdns_name"):
        return device["mdns_name"], "mdns"
    if vendor:
        return vendor, "vendor"
    return device["mac"], "unknown"


def update_meta(path: Path, mac: str, fields: dict) -> bool:
    """Met à jour les colonnes de méta d'un appareil. False si la MAC n'existe pas —
    l'API ne crée jamais d'appareil, seul le job de fond le fait."""
    allowed = {k: v for k, v in fields.items() if k in _META_FIELDS}
    if not allowed:
        return False
    assignments = ", ".join(f"{key} = ?" for key in allowed)
    with sqlite3.connect(path) as conn:
        cursor = conn.execute(
            f"UPDATE devices SET {assignments} WHERE mac = ?",
            (*allowed.values(), mac),
        )
        return cursor.rowcount > 0
