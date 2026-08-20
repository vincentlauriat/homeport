"""Résolution des URLs de services à partir de l'hôte de la requête.

Le principe : Homeport ne code aucune URL en dur. Si tu ouvres le dashboard sur
`http://192.168.68.56/`, les liens pointent vers `192.168.68.56` ; si tu l'ouvres sur
`http://homeserver.example.ts.net/` via Tailscale, ils pointent vers ce nom-là.
Un seul jeu de configuration couvre donc le LAN et le tailnet.
"""

from __future__ import annotations

from .config import Link


def request_hostname(host_header: str | None, fallback: str = "localhost") -> str:
    """Extrait le nom d'hôte de l'en-tête `Host`, port éventuel retiré.

    Gère les adresses IPv6 littérales (`[fd7a::1]:80`).
    """
    if not host_header:
        return fallback
    host = host_header.strip()
    if host.startswith("["):  # IPv6 littéral
        end = host.find("]")
        return host[: end + 1] if end != -1 else host
    return host.rsplit(":", 1)[0] if ":" in host else host


def build_url(link: Link, hostname: str) -> str:
    """Recompose l'URL d'un service sur l'hôte courant."""
    netloc = hostname if link.port is None else f"{hostname}:{link.port}"
    path = link.path if link.path.startswith("/") else f"/{link.path}"
    return f"{link.scheme}://{netloc}{path}"
