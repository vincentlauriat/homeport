"""Résolution mDNS inverse des IP du LAN via avahi-resolve-address (paquet avahi-utils,
installé par deploy.sh). Seuls les appareils qui s'annoncent (Apple, imprimantes, TV…)
répondent — l'échec est le cas majoritaire et n'est jamais journalisé.
"""

from __future__ import annotations

import asyncio

from . import _process

# 8 résolutions à la fois : assez pour couvrir ~50 IP en quelques secondes, sans lâcher
# 50 sous-processus d'un coup sur un Pi.
_CONCURRENCY = 8


def parse_avahi_output(raw: str) -> str | None:
    """`192.168.68.27<TAB>MacBook-Air.local` -> `MacBook-Air`. Tout le reste -> None."""
    line = raw.strip().splitlines()[0] if raw.strip() else ""
    _, tab, hostname = line.partition("\t")
    if not tab or not hostname:
        return None
    return hostname.removesuffix(".local") or None


async def resolve(ip: str) -> str | None:
    stdout = await _process.run("avahi-resolve-address", ip, timeout=3)
    if stdout is None:
        return None
    return parse_avahi_output(stdout.decode())


async def resolve_many(ips: list[str]) -> dict[str, str]:
    semaphore = asyncio.Semaphore(_CONCURRENCY)

    async def bounded(ip: str) -> tuple[str, str | None]:
        async with semaphore:
            return ip, await resolve(ip)

    results = await asyncio.gather(*(bounded(ip) for ip in ips))
    return {ip: name for ip, name in results if name}
