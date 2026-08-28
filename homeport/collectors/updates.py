"""Mises à jour disponibles : paquets APT et images Docker.

**Ce module ne modifie jamais l'état de la machine.** En particulier il n'exécute pas
`apt update` : cela demande les droits root et réécrit `/var/lib/apt/lists`, ce qu'un tableau
de bord en lecture seule n'a pas à faire. Conséquence assumée : le nombre de paquets reflète
la dernière fois que les listes ont été rafraîchies, pas l'état réel des dépôts. C'est
pourquoi l'ancienneté de ces listes est mesurée et affichée à côté du compteur — un chiffre
issu de listes vieilles de trois semaines est un chiffre qui ment.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

import httpx

from . import docker_api

APT_LISTS = Path("/var/lib/apt/lists")

# Un registre peut répondre avec l'un ou l'autre de ces types ; les demander tous évite
# d'obtenir un digest qui ne correspondra jamais à celui stocké localement.
MANIFEST_ACCEPT = ", ".join(
    [
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    ]
)


# --------------------------------------------------------------------------- APT


def _lists_age_days() -> float | None:
    """Ancienneté du rafraîchissement des listes APT, d'après le fichier le plus récent."""
    try:
        newest = max((p.stat().st_mtime for p in APT_LISTS.glob("*_Packages*")), default=None)
    except OSError:
        return None
    return round((time.time() - newest) / 86400, 1) if newest else None


async def apt() -> dict:
    try:
        process = await asyncio.create_subprocess_exec(
            "apt", "list", "--upgradable",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=30.0)
    except Exception:
        return {"available": False, "total": 0, "security": 0, "lists_age_days": None, "packages": []}

    packages = []
    for line in stdout.decode("utf-8", "replace").splitlines():
        if "/" not in line or "upgradable from" not in line:
            continue  # ignore l'en-tête « Listing… »
        name = line.split("/", 1)[0]
        # Le dépôt d'origine suit le « / » : `bsdutils/stable-security 2.41…`
        origin = line.split("/", 1)[1].split(" ", 1)[0]
        packages.append({"name": name, "security": "security" in origin})

    security = sum(1 for p in packages if p["security"])
    return {
        "available": True,
        "total": len(packages),
        "security": security,
        "lists_age_days": _lists_age_days(),
        "packages": [p["name"] for p in packages if p["security"]][:10],
    }


# ------------------------------------------------------------------------ Docker


def _split_image(reference: str) -> tuple[str, str, str] | None:
    """`ghcr.io/foo/bar:stable` -> (registre, dépôt, tag). None si non analysable."""
    if "@" in reference:
        reference = reference.split("@", 1)[0]
    name, _, tag = reference.rpartition(":")
    if not name or "/" in tag:  # pas de tag : le « : » appartenait au port du registre
        name, tag = reference, "latest"

    head, _, rest = name.partition("/")
    if rest and ("." in head or ":" in head or head == "localhost"):
        return head, rest, tag
    # Docker Hub : les images officielles vivent sous `library/`
    return "registry-1.docker.io", name if "/" in name else f"library/{name}", tag


async def _token(client: httpx.AsyncClient, registry: str, repository: str) -> str | None:
    if registry == "registry-1.docker.io":
        url = "https://auth.docker.io/token"
        params = {"service": "registry.docker.io", "scope": f"repository:{repository}:pull"}
    elif registry == "ghcr.io":
        url = "https://ghcr.io/token"
        params = {"service": "ghcr.io", "scope": f"repository:{repository}:pull"}
    else:
        return None
    try:
        response = await client.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        return response.json().get("token")
    except Exception:
        return None


async def _remote_digest(client: httpx.AsyncClient, reference: str) -> str | None:
    parts = _split_image(reference)
    if parts is None:
        return None
    registry, repository, tag = parts
    token = await _token(client, registry, repository)
    if token is None:
        return None
    try:
        response = await client.head(
            f"https://{registry}/v2/{repository}/manifests/{tag}",
            headers={"Accept": MANIFEST_ACCEPT, "Authorization": f"Bearer {token}"},
            timeout=15.0,
            follow_redirects=True,
        )
        return response.headers.get("Docker-Content-Digest")
    except Exception:
        return None


