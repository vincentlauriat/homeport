"""Santé de la connexion Internet — « la box a-t-elle coupé cette nuit ? ».

La mesure évite ICMP (privilèges) et les sous-processus : une connexion TCP vers le port 53
de deux résolveurs publics indépendants (Cloudflare, Quad9) mesure la joignabilité et la
latence ; `getaddrinfo` vérifie que la résolution DNS fonctionne. Un résolveur suffit pour
être « en ligne » — c'est la panne de l'autre, pas la nôtre.

Chaque mesure est historisée en SQLite (même base, mêmes conventions que history.py) : les
coupures sont *dérivées* des échantillons — une suite d'échantillons hors ligne = une coupure,
avec début et durée. Le job tourne toutes les 60 s : une coupure plus courte peut passer
inaperçue, compromis assumé pour un lien domestique.
"""

from __future__ import annotations

import asyncio
import socket
import sqlite3
import statistics
import time
from pathlib import Path

# Deux opérateurs distincts : la panne simultanée des deux signifie que c'est nous.
_TARGETS = [("1.1.1.1", 53), ("9.9.9.9", 53)]
_TIMEOUT = 3.0
_DNS_PROBE = "debian.org"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS wan_samples (
    ts INTEGER NOT NULL,
    online INTEGER NOT NULL,
    latency_ms REAL
)
"""


async def _tcp_latency_ms(host: str, port: int, timeout: float) -> float | None:
    start = time.monotonic()
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
    except (OSError, asyncio.TimeoutError):
        return None
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        pass
    return round((time.monotonic() - start) * 1000, 1)


def _dns_resolves() -> bool:
    try:
        socket.getaddrinfo(_DNS_PROBE, 443, proto=socket.IPPROTO_TCP)
        return True
    except OSError:
        return False


async def measure() -> dict:
    latencies = await asyncio.gather(
        *(_tcp_latency_ms(host, port, _TIMEOUT) for host, port in _TARGETS)
    )
    reachable = [lat for lat in latencies if lat is not None]
    return {
        "online": bool(reachable),
        "latency_ms": round(statistics.median(reachable), 1) if reachable else None,
        "dns_ok": _dns_resolves(),
    }


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(_SCHEMA)


def record(path: Path, sample: dict, now: float | None = None) -> None:
    ts = int(now if now is not None else time.time())
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO wan_samples (ts, online, latency_ms) VALUES (?, ?, ?)",
            (ts, 1 if sample.get("online") else 0, sample.get("latency_ms")),
        )


def prune(path: Path, retention_days: int, now: float | None = None) -> None:
    cutoff = int((now if now is not None else time.time()) - retention_days * 86400)
    with sqlite3.connect(path) as conn:
        conn.execute("DELETE FROM wan_samples WHERE ts < ?", (cutoff,))


def outages(path: Path, hours: float = 24.0, now: float | None = None) -> list[dict]:
    """Liste détaillée des coupures sur la fenêtre : [{start_ts, minutes}] — pour la page
    /historique, qui les surimprime sur les courbes."""
    cutoff = int((now if now is not None else time.time()) - hours * 3600)
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            "SELECT ts, online FROM wan_samples WHERE ts >= ? ORDER BY ts ASC", (cutoff,)
        ).fetchall()
    if not rows:
        return []
    gaps = [b[0] - a[0] for a, b in zip(rows, rows[1:])]
    step = statistics.median(gaps) if gaps else 60
    result, start, count = [], None, 0
    for ts, online in rows:
        if not online:
            start = ts if start is None else start
            count += 1
        elif start is not None:
            result.append({"start_ts": start, "minutes": round(count * step / 60)})
            start, count = None, 0
    if start is not None:
        result.append({"start_ts": start, "minutes": round(count * step / 60)})
    return result


def summarize(path: Path, hours: float = 24.0, now: float | None = None) -> dict:
    """Synthèse pour la tuile : état courant, latence médiane, coupures sur la fenêtre.

    Une coupure = une suite maximale d'échantillons hors ligne ; sa durée = nb d'échantillons
    × l'écart médian réel entre échantillons (robuste si l'intervalle de mesure change)."""
    cutoff = int((now if now is not None else time.time()) - hours * 3600)
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            "SELECT ts, online, latency_ms FROM wan_samples WHERE ts >= ? ORDER BY ts ASC",
            (cutoff,),
        ).fetchall()

    if not rows:
        return {"online": None, "latency_ms": None, "outages_24h": 0,
                "last_outage_ts": None, "last_outage_minutes": None}

    outages: list[tuple[int, int]] = []  # (ts de début, nb d'échantillons)
    current_start, current_count = None, 0
    for ts, online, _ in rows:
        if not online:
            current_start = ts if current_start is None else current_start
            current_count += 1
        elif current_start is not None:
            outages.append((current_start, current_count))
            current_start, current_count = None, 0
    if current_start is not None:
        outages.append((current_start, current_count))

    gaps = [b[0] - a[0] for a, b in zip(rows, rows[1:])]
    step = statistics.median(gaps) if gaps else 60
    latencies = [lat for _, online, lat in rows if online and lat is not None]

    last_outage = outages[-1] if outages else None
    return {
        "online": bool(rows[-1][1]),
        "latency_ms": round(statistics.median(latencies), 1) if latencies else None,
        "outages_24h": len(outages),
        "last_outage_ts": last_outage[0] if last_outage else None,
        "last_outage_minutes": round(last_outage[1] * step / 60) if last_outage else None,
    }
