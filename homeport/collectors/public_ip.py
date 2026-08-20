"""IP publique du foyer — relevée une fois par heure, historisée au changement.

Le jour où un service externe dépend de cette IP (DDNS, allowlist), la réponse existe déjà :
quand a-t-elle changé, et combien de fois. Source : api.ipify.org (réponse en texte brut,
service dédié à cet unique usage) — c'est le seul appel sortant de tout Homeport, une fois
par heure, sans aucune donnée envoyée.
"""

from __future__ import annotations

import ipaddress
import sqlite3
import time
from pathlib import Path

import httpx

_ENDPOINT = "https://api.ipify.org"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS public_ip_history (
    ts INTEGER NOT NULL,
    ip TEXT NOT NULL
)
"""


def parse_ip(raw: str) -> str | None:
    candidate = raw.strip()
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return None
    return candidate


async def fetch() -> str | None:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(_ENDPOINT)
            response.raise_for_status()
            return parse_ip(response.text)
    except Exception:
        return None


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(_SCHEMA)


def track(path: Path, ip: str, now: float | None = None) -> bool:
    """Historise l'IP si elle diffère de la dernière connue. True = changement réel."""
    ts = int(now if now is not None else time.time())
    with sqlite3.connect(path) as conn:
        last = conn.execute(
            "SELECT ip FROM public_ip_history ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        if last and last[0] == ip:
            return False
        conn.execute("INSERT INTO public_ip_history (ts, ip) VALUES (?, ?)", (ts, ip))
        return True


def current(path: Path) -> dict | None:
    """Dernière IP connue et la date de son VRAI changement (pas du dernier relevé)."""
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            "SELECT ts, ip FROM public_ip_history ORDER BY ts DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    return {"ip": row[1], "changed_ts": row[0]}
