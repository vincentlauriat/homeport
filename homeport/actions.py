"""Actions authentifiées par identité Tailscale (chantier E de la roadmap).

Le principe : l'identité vient du réseau, pas d'un login. Une requête arrivant par le tailnet
porte une IP 100.64.0.0/10 ; `tailscale whois` sur cette IP répond — de manière infalsifiable
depuis le LAN — quel compte du tailnet la possède. Le LAN (et la tablette murale) garde le
Homeport strictement lecture seule : aucune action n'y est jamais proposée ni acceptée.

Chaque action est journalisée en SQLite (qui, quoi, quand, résultat) — la confiance n'exclut
pas la traçabilité.
"""

from __future__ import annotations

import ipaddress
import json
import sqlite3
import time
from pathlib import Path

from .collectors import _process

# La plage réservée CGNAT qu'utilise Tailscale pour toutes les adresses du tailnet.
_TAILNET = ipaddress.ip_network("100.64.0.0/10")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS actions (
    ts INTEGER NOT NULL,
    identity TEXT NOT NULL,
    kind TEXT NOT NULL,
    target TEXT NOT NULL,
    ok INTEGER NOT NULL
)
"""


def is_tailnet_ip(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip) in _TAILNET
    except ValueError:
        return False


def parse_whois_login(raw_json: str) -> str | None:
    """LoginName du propriétaire de l'IP, ou None (JSON invalide, pas de profil)."""
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        return None
    return (data.get("UserProfile") or {}).get("LoginName") or None


async def authorize(ip: str, expected_login: str) -> bool:
    """L'IP appartient-elle au tailnet ET à l'identité attendue ?

    Le test d'appartenance à la plage vient en premier : pour une IP LAN, `whois` n'est même
    pas consulté — la réponse est structurelle, pas un appel système."""
    if not expected_login or not is_tailnet_ip(ip):
        return False
    stdout = await _process.run("tailscale", "whois", "--json", ip, timeout=5)
    if stdout is None:
        return False
    return parse_whois_login(stdout.decode()) == expected_login


async def restart(service) -> bool:
    """Redémarre le service — conteneur via `sudo docker restart`, unité via `sudo systemctl`.

    `sudo -n` : non interactif — sans la règle sudoers exacte (deploy/sudoers-homeport), l'appel
    échoue immédiatement au lieu de bloquer la boucle. Jamais par le socket Docker : le chantier
    B l'a rendu structurellement lecture seule, et c'est très bien comme ça."""
    if service.docker:
        out = await _process.run("sudo", "-n", "docker", "restart", service.docker, timeout=60)
        return out is not None
    if service.systemd:
        out = await _process.run("sudo", "-n", "systemctl", "restart", service.systemd, timeout=60)
        return out is not None
    return False


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(_SCHEMA)


def record(path: Path, identity: str, kind: str, target: str, ok: bool, now: float | None = None) -> None:
    ts = int(now if now is not None else time.time())
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO actions (ts, identity, kind, target, ok) VALUES (?, ?, ?, ?, ?)",
            (ts, identity, kind, target, 1 if ok else 0),
        )


def recent(path: Path, limit: int = 20) -> list[dict]:
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT ts, identity, kind, target, ok FROM actions ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
