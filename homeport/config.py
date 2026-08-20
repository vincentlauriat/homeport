"""Chargement de l'inventaire des services (config/services.yaml)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Résolution des répertoires, dans l'ordre : variable d'environnement, emplacement FHS
# (/etc/homeport, /var/lib/homeport) s'il est utilisable, sinon repli développement relatif
# au répertoire courant (./config, ./data). Chaque fichier individuel reste surchargeable.
_ETC = Path("/etc/homeport")
_VAR = Path("/var/lib/homeport")


def _resolve_dir(env_var: str, system: Path, dev_name: str, need_write: bool) -> Path:
    override = os.environ.get(env_var)
    if override:
        return Path(override)
    usable = system.is_dir() and (not need_write or os.access(system, os.W_OK))
    return system if usable else Path.cwd() / dev_name


CONFIG_DIR = _resolve_dir("HOMEPORT_CONFIG_DIR", _ETC, "config", need_write=False)
DATA_DIR = _resolve_dir("HOMEPORT_DATA_DIR", _VAR, "data", need_write=True)

CONFIG_PATH = Path(os.environ.get("HOMEPORT_CONFIG", CONFIG_DIR / "services.yaml"))
DB_PATH = Path(os.environ.get("HOMEPORT_DB_PATH", DATA_DIR / "history.db"))

# Écrit par le timer root `homeport-nvme.timer` (voir collectors/nvme.py), lu seulement.
NVME_PATH = Path(os.environ.get("HOMEPORT_NVME_PATH", DATA_DIR / "nvme.json"))



def _read_yaml(source: Path) -> dict:
    """Fichier absent = config vide : Homeport démarre sain sans aucune configuration
    (dashboard vide), plutôt que d'échouer avant même de pouvoir aider."""
    try:
        return yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return {}


@dataclass(frozen=True)
class Link:
    scheme: str = "http"
    port: int | None = None
    path: str = "/"


@dataclass(frozen=True)
class Probe:
    type: str = "tcp"  # "tcp" | "http"
    port: int = 0
    scheme: str = "http"
    path: str = "/"


@dataclass(frozen=True)
class Service:
    id: str
    name: str
    icon: str = "•"
    description: str = ""
    docker: str | None = None
    systemd: str | None = None
    link: Link | None = None
    probe: Probe | None = None
    # Redémarrable depuis le dashboard par l'admin (identité Tailscale) — voir app/actions.py.
    # Défaut False : rien n'est redémarrable sans déclaration explicite dans services.yaml.
    restartable: bool = False


@dataclass(frozen=True)
class Group:
    name: str
    services: list[Service] = field(default_factory=list)


def _service_from_dict(raw: dict) -> Service:
    link = Link(**raw["link"]) if raw.get("link") else None
    probe = Probe(**raw["probe"]) if raw.get("probe") else None
    return Service(
        id=raw["id"],
        name=raw["name"],
        icon=raw.get("icon", "•"),
        description=raw.get("description", ""),
        docker=raw.get("docker"),
        systemd=raw.get("systemd"),
        link=link,
        probe=probe,
        restartable=bool(raw.get("restartable", False)),
    )


def load_groups(path: Path | None = None) -> list[Group]:
    """Lit le YAML et le convertit en objets. Relu à chaque appel : éditer le fichier
    et rafraîchir la page suffit, aucun redémarrage nécessaire."""
    source = path or CONFIG_PATH
    data = _read_yaml(source)
    return [
        Group(name=g["name"], services=[_service_from_dict(s) for s in g.get("services", [])])
        for g in data.get("groups", [])
    ]


def all_services(groups: list[Group]) -> list[Service]:
    return [s for g in groups for s in g.services]


DEFAULT_INTERVALS = {
    "backups": 300,
    "journal": 180,
    "throttling": 60,
    "apt": 1800,
    "docker_images": 3600,
    "history": 300,
    "network": 60,
    "sessions": 60,
    "docker_stats": 30,
    "mdns": 300,
    "wan": 60,
    "service_states": 60,
    "availability": 300,
    "public_ip": 3600,
}
DEFAULT_HISTORY_RETENTION_DAYS = 7
DEFAULT_LANGUAGE = "en"


def load_language(path: Path | None = None) -> str:
    """Clé `language:` au sommet du fichier de config, surchargeable par HOMEPORT_LANG."""
    override = os.environ.get("HOMEPORT_LANG")
    if override:
        return override
    return _read_yaml(path or CONFIG_PATH).get("language") or DEFAULT_LANGUAGE


def load_health(path: Path | None = None) -> dict:
    """Section `health:` du même fichier : sauvegardes surveillées, filtres du journal,
    cadence des mesures de fond."""
    source = path or CONFIG_PATH
    data = _read_yaml(source)
    health = data.get("health") or {}
    history = health.get("history") or {}
    return {
        "backups": health.get("backups", []),
        "disks": health.get("disks") or ["/"],
        "journal": health.get("journal", {}) or {},
        "updates": health.get("updates", {}) or {},
        "intervals": {**DEFAULT_INTERVALS, **(health.get("intervals") or {})},
        "history_retention_days": history.get("retention_days", DEFAULT_HISTORY_RETENTION_DAYS),
    }


def load_actions(path: Path | None = None) -> dict:
    """Section `actions:` du même fichier — l'identité Tailscale admin autorisée à agir.
    `admin: None` désactive toutes les actions : sûr par défaut."""
    source = path or CONFIG_PATH
    data = _read_yaml(source)
    section = data.get("actions") or {}
    return {"admin": section.get("admin")}


DEFAULT_MQTT = {
    "enabled": False,
    "host": "127.0.0.1",
    "port": 1883,
    "base_topic": "homeport",
    "discovery_prefix": "homeassistant",
    "interval": 60,
}


def load_mqtt(path: Path | None = None) -> dict:
    """Section `mqtt:` du même fichier.

    Aucun identifiant ici : le fichier est versionné. Nom d'utilisateur et mot de passe
    viennent de `HOMEPORT_MQTT_USERNAME` / `HOMEPORT_MQTT_PASSWORD`, que systemd charge depuis
    `/etc/homeport/mqtt.env` (root, 600, hors dépôt).
    """
    source = path or CONFIG_PATH
    data = _read_yaml(source)
    return {**DEFAULT_MQTT, **(data.get("mqtt") or {})}
