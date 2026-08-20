"""État des conteneurs, lu sur l'API HTTP de Docker via httpx (jamais le SDK `docker`,
synchrone, qui bloquerait la boucle asyncio de FastAPI à chaque rafraîchissement).

Le transport est configurable par `HOMEPORT_DOCKER_HOST` :
  - `unix:///var/run/docker.sock` (défaut) — accès direct, pratique en développement ;
  - `tcp://127.0.0.1:2375` — le docker-socket-proxy en lecture seule (chantier B de la
    roadmap) : l'API est structurellement limitée aux GET sur /containers, quel que soit
    le bug côté Homeport, et le service n'a plus besoin du groupe `docker`.
"""

from __future__ import annotations

import os
import time

import httpx

DOCKER_HOST = os.environ.get("HOMEPORT_DOCKER_HOST", "unix:///var/run/docker.sock")


def _client(timeout: float) -> httpx.AsyncClient:
    """Client httpx pointant vers Docker, quel que soit le transport configuré."""
    if DOCKER_HOST.startswith("unix://"):
        transport = httpx.AsyncHTTPTransport(uds=DOCKER_HOST.removeprefix("unix://"))
        # L'hôte de base_url est décoratif : le transport UDS impose la destination.
        return httpx.AsyncClient(transport=transport, base_url="http://docker", timeout=timeout)
    return httpx.AsyncClient(base_url=DOCKER_HOST.replace("tcp://", "http://", 1), timeout=timeout)


def _uptime(started_unix: int | None) -> str:
    if not started_unix:
        return ""
    delta = int(time.time()) - started_unix
    if delta < 0:
        return ""
    days, rest = divmod(delta, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    if days:
        return f"{days} j {hours} h"
    if hours:
        return f"{hours} h {minutes} min"
    return f"{minutes} min"


async def collect() -> dict[str, dict]:
    """Retourne {nom_du_conteneur: {state, status, image, uptime, ports}}.

    En cas d'échec (socket absent, droits manquants), retourne un dict vide : le dashboard
    reste utilisable, les services Docker apparaissent simplement en état inconnu.
    """
    try:
        async with _client(timeout=5.0) as client:
            response = await client.get("/containers/json", params={"all": "1"})
            response.raise_for_status()
            containers = response.json()
    except Exception:
        return {}

    result: dict[str, dict] = {}
    for container in containers:
        for raw_name in container.get("Names", []):
            name = raw_name.lstrip("/")
            ports = sorted(
                {p["PublicPort"] for p in container.get("Ports", []) if p.get("PublicPort")}
            )
            result[name] = {
                "state": container.get("State", "unknown"),  # running | exited | paused ...
                "status": container.get("Status", ""),
                "image": container.get("Image", ""),
                "uptime": _uptime(container.get("Created")),
                "ports": ports,
            }
    return result


async def is_available() -> bool:
    """Le socket Docker est-il joignable ?"""
    try:
        async with _client(timeout=3.0) as client:
            response = await client.get("/_ping")
            return response.status_code == 200
    except Exception:
        return False


def _cpu_percent(stats: dict) -> float:
    """% CPU d'un conteneur à partir d'un payload `stats`, formule officielle de Docker.

    `system_cpu_usage` est la somme sur tous les cœurs : le ratio est donc multiplié par le
    nombre de cœurs en ligne pour rendre un pourcentage lisible (un conteneur qui sature un cœur
    sur quatre pèse 25 %). La mémoire n'est **pas** exposée : `docker stats` renvoie `0B` sur cet
    hôte (cgroup v2 sans le contrôleur mémoire côté hôte), seul le CPU est exploitable.
    """
    cpu = stats.get("cpu_stats") or {}
    precpu = stats.get("precpu_stats") or {}
    # Sans échantillon précédent (premier relevé), le delta se calcule contre l'usage cumulé
    # depuis le boot et rend un pourcentage absurde : mieux vaut 0 que faux.
    if "system_cpu_usage" not in precpu:
        return 0.0
    cpu_total = (cpu.get("cpu_usage") or {}).get("total_usage", 0)
    precpu_total = (precpu.get("cpu_usage") or {}).get("total_usage", 0)
    cpu_delta = cpu_total - precpu_total
    system_delta = cpu.get("system_cpu_usage", 0) - precpu.get("system_cpu_usage", 0)
    if system_delta <= 0 or cpu_delta < 0:
        return 0.0
    online = cpu.get("online_cpus") or len((cpu.get("cpu_usage") or {}).get("percpu_usage") or []) or 1
    return round(cpu_delta / system_delta * online * 100, 1)


def _demux_logs(raw: bytes) -> str:
    """Reconstruit le texte d'un flux de logs Docker.

    Sans TTY, Docker multiplexe stdout et stderr : chaque trame porte un en-tête de 8 octets
    (`[type, 0, 0, 0, taille sur 4 octets big-endian]`). Avec TTY, c'est du texte brut. On tente
    le démultiplexage ; au premier en-tête qui n'a pas de sens (flux TTY, ou trame tronquée), on
    rend le reste tel quel — mieux vaut du texte brut lisible que des octets perdus."""
    out = []
    i, n = 0, len(raw)
    while i + 8 <= n:
        stream = raw[i]
        size = int.from_bytes(raw[i + 4 : i + 8], "big")
        if stream not in (0, 1, 2) or i + 8 + size > n:
            break
        out.append(raw[i + 8 : i + 8 + size])
        i += 8 + size
    if i == 0:
        return raw.decode("utf-8", "replace")
    if i < n:
        out.append(raw[i:])
    return b"".join(out).decode("utf-8", "replace")


async def logs(name: str, tail: int = 100) -> str:
    """Dernières `tail` lignes de log d'un conteneur. Appel ponctuel (à la demande d'un clic),
    pas une boucle de fond : rapide car borné par `tail`, sans streaming."""
    try:
        async with _client(timeout=10.0) as client:
            response = await client.get(
                f"/containers/{name}/logs",
                params={"stdout": "1", "stderr": "1", "tail": str(tail), "timestamps": "0"},
            )
            response.raise_for_status()
            return _demux_logs(response.content)
    except Exception:
        return ""


async def stats(names: list[str]) -> dict[str, float]:
    """{nom_conteneur: % CPU} pour les conteneurs demandés, interrogés en parallèle.

    Un appel `stats?stream=false` bloque ~1 s (Docker échantillonne deux fois) : réservé aux
    boucles de fond, jamais au chemin d'une requête. Un conteneur absent ou en échec est simplement
    omis du résultat plutôt que de faire échouer les autres.
    """
    import asyncio

    async def one(client: httpx.AsyncClient, name: str) -> tuple[str, float] | None:
        try:
            response = await client.get(f"/containers/{name}/stats", params={"stream": "false"})
            response.raise_for_status()
            return name, _cpu_percent(response.json())
        except Exception:
            return None

    try:
        async with _client(timeout=10.0) as client:
            results = await asyncio.gather(*(one(client, n) for n in names))
    except Exception:
        return {}
    return {name: pct for r in results if r for name, pct in [r]}
