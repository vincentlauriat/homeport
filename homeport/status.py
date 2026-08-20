"""Agrégation : croise les collecteurs avec l'inventaire pour produire l'état des services."""

from __future__ import annotations

import asyncio
import sqlite3
import time

from . import __version__, background, i18n
from . import config as cfg
from .collectors import cron, devices, docker_api, nvme, oui, probes, statusfile, system, wan
from .collectors import systemd as systemd_collector
from .collectors import updates as updates_collector
from .links import build_url

# États possibles, du meilleur au pire.
UP, WARN, DOWN, UNKNOWN = "up", "warn", "down", "unknown"

def state_label(state: str, lang: str) -> str:
    return i18n.t(f"state.{state}", lang)

_CACHE_TTL = 3.0
_cache: dict = {}
_cache_time = 0.0
_lock = asyncio.Lock()


def _docker_state(entry: dict | None) -> str:
    if entry is None:
        return UNKNOWN
    return {"running": UP, "restarting": WARN, "paused": WARN, "created": WARN}.get(
        entry.get("state", ""), DOWN
    )


def _systemd_state(entry: dict | None) -> str:
    if entry is None:
        return UNKNOWN
    return {"active": UP, "activating": WARN, "reloading": WARN, "deactivating": WARN}.get(
        entry.get("active_state", ""), DOWN
    )


_SEVERITY = {DOWN: 0, WARN: 1, UNKNOWN: 2, UP: 3}


def _sort_by_severity(items: list[dict]) -> list[dict]:
    """Les services en panne remontent en haut de leur groupe. Tri stable : à sévérité égale,
    l'ordre déclaré dans `services.yaml` est conservé."""
    return sorted(items, key=lambda item: _SEVERITY.get(item["state"], len(_SEVERITY)))


def _combine(states: list[str]) -> str:
    """État global d'un service à partir de ses sources.

    Tout d'accord sur `up` -> `up`. Sources en désaccord -> `warn` : c'est le cas d'un
    conteneur `running` dont l'application ne répond plus, exactement ce qu'un simple
    `docker ps` masque.
    """
    known = [s for s in states if s != UNKNOWN]
    if not known:
        return UNKNOWN
    if all(s == UP for s in known):
        return UP
    if all(s == DOWN for s in known):
        return DOWN
    return WARN


async def _probe_service(service: cfg.Service) -> str:
    probe = service.probe
    if probe is None:
        return UNKNOWN
    if probe.type == "http":
        alive = await probes.http(probe.port, scheme=probe.scheme, path=probe.path)
    else:
        alive = await probes.tcp(probe.port)
    return UP if alive else DOWN


async def build(hostname: str) -> dict:
    """Construit l'état complet. Le résultat est mis en cache quelques secondes pour qu'un
    onglet laissé ouvert (ou plusieurs) ne martèle pas le socket Docker et systemd."""
    global _cache, _cache_time

    async with _lock:
        now = time.monotonic()
        if _cache and now - _cache_time < _CACHE_TTL:
            snapshot = _cache
        else:
            snapshot = await _snapshot()
            _cache, _cache_time = snapshot, now

    # Les liens dépendent de l'hôte de la requête : recalculés hors cache.
    return _with_links(snapshot, hostname)


async def _snapshot() -> dict:
    groups = cfg.load_groups()
    services = cfg.all_services(groups)
    units = [s.systemd for s in services if s.systemd]

    containers, units_state, probe_results = await asyncio.gather(
        docker_api.collect(),
        systemd_collector.collect(units),
        asyncio.gather(*(_probe_service(s) for s in services)),
    )

    probe_by_id = {s.id: state for s, state in zip(services, probe_results, strict=True)}

    # Calculés une fois pour tout l'instantané : `_extra_info()` s'en sert pour quelques
    # tuiles seulement, mais lire les crontabs ou relire le résultat de fond une fois par
    # service reviendrait à le faire 14 fois pour la même réponse.
    network_data = _network()
    availability_raw = background.snapshot().get("availability")
    availability = (availability_raw or {}).get("data") or {}
    cron_jobs = cron.collect()
    lang = cfg.load_language()
    ssh_sessions = _ssh_sessions()
    container_cpu = _container_cpu()

    rendered_groups = []
    counters = {UP: 0, WARN: 0, DOWN: 0, UNKNOWN: 0}

    for group in groups:
        items = []
        for service in group.services:
            container = containers.get(service.docker) if service.docker else None
            unit = units_state.get(service.systemd) if service.systemd else None
            probe_state = probe_by_id[service.id]

            state = _combine([_docker_state(container), _systemd_state(unit), probe_state])
            counters[state] += 1

            items.append(
                {
                    "id": service.id,
                    "name": service.name,
                    "icon": service.icon,
                    "description": service.description,
                    "state": state,
                    "state_label": state_label(state, lang),
                    "sources": _source_rows(container, unit, probe_state, service),
                    "extra": _extra_info(service, containers, unit, network_data, cron_jobs, ssh_sessions),
                    "uptime": (container or {}).get("uptime", ""),
                    "image": (container or {}).get("image", ""),
                    "ports": (container or {}).get("ports", []),
                    "cpu_percent": container_cpu.get(service.docker) if service.docker else None,
                    "container": service.docker,
                    "restartable": service.restartable,
                    "availability": availability.get(service.id),
                    "_link": service.link,
                }
            )
        rendered_groups.append({"name": group.name, "services": _sort_by_severity(items)})

    return {
        "groups": rendered_groups,
        "summary": {
            "up": counters[UP],
            "warn": counters[WARN],
            "down": counters[DOWN],
            "unknown": counters[UNKNOWN],
            "total": len(services),
        },
        "system": system.collect(cfg.load_health()["disks"]),
        "docker_available": await docker_api.is_available(),
        # Mesures lentes : simple lecture du dernier résultat des boucles de fond, jamais
        # d'attente. `None` signifie « pas encore mesuré », pas « rien à signaler ».
        "health": _health(),
        "network": network_data,
        # Lecture d'un simple fichier JSON (écrit par le timer root), rapide : hors boucle de fond.
        "nvme": nvme.collect(cfg.NVME_PATH),
        "wan": _wan_summary(),
        "public_ip": (background.snapshot().get("public_ip") or {}).get("data"),
        "status_files": [statusfile.collect(e) for e in cfg.load_health()["status_files"]],
        "update": updates_collector.update_summary(
            __version__, (background.snapshot().get("update_check") or {}).get("data")
        ),
    }


