"""Voisinage réseau : pairs Tailscale en ligne et appareils vus sur le LAN.

Deux sources, toutes deux lisibles sans `sudo` (vérifié sur `homeserver` le 2026-08-19) :
  - `tailscale status --json`  état de chaque pair du tailnet
  - `ip neigh show`            table de voisinage ARP/NDP du noyau — ce que le Pi a vu
                                récemment sur le LAN, sans scan actif ni dépendance externe

L'agent Fing déjà déployé sur l'hôte a été écarté : il n'expose localement qu'un descripteur
UPnP, l'inventaire des appareils vivant dans le cloud Fing (compte payant pour l'API).
"""

from __future__ import annotations

import asyncio
import json

from . import _process

# États qui signifient « une adresse MAC valide a été vue », par opposition à FAILED /
# INCOMPLETE (résolution en cours ou en échec, pas d'appareil confirmé derrière).
_NEIGH_KEPT_STATES = {"REACHABLE", "STALE", "DELAY", "PROBE", "PERMANENT"}
# Interfaces internes à Docker : le Pi héberge Docker, elles apparaîtraient en permanence et
# ne représentent aucun appareil du LAN.
_EXCLUDED_INTERFACE_PREFIXES = ("docker", "veth", "br-")


def parse_tailscale_peers(raw_json: str) -> list[dict]:
    """Pairs du tailnet, `Self` et les pairs nommés `localhost` exclus (ce dernier désigne
    l'hôte lui-même vu à travers une route Tailscale, pas un pair distinct)."""
    data = json.loads(raw_json)
    peers = []
    for peer in data.get("Peer", {}).values():
        hostname = peer.get("HostName", "")
        if hostname == "localhost":
            continue
        peers.append(
            {
                "hostname": hostname,
                "online": bool(peer.get("Online", False)),
                "tailscale_ip": (peer.get("TailscaleIPs") or [None])[0],
            }
        )
    return peers


def parse_tailscale_summary(raw_json: str) -> dict:
    """Résumé pour la tuile Tailscale — dérivé de `parse_tailscale_peers()` pour que les
    compteurs correspondent exactement à la liste de pairs affichée, jamais au dict brut."""
    data = json.loads(raw_json)
    peers = parse_tailscale_peers(raw_json)
    self_data = data.get("Self") or {}
    return {
        "version": (data.get("Version") or "").split("-")[0],
        "self_ip": (self_data.get("TailscaleIPs") or [None])[0],
        "peers_total": len(peers),
        "peers_online": sum(1 for p in peers if p["online"]),
    }


def parse_ip_neigh(raw_output: str) -> list[dict]:
    """Appareils LAN avec une adresse MAC confirmée dans la table de voisinage.

    Parsé par position de mot-clé (`dev`, `lladdr`) plutôt que par regex à positions fixes :
    les entrées IPv6 intercalent parfois un drapeau (`router`, `proxy`, `extern_learn`) entre
    l'adresse MAC et l'état, qu'une regex stricte raterait silencieusement. Dédupliqué par
    MAC : un même appareil apparaît souvent deux fois (une entrée IPv4, une IPv6)."""
    seen_macs: set[str] = set()
    neighbors = []
    for line in raw_output.splitlines():
        tokens = line.split()
        if len(tokens) < 4 or "dev" not in tokens or "lladdr" not in tokens:
            continue
        state = tokens[-1]
        if state not in _NEIGH_KEPT_STATES:
            continue
        interface = tokens[tokens.index("dev") + 1]
        if interface.startswith(_EXCLUDED_INTERFACE_PREFIXES):
            continue
        mac = tokens[tokens.index("lladdr") + 1]
        if mac in seen_macs:
            continue
        seen_macs.add(mac)
        neighbors.append({"ip": tokens[0], "mac": mac, "interface": interface})
    return neighbors


_EMPTY_SUMMARY = {"version": "", "self_ip": None, "peers_total": 0, "peers_online": 0}


async def _tailscale_status() -> str | None:
    stdout = await _process.run("tailscale", "status", "--json")
    return stdout.decode() if stdout is not None else None


async def lan_neighbors() -> list[dict]:
    stdout = await _process.run("ip", "neigh", "show")
    if stdout is None:
        return []
    return parse_ip_neigh(stdout.decode())


async def collect() -> dict:
    raw_status, neighbors = await asyncio.gather(_tailscale_status(), lan_neighbors())

    peers, summary = [], _EMPTY_SUMMARY
    if raw_status is not None:
        try:
            peers = parse_tailscale_peers(raw_status)
            summary = parse_tailscale_summary(raw_status)
        except (json.JSONDecodeError, AttributeError):
            pass

    return {"tailscale_peers": peers, "tailscale_summary": summary, "lan_neighbors": neighbors}
