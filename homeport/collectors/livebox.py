"""Livebox Orange — état WAN et identité via l'API locale « sysbus » (POST /ws).

Sur la Livebox W7 (firmware SGW7-*), `DeviceInfo:get` et `NMC:getWANStatus` répondent
sans authentification : le module ne demande aucun secret. La latence affichée est le
temps de réponse HTTP de la box vue du serveur — un vrai signal de santé du lien local,
conservé dans un ring RAM pour la sparkline de /livebox. Une box injoignable (ou un
firmware qui verrouillerait ces méthodes) donne `reachable: false`, jamais une exception.
"""

from __future__ import annotations

import logging
import time
from collections import deque

import httpx

log = logging.getLogger("homeport.livebox")

DEFAULT_ADDRESS = "192.168.100.254"
_HEADERS = {"Content-Type": "application/x-sah-ws-4-call+json"}

# 480 points à un tick de 15 s = 2 h de latences pour la sparkline.
_latency_history: deque = deque(maxlen=480)


def reset() -> None:
    """Vide le ring de latences (tests)."""
    _latency_history.clear()


async def _ws(client: httpx.AsyncClient, base: str, service: str, method: str) -> dict | None:
    """Un appel sysbus. Selon la méthode, la réponse utile est `status` (DeviceInfo:get)
    ou `data` (NMC:getWANStatus) — on prend le premier des deux qui est un objet."""
    try:
        resp = await client.post(
            f"{base}/ws",
            headers=_HEADERS,
            json={"service": service, "method": method, "parameters": {}},
        )
        resp.raise_for_status()
        body = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        log.debug("livebox %s:%s injoignable : %s", service, method, exc)
        return None
    for key in ("status", "data"):
        if isinstance(body.get(key), dict):
            return body[key]
    return None


async def _collect(client: httpx.AsyncClient, address: str) -> dict:
    base = f"http://{address}"
    start = time.monotonic()
    wan = await _ws(client, base, "NMC", "getWANStatus")
    latency_ms = round((time.monotonic() - start) * 1000, 1)
    if wan is None:
        return {"reachable": False, "online": False, "latency_ms": None,
                "latency_history": list(_latency_history)}
    info = await _ws(client, base, "DeviceInfo", "get") or {}
    _latency_history.append(latency_ms)
    return {
        "reachable": True,
        "online": str(wan.get("WanState", "")).lower() == "up",
        "latency_ms": latency_ms,
        "wan_state": wan.get("WanState"),
        "link_type": wan.get("LinkType"),
        "link_state": wan.get("LinkState"),
        "gpon_state": wan.get("GponState"),
        "protocol": wan.get("Protocol"),
        "connection_state": wan.get("ConnectionState"),
        "connection_state_ipv6": wan.get("ConnectionStateIPv6"),
        "last_error": wan.get("LastConnectionError"),
        "model": info.get("ProductClass"),
        "firmware": info.get("SoftwareVersion"),
        "serial": info.get("SerialNumber"),
        "latency_history": list(_latency_history),
    }


async def fetch_status(settings: dict) -> dict:
    async with httpx.AsyncClient(timeout=5.0) as client:
        return await _collect(client, settings["address"])