def _health() -> dict:
    """Assemble les mesures de fond en une section prête à afficher."""
    raw = background.snapshot()
    lang = cfg.load_language()

    def value(key):
        entry = raw.get(key)
        return entry.get("data") if entry else None

    def measured_at(key):
        entry = raw.get(key)
        return entry.get("measured_at") if entry else None

    backups = value("backups") or []
    journal = value("journal")
    apt = value("apt")
    images = value("docker_images")
    throttling = value("throttling")

    alerts = []
    for backup in backups:
        if backup["state"] == "never":
            alerts.append({"level": "down", "text": i18n.t("alert.backup_never", lang, name=backup["name"])})
        elif backup["state"] == "warn":
            alerts.append({"level": "warn", "text": i18n.t("alert.backup_stale", lang, name=backup["name"], detail=backup["detail"])})
    if apt and apt.get("security"):
        alerts.append({"level": "warn", "text": i18n.t("alert.apt_security", lang, count=apt["security"])})
    if apt and (age := apt.get("lists_age_days")) is not None and age > 14:
        # Un compteur calculé sur des listes périmées annonce un chiffre faux.
        alerts.append({"level": "warn", "text": i18n.t("alert.apt_lists", lang, count=f"{age:.0f}")})
    if throttling and throttling.get("available"):
        # Le passé compte autant que le présent : une sous-tension de trente secondes cette
        # nuit n'apparaît nulle part ailleurs et menace la carte SD.
        for label in throttling["now"]:
            alerts.append({"level": "down", "text": i18n.t("alert.throttle_now", lang, label=label)})
        for label in throttling["since_boot"]:
            alerts.append({"level": "warn", "text": i18n.t("alert.throttle_boot", lang, label=label)})
    for sf in [statusfile.collect(e) for e in cfg.load_health()["status_files"]]:
        if sf["level"] != "up":
            text = sf["message"] or (i18n.t("statusfile.stale", lang) if sf["stale"] else sf["status"])
            alerts.append({"level": sf["level"] if sf["level"] == "down" else "warn",
                           "text": f"{sf['name']} : {text}" if lang == "fr" else f"{sf['name']}: {text}"})
    if images and images.get("outdated"):
        names = ", ".join(i["image"] for i in images["images"] if i["state"] == "outdated")
        alerts.append({"level": "warn", "text": i18n.t("alert.images", lang, names=names)})

    return {
        "backups": backups,
        "backups_measured_at": measured_at("backups"),
        "journal": journal,
        "journal_measured_at": measured_at("journal"),
        "apt": apt,
        "apt_measured_at": measured_at("apt"),
        "images": images,
        "images_measured_at": measured_at("docker_images"),
        "throttling": throttling,
        "alerts": alerts,
    }


def _wan_summary() -> dict | None:
    """Synthèse Internet — dérivée de l'historique SQLite (job de fond `wan`, 60 s).
    Requête légère (≤ 1440 lignes/24 h) derrière le cache de 3 s du snapshot."""
    try:
        return wan.summarize(cfg.DB_PATH)
    except sqlite3.Error:
        return None


def _network() -> dict:
    """Pairs Tailscale et voisins LAN — mesurés en tâche de fond (voir `background.py`),
    jamais dans le chemin d'une requête (un sous-processus par requête ralentirait la page)."""
    raw = background.snapshot().get("network")
    data = raw.get("data") if raw else None
    # Compteur « nouveaux appareils » pour la tuile et le capteur MQTT. La base peut être
    # absente (SSD démonté) : l'inventaire est optionnel, le snapshot réseau ne l'est pas.
    try:
        pending = devices.unacknowledged(cfg.DB_PATH)
        new_devices = {
            "count": len(pending),
            "names": [devices.display_name(d, oui.vendor(d["mac"]))[0] for d in pending[:10]],
        }
    except sqlite3.Error:
        new_devices = {"count": None, "names": []}
    return {
        "tailscale_peers": (data or {}).get("tailscale_peers", []),
        "tailscale_summary": (data or {}).get("tailscale_summary") or {},
        "lan_neighbors": (data or {}).get("lan_neighbors", []),
        "measured_at": raw.get("measured_at") if raw else None,
        "new_devices": new_devices,
    }


