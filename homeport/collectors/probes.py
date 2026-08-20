"""Sondes de disponibilité : le service répond-il vraiment sur son port ?

Utile pour ce qui n'est ni un conteneur ni une unité systemd (go2rtc, lancé comme process
enfant par Home Assistant), et comme confirmation pour le reste : un conteneur peut être
`running` alors que l'application qu'il héberge ne répond plus.
"""

from __future__ import annotations

import asyncio
import ssl

import httpx

TIMEOUT = 2.5
HOST = "127.0.0.1"


async def tcp(port: int, timeout: float = TIMEOUT) -> bool:
    """Le port accepte-t-il une connexion TCP ?"""
    writer = None
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(HOST, port), timeout=timeout)
        return True
    except Exception:
        return False
    finally:
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass


async def http(port: int, scheme: str = "http", path: str = "/", timeout: float = TIMEOUT) -> bool:
    """Le service renvoie-t-il une réponse HTTP ?

    N'importe quel code de statut vaut « vivant » : une redirection ou un 401 prouvent qu'un
    serveur écoute. Les certificats auto-signés (Portainer en 9443) sont acceptés — on sonde
    la boucle locale, pas Internet.
    """
    verify: ssl.SSLContext | bool = False if scheme == "https" else True
    url = f"{scheme}://{HOST}:{port}{path}"
    try:
        async with httpx.AsyncClient(verify=verify, timeout=timeout, follow_redirects=False) as client:
            await client.get(url)
        return True
    except httpx.HTTPStatusError:
        return True
    except Exception:
        return False