async def docker_images() -> dict:
    """Compare le digest local de chaque image à celui publié par son registre.

    Une image construite localement (`claudebox`) n'a pas de `RepoDigests` : elle est ignorée
    proprement et signalée comme « locale », jamais comptée comme à mettre à jour.

    Passe par le transport partagé (`HOMEPORT_DOCKER_HOST`) comme le reste de l'intégration
    Docker. **Le socket-proxy doit exposer `IMAGES: 1`** : sous le seul `CONTAINERS: 1` il
    refuse `/images/…` par un 403, et la fonction rend `available: False` — l'inspection des
    conteneurs, elle, continue de marcher.
    """
    try:
        async with docker_api.open_client(timeout=10.0) as docker:
            containers = (await docker.get("/containers/json")).json()
            images = sorted({c["Image"] for c in containers})
            details = await asyncio.gather(
                *(docker.get(f"/images/{i}/json") for i in images),
                return_exceptions=True,
            )
    except Exception:
        return {"available": False, "outdated": 0, "checked": 0, "images": []}

    # Un refus du proxy est un 403, pas une exception : sans cette distinction, chaque image
    # illisible passerait pour « construite localement » et la vue annoncerait un contrôle
    # qui n'a jamais eu lieu. Digest absent (image locale) et image illisible sont deux
    # choses différentes, et une seule des deux est une vérité sur la machine.
    local: dict[str, str | None] = {}
    unreadable: set[str] = set()
    for reference, response in zip(images, details, strict=True):
        if isinstance(response, Exception) or response.status_code != 200:
            local[reference] = None
            unreadable.add(reference)
            continue
        digests = response.json().get("RepoDigests") or []
        local[reference] = digests[0].split("@", 1)[1] if digests else None

    # Aucune image lisible = l'accès aux images n'est pas ouvert. Mieux vaut déclarer la
    # fonctionnalité indisponible que rendre une liste entièrement fausse.
    if images and len(unreadable) == len(images):
        return {"available": False, "outdated": 0, "checked": 0, "images": []}

    results = []
    async with httpx.AsyncClient() as client:
        remotes = await asyncio.gather(
            *(_remote_digest(client, ref) if local[ref] else _noop() for ref in images)
        )

    for reference, remote in zip(images, remotes, strict=True):
        current = local[reference]
        if reference in unreadable:
            state = "unknown"        # image non lisible (proxy restreint), pas « locale »
        elif current is None:
            state = "local"          # image construite sur place, pas de registre
        elif remote is None:
            state = "unknown"        # registre injoignable ou non géré
        elif remote == current:
            state = "current"
        else:
            state = "outdated"
        results.append({"image": reference, "state": state})

    return {
        "available": True,
        "outdated": sum(1 for r in results if r["state"] == "outdated"),
        "checked": sum(1 for r in results if r["state"] in ("current", "outdated")),
        "images": results,
    }


async def _noop() -> None:
    return None


# --------------------------------------------------------------------------- macOS


def parse_softwareupdate_stderr(text: str) -> list[str]:
    """`softwareupdate -l` écrit son résultat sur **stderr**, jamais stdout — vérifié
    directement sur un vrai Mac avant d'écrire ce module ; lire stdout renverrait toujours
    « aucune mise à jour », quel que soit l'état réel de la machine."""
    return [
        line.split("Label:", 1)[1].strip().rstrip(",")
        for line in text.splitlines()
        if line.strip().startswith("* Label:")
    ]


async def softwareupdate() -> dict:
    try:
        process = await asyncio.create_subprocess_exec(
            "softwareupdate", "-l",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=60.0)
    except Exception:
        return {"available": False, "total": 0, "packages": []}

    packages = parse_softwareupdate_stderr(stderr.decode("utf-8", "replace"))
    return {"available": True, "total": len(packages), "packages": packages[:10]}


def parse_brew_outdated(raw_json: str) -> list[str]:
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        return []
    return [pkg["name"] for pkg in data.get("formulae", []) + data.get("casks", [])]


async def brew_outdated() -> dict:
    """`HOMEBREW_NO_AUTO_UPDATE=1` est impératif : sans lui, `brew outdated` met à jour
    Homebrew et ses taps avant de répondre (fetch/rebase de plusieurs dépôts git, texte
    parasite sur stdout avant le JSON) — un effet de bord réseau qu'un tableau de bord en
    lecture seule ne doit jamais déclencher. Vérifié directement sur un vrai Mac."""
    env = {**os.environ, "HOMEBREW_NO_AUTO_UPDATE": "1", "HOMEBREW_NO_ENV_HINTS": "1"}
    try:
        process = await asyncio.create_subprocess_exec(
            "brew", "outdated", "--json",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, env=env,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=30.0)
    except Exception:
        return {"available": False, "total": 0, "packages": []}

    packages = parse_brew_outdated(stdout.decode("utf-8", "replace"))
    return {"available": True, "total": len(packages), "packages": packages[:10]}


# --- Nouvelle version de Homeport (GitHub Releases) -------------------------------------
# Le « système de mise à jour » côté dashboard : un contrôle quotidien opt-out
# (`intervals: {update_check: 0}` le coupe), qui compare la version locale au dernier tag
# publié. La mise à jour elle-même reste un geste volontaire : `sudo ./deploy/update.sh`.

RELEASES_URL = "https://api.github.com/repos/vincentlauriat/homeport/releases/latest"


def parse_latest_release(payload: str) -> str | None:
    """`tag_name` du JSON de l'API GitHub, sans le préfixe `v`. None si illisible."""
    try:
        tag = json.loads(payload).get("tag_name") or ""
    except (json.JSONDecodeError, AttributeError):
        return None
    return tag.lstrip("v") or None


def update_summary(current: str, latest: str | None) -> dict:
    return {
        "current": current,
        "latest": latest,
        "available": latest is not None and latest != current,
    }


async def latest_release() -> str | None:
    """Interroge l'API GitHub — seul autre appel sortant de Homeport avec l'IP publique,
    tous deux désactivables. Échec silencieux : pas de réseau = pas de badge."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(RELEASES_URL, headers={"Accept": "application/vnd.github+json"})
        if response.status_code != 200:
            return None
        return parse_latest_release(response.text)
    except httpx.HTTPError:
        return None