def _ssh_sessions() -> list[dict]:
    """Sessions SSH actives — mesurées en tâche de fond (`who` est un sous-processus, voir
    `collectors/sessions.py`), même logique que `_network()`."""
    raw = background.snapshot().get("sessions")
    return (raw.get("data") if raw else None) or []


def _container_cpu() -> dict:
    """{nom_conteneur: % CPU} — mesuré en tâche de fond (`stats` bloque ~1 s par conteneur,
    voir `collectors/docker_api.py`), jamais dans le chemin d'une requête."""
    raw = background.snapshot().get("docker_stats")
    return (raw.get("data") if raw else None) or {}


def _source_rows(container: dict | None, unit: dict | None, probe_state: str, service: cfg.Service) -> list[dict]:
    """Version structurée de `_detail()` — une ligne par source, pour l'affichage en
    mini-tableau plutôt qu'en phrase (carte de service dépliée)."""
    rows = []
    if service.docker:
        ok = bool(container) and container.get("state") == "running"
        rows.append({"label": "docker", "value": container["state"] if container else i18n.t("source.absent", cfg.load_language()), "ok": ok})
    if service.systemd:
        ok = bool(unit) and unit.get("active_state") == "active"
        rows.append({"label": "systemd", "value": unit["active_state"] if unit else i18n.t("source.unknown", cfg.load_language()), "ok": ok})
    if service.probe:
        ok = probe_state == UP
        rows.append({"label": f"port {service.probe.port}", "value": i18n.t("source.answers" if ok else "source.silent", cfg.load_language()), "ok": ok})
    return rows


def _extra_info(
    service: cfg.Service,
    containers: dict,
    unit: dict | None,
    network_data: dict,
    cron_jobs: list[dict],
    ssh_sessions: list[dict],
) -> list[dict]:
    """Contenu spécifique à quelques tuiles du groupe Système, en plus des sources génériques.

    Se contente des données déjà collectées ailleurs (conteneurs, minuteur, réseau) plus deux
    lectures dédiées bon marché (crontabs, sessions SSH) — jamais rien qui suppose un service ou
    un droit absent de cet hôte (Avahi, NFS : aucun outil client/serveur disponible pour aller
    plus loin, donc aucune ligne ajoutée plutôt qu'un contenu inventé).

    Une ligne « démarré » (date de démarrage de l'unité) est ajoutée en fin de liste pour tout
    service systemd qui en a une — y compris ceux sans contenu id-spécifique (Avahi, NFS)."""
    rows: list[dict] = []

    if service.id == "docker":
        running = sum(1 for c in containers.values() if c.get("state") == "running")
        rows.append({"label": "conteneurs", "value": f"{running} actif(s) / {len(containers)} au total"})

    elif service.id == "tailscale":
        summary = network_data.get("tailscale_summary") or {}
        if summary.get("version"):
            rows.append({"label": "version", "value": summary["version"]})
        rows.append(
            {
                "label": "pairs",
                "value": f"{summary.get('peers_online', 0)}/{summary.get('peers_total', 0)} en ligne",
            }
        )

    elif service.id == "ssh":
        if not ssh_sessions:
            rows.append({"label": "sessions", "value": "aucune"})
        else:
            hosts = ", ".join(s["host"] for s in ssh_sessions)
            rows.append({"label": "sessions", "value": f"{len(ssh_sessions)} active(s) — {hosts}"})

    elif service.id == "cron":
        rows += [{"label": job["schedule"], "value": job["command"]} for job in cron_jobs]

    elif (service.systemd or "").endswith(".timer"):
        # Vaut pour tout minuteur (sauvegarde, mises à jour auto…) : les propriétés next/last
        # viennent du même appel `systemctl show` que le reste, sans coût supplémentaire.
        if unit and unit.get("next_run"):
            rows.append({"label": "prochaine", "value": unit["next_run"]})
        if unit and unit.get("last_run"):
            rows.append({"label": "dernière", "value": unit["last_run"]})

    if service.systemd and unit and unit.get("since"):
        rows.append({"label": "démarré", "value": unit["since"]})

    return rows


def _with_links(snapshot: dict, hostname: str) -> dict:
    """Recompose les URLs sur l'hôte courant (LAN ou Tailscale) — voir app/links.py."""
    groups = []
    for group in snapshot["groups"]:
        services = []
        for service in group["services"]:
            item = {k: v for k, v in service.items() if k != "_link"}
            link = service["_link"]
            item["url"] = build_url(link, hostname) if link else None
            services.append(item)
        groups.append({"name": group["name"], "services": services})
    return {**snapshot, "groups": groups}
