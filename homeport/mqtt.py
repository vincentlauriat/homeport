"""Publication de l'état sur MQTT avec découverte automatique Home Assistant.

Pourquoi passer par MQTT plutôt qu'écrire un système d'alerte dans Homeport : Home Assistant
est déjà installé sur cette machine, avec ses automatisations, ses notifications et son
historique. Republier l'état sous une forme qu'il comprend lui délègue tout ça — Homeport reste
un tableau de bord, il ne devient pas un système de notification de plus à configurer.

Un seul message d'état porte toutes les valeurs (`homeport/state`), et chaque entité y pioche
son champ via `value_template`. Alternative écartée : un topic par entité, soit vingt messages
là où un seul suffit, et vingt occasions d'être partiellement à jour.

Limite à connaître : le courtier, Home Assistant et Homeport tournent sur la **même machine**.
Ce canal signale un service tombé, une sauvegarde en retard ou une sous-tension — il ne
signalera jamais que le Pi lui-même est mort. Le testament (LWT) couvre le seul cas
intermédiaire : Homeport s'arrête alors que le reste tourne.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from . import config as cfg
from . import i18n

try:  # pragma: no cover - dépend de l'environnement d'installation
    import paho.mqtt.client as paho
except ImportError:  # une dépendance optionnelle manquante ne doit pas empêcher le site de démarrer
    paho = None

log = logging.getLogger("homeport.mqtt")

ONLINE, OFFLINE = "online", "offline"


# --------------------------------------------------------------------------------------
# Description des entités
#
# Une entité = une ligne. `template` est du Jinja2 évalué par Home Assistant sur le message
# d'état, pas par Python. `unique_id` est indispensable : sans lui Home Assistant interdit de
# renommer l'entité dans l'interface, et le retrouver après coup casserait les automatisations.
# --------------------------------------------------------------------------------------

# (clé, nom, template, unité, device_class, state_class, icône)
SENSORS: list[tuple[str, str, str, str | None, str | None, str | None, str | None]] = [
    ("services_down", "mqttname.services_down", "{{ value_json.services.down }}", None, None, "measurement", "mdi:alert-circle"),
    ("services_warn", "mqttname.services_warn", "{{ value_json.services.warn }}", None, None, "measurement", "mdi:alert"),
    ("services_up", "mqttname.services_up", "{{ value_json.services.up }}", None, None, "measurement", "mdi:check-circle"),
    ("alerts", "mqttname.alerts", "{{ value_json.alerts.count }}", None, None, "measurement", "mdi:bell-alert"),
    ("backup_age", "mqttname.backup_age", "{{ value_json.backups.oldest_age_days }}", "d", "duration", "measurement", "mdi:backup-restore"),
    ("apt_updates", "mqttname.apt_updates", "{{ value_json.updates.apt_total }}", None, None, "measurement", "mdi:package-up"),
    ("apt_security", "mqttname.apt_security", "{{ value_json.updates.apt_security }}", None, None, "measurement", "mdi:shield-alert"),
    ("docker_outdated", "mqttname.docker_outdated", "{{ value_json.updates.docker_outdated }}", None, None, "measurement", "mdi:docker"),
    ("journal_errors", "mqttname.journal_errors", "{{ value_json.journal.errors }}", None, None, "measurement", "mdi:text-box-search"),
    ("new_devices", "mqttname.new_devices", "{{ value_json.network.new_devices }}", None, None, "measurement", "mdi:lan-pending"),
    ("wan_latency", "mqttname.wan_latency", "{{ value_json.wan.latency_ms }}", "ms", None, "measurement", "mdi:speedometer"),
    ("wan_outages", "mqttname.wan_outages", "{{ value_json.wan.outages_24h }}", None, None, "measurement", "mdi:wan"),
    ("ssd_wear", "mqttname.ssd_wear", "{{ value_json.system.ssd_wear_pct }}", "%", None, "measurement", "mdi:harddisk"),
    ("public_ip", "mqttname.public_ip", "{{ value_json.public_ip }}", None, None, None, "mdi:ip-outline"),
    ("cpu_temperature", "mqttname.cpu_temperature", "{{ value_json.system.cpu_temperature_c }}", "°C", "temperature", "measurement", None),
    ("nvme_temperature", "mqttname.nvme_temperature", "{{ value_json.system.storage_temperature_c }}", "°C", "temperature", "measurement", None),
    ("fan", "mqttname.fan", "{{ value_json.system.fan_rpm }}", "rpm", None, "measurement", "mdi:fan"),
    ("cpu_load", "mqttname.cpu_load", "{{ value_json.system.cpu_percent }}", "%", None, "measurement", "mdi:cpu-64-bit"),
    ("memory", "mqttname.memory", "{{ value_json.system.memory_percent }}", "%", None, "measurement", "mdi:memory"),
    # Un uptime en secondes s'affiche « 176 938,00 s » : illisible. Home Assistant rend en
    # revanche un horodatage en relatif (« il y a 2 jours »), d'où la date de démarrage plutôt
    # que la durée — c'est aussi ce que fait son intégration System Monitor.
    ("uptime", "mqttname.uptime", "{{ (value_json.timestamp | int - value_json.system.uptime_seconds | int) | as_datetime }}", None, "timestamp", None, "mdi:clock-outline"),
    # `timestamp` en device_class exige une date **avec fuseau** : `as_datetime` sur un entier
    # Unix rend un datetime UTC conscient de son fuseau, là où `timestamp_utc` rendrait une
    # chaîne sans fuseau que Home Assistant rejetterait.
    ("updated", "mqttname.updated", "{{ value_json.timestamp | int | as_datetime }}", None, "timestamp", None, "mdi:update"),
]

# (clé, nom, template, device_class, icône)
BINARY_SENSORS: list[tuple[str, str, str, str | None, str | None]] = [
    ("problem", "mqttname.problem", "{{ 'ON' if value_json.problem else 'OFF' }}", "problem", None),
    ("backup_late", "mqttname.backup_late", "{{ 'ON' if value_json.backups.late else 'OFF' }}", "problem", "mdi:backup-restore"),
    ("undervoltage", "mqttname.undervoltage", "{{ 'ON' if value_json.system.undervoltage else 'OFF' }}", "problem", "mdi:flash-alert"),
    ("throttling", "mqttname.throttling", "{{ 'ON' if value_json.system.throttling else 'OFF' }}", "problem", "mdi:speedometer-slow"),
    # Le signal le plus précieux du lot : une sous-tension de trente secondes cette nuit ne
    # laisse aucune autre trace, et elle a disparu quand on regarde le capteur instantané.
    # Il lui faut donc son entité propre — noyé dans le compteur d'alertes, il serait invisible.
    ("throttled_since_boot", "mqttname.throttled_since_boot", "{{ 'ON' if value_json.system.throttling_since_boot else 'OFF' }}", "problem", "mdi:history"),
]

# Attributs supplémentaires, par clé d'entité. Une liste ne peut pas être l'état d'une entité
# Home Assistant ; en attribut, elle transforme « Problème détecté » en « eufy-security-ws hors
# service » dans le texte d'une notification.
EXTRAS: dict[str, dict] = {
    "problem": {
        "json_attributes_template": (
            "{{ {'alertes': value_json.alerts.text, "
            "'services_en_defaut': value_json.services.failing} | tojson }}"
        )
    }
}


def _device(hostname: str) -> dict:
    """Bloc `device` partagé : sans lui, Home Assistant afficherait vingt entités orphelines
    au lieu d'une seule page d'appareil."""
    model = "Raspberry Pi"
    try:
        raw = Path("/proc/device-tree/model").read_text(encoding="utf-8", errors="replace")
        model = raw.replace("\x00", "").strip() or model
    except OSError:
        pass
    return {
        "identifiers": ["homeport"],
        "name": f"Homeport ({hostname})",
        "manufacturer": "Raspberry Pi Foundation",
        "model": model,
        "configuration_url": f"http://{hostname}/",
    }


def _slug(mountpoint: str) -> str:
    return "root" if mountpoint == "/" else mountpoint.strip("/").replace("/", "_")


# --------------------------------------------------------------------------------------
# Charge utile
# --------------------------------------------------------------------------------------


def _undervoltage(system: dict, throttling: dict) -> bool:
    """Sous-tension **en cours**, la première cause de corruption de carte SD sur Pi.

    Deux sources pour la même chose : l'alarme hwmon (lue sans processus, à jour à la seconde)
    et le bit 0 de `vcgencmd`, rafraîchi moins souvent. La première fait foi quand elle
    existe ; la seconde évite de perdre l'information sur une machine sans `rpi_volt`.
    """
    sensor = system.get("undervoltage")
    if sensor is not None:
        return bool(sensor)
    return bool((throttling.get("bits") or 0) & 0b1)


def build_payload(snapshot: dict) -> dict:
    """Aplatit l'état du tableau de bord en un objet plat, stable, prêt pour `value_template`.

    Volontairement séparé de la publication : c'est la partie testable sans courtier.
    """
    summary = snapshot.get("summary") or {}
    system = snapshot.get("system") or {}
    health = snapshot.get("health") or {}

    backups = health.get("backups") or []
    ages = [b["age_days"] for b in backups if b.get("age_days") is not None]
    apt = health.get("apt") or {}
    images = health.get("images") or {}
    journal = health.get("journal") or {}
    throttling = health.get("throttling") or {}
    alerts = health.get("alerts") or []

    return {
        "services": {
            "up": summary.get("up", 0),
            "warn": summary.get("warn", 0),
            "down": summary.get("down", 0),
            "unknown": summary.get("unknown", 0),
            "total": summary.get("total", 0),
            "failing": [
                s["name"]
                for g in snapshot.get("groups", [])
                for s in g["services"]
                if s["state"] in ("down", "warn")
            ],
        },
        "alerts": {
            "count": len(alerts),
            "critical": sum(1 for a in alerts if a["level"] == "down"),
            "text": [a["text"] for a in alerts],
        },
        "backups": {
            # Le maximum, pas la moyenne : une cible à jour ne doit pas masquer une cible figée.
            "oldest_age_days": round(max(ages), 1) if ages else None,
            "late": any(b.get("state") in ("warn", "never") for b in backups),
            "targets": {b["name"]: b.get("age_days") for b in backups},
        },
        "updates": {
            "apt_total": apt.get("total"),
            "apt_security": apt.get("security"),
            "docker_outdated": images.get("outdated"),
        },
        "journal": {"errors": journal.get("counted"), "raw": journal.get("total")},
        "system": {
            "cpu_temperature_c": system.get("temperature_c"),
            "storage_temperature_c": system.get("storage_temperature_c"),
            "fan_rpm": system.get("fan_rpm"),
            "cpu_percent": (system.get("load") or {}).get("percent"),
            "memory_percent": (system.get("memory") or {}).get("percent"),
            "uptime_seconds": (system.get("uptime") or {}).get("seconds"),
            # Deux causes distinctes, deux capteurs distincts : une alimentation insuffisante
            # ne se répare pas comme une surchauffe. Le bit brut sert d'appoint quand le
            # capteur hwmon est absent — les libellés en français ne sont jamais testés.
            "undervoltage": _undervoltage(system, throttling),
            "throttling": bool((throttling.get("bits") or 0) & 0b1110),
            "throttling_since_boot": bool(throttling.get("since_boot")),
            "disks": {_slug(d["mount"]): d["percent"] for d in system.get("disks", [])},
            "ssd_wear_pct": (snapshot.get("nvme") or {}).get("percent_used"),
        },
        "public_ip": (snapshot.get("public_ip") or {}).get("ip"),
        "status_files": {
            sf["id"]: {"age_hours": sf["age_hours"], "status": sf["status"], "level": sf["level"]}
            for sf in (snapshot.get("status_files") or [])
        },
        "network": {
            "new_devices": ((snapshot.get("network") or {}).get("new_devices") or {}).get("count"),
            "new_names": ((snapshot.get("network") or {}).get("new_devices") or {}).get("names", []),
        },
        "wan": {
            "online": (snapshot.get("wan") or {}).get("online"),
            "latency_ms": (snapshot.get("wan") or {}).get("latency_ms"),
            "outages_24h": (snapshot.get("wan") or {}).get("outages_24h"),
        },
        # L'état est retenu par le courtier : sans horodatage, rien ne distingue une valeur
        # fraîche d'un dernier message vieux de trois jours laissé par un service arrêté.
        "timestamp": system.get("timestamp"),
        "problem": summary.get("down", 0) > 0 or any(a["level"] == "down" for a in alerts),
    }


def build_discovery(payload: dict, hostname: str, base: str, prefix: str) -> list[tuple[str, dict]]:
    lang = cfg.load_language()
    """(topic, configuration) pour chaque entité. Les disques sont dérivés de l'état courant :
    leur nombre dépend de ce qui est monté, il ne peut pas être écrit en dur."""
    device = _device(hostname)
    common = {
        "device": device,
        "state_topic": f"{base}/state",
        "availability_topic": f"{base}/availability",
        "payload_available": ONLINE,
        "payload_not_available": OFFLINE,
        "origin": {"name": "Homeport"},
    }
    messages: list[tuple[str, dict]] = []

    for key, name, template, unit, device_class, state_class, icon in SENSORS:
        config = {**common, "name": i18n.t(name, lang), "unique_id": f"{base}_{key}", "value_template": template}
        if unit:
            config["unit_of_measurement"] = unit
        if device_class:
            config["device_class"] = device_class
        if state_class:
            config["state_class"] = state_class
        if icon:
            config["icon"] = icon
        messages.append((f"{prefix}/sensor/{base}/{key}/config", config))

    for key, name, template, device_class, icon in BINARY_SENSORS:
        config = {
            **common,
            "name": i18n.t(name, lang),
            "unique_id": f"{base}_{key}",
            "value_template": template,
            "payload_on": "ON",
            "payload_off": "OFF",
        }
        if device_class:
            config["device_class"] = device_class
        if icon:
            config["icon"] = icon
        if extra := EXTRAS.get(key):
            # Les attributs sont extraits du message d'état déjà publié : aucun topic de plus.
            config["json_attributes_topic"] = f"{base}/state"
            config.update(extra)
        messages.append((f"{prefix}/binary_sensor/{base}/{key}/config", config))

    for sf_id in payload.get("status_files", {}):
        messages.append((
            f"{prefix}/sensor/{base}/{sf_id}_age/config",
            {
                **common,
                "name": i18n.t("mqttname.statusfile_age", lang, name=sf_id),
                "unique_id": f"{base}_{sf_id}_age",
                "value_template": f"{{{{ value_json.status_files.{sf_id}.age_hours }}}}",
                "unit_of_measurement": "h",
                "device_class": "duration",
                "state_class": "measurement",
                "icon": "mdi:cloud-upload",
            },
        ))

    for slug in payload["system"]["disks"]:
        messages.append(
            (
                f"{prefix}/sensor/{base}/disk_{slug}/config",
                {
                    **common,
                    "name": i18n.t("mqttname.disk", lang, mount=slug),
                    "unique_id": f"{base}_disk_{slug}",
                    "value_template": f"{{{{ value_json.system.disks.{slug} }}}}",
                    "unit_of_measurement": "%",
                    "state_class": "measurement",
                    "icon": "mdi:harddisk",
                },
            )
        )

    return messages


# --------------------------------------------------------------------------------------
# Boucle de publication
# --------------------------------------------------------------------------------------


class Publisher:
    def __init__(self, settings: dict, hostname: str) -> None:
        self.host = settings.get("host", "127.0.0.1")
        self.port = int(settings.get("port", 1883))
        self.base = settings.get("base_topic", "homeport").rstrip("/")
        self.prefix = settings.get("discovery_prefix", "homeassistant").rstrip("/")
        self.interval = float(settings.get("interval", 60))
        self.hostname = hostname
        self.client: Any = None
        self._discovery_sent = False

    def connect(self, username: str, password: str) -> None:
        client = paho.Client(
            paho.CallbackAPIVersion.VERSION2, client_id="homeport", protocol=paho.MQTTv311
        )
        client.username_pw_set(username, password)
        # Testament : publié par le courtier si Homeport disparaît sans se déconnecter proprement.
        client.will_set(f"{self.base}/availability", OFFLINE, qos=1, retain=True)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.connect_async(self.host, self.port, keepalive=60)
        client.loop_start()  # thread paho : gère la reconnexion automatique
        self.client = client

    def _on_connect(self, client, _userdata, _flags, reason_code, _properties=None) -> None:
        if reason_code != 0:
            log.warning("connexion MQTT refusée : %s", reason_code)
            return
        log.info("connecté à %s:%s", self.host, self.port)
        client.publish(f"{self.base}/availability", ONLINE, qos=1, retain=True)
        # Une reconnexion peut suivre un redémarrage du courtier, qui a pu perdre les messages
        # retenus : la découverte est renvoyée au prochain tour de boucle.
        self._discovery_sent = False

    def _on_disconnect(self, _client, _userdata, _flags, reason_code, _properties=None) -> None:
        if reason_code != 0:
            log.warning("déconnecté du courtier MQTT (%s), reconnexion automatique", reason_code)

    def publish(self, snapshot: dict) -> None:
        payload = build_payload(snapshot)

        if not self._discovery_sent:
            for topic, config in build_discovery(payload, self.hostname, self.base, self.prefix):
                # retain=True, sans quoi Home Assistant perd toutes les entités à son
                # redémarrage et ne les retrouve qu'au prochain envoi de découverte.
                self.client.publish(topic, json.dumps(config, ensure_ascii=False), qos=1, retain=True)
            self._discovery_sent = True
            log.info("découverte publiée sous %s/…/homeport/", self.prefix)

        # retain sur l'état aussi : au redémarrage de Home Assistant, les entités ont une valeur
        # immédiatement au lieu d'afficher « inconnu » jusqu'à la prochaine publication.
        self.client.publish(
            f"{self.base}/state", json.dumps(payload, ensure_ascii=False), qos=0, retain=True
        )

    def close(self) -> None:
        if self.client is None:
            return
        try:
            self.client.publish(f"{self.base}/availability", OFFLINE, qos=1, retain=True).wait_for_publish(2)
        except Exception:  # un arrêt ne doit jamais échouer sur une publication
            pass
        self.client.loop_stop()
        self.client.disconnect()


_task: asyncio.Task | None = None
_publisher: Publisher | None = None


async def _loop(publisher: Publisher, state_provider) -> None:
    while True:
        try:
            publisher.publish(await state_provider())
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # une publication ratée ne doit pas tuer la boucle
            log.warning("publication MQTT échouée : %s: %s", type(exc).__name__, exc)
        await asyncio.sleep(publisher.interval)


def start(settings: dict, hostname: str, state_provider) -> str | None:
    """Démarre la publication. Renvoie la raison de l'abandon, ou None si tout va bien.

    Chaque cas d'abandon est un message explicite plutôt qu'un silence : une intégration qui
    ne publie rien sans dire pourquoi est indébogable.
    """
    global _task, _publisher

    if not settings.get("enabled"):
        return None
    if paho is None:
        return "paho-mqtt n'est pas installé"

    username = os.environ.get("HOMEPORT_MQTT_USERNAME")
    password = os.environ.get("HOMEPORT_MQTT_PASSWORD")
    if not username or not password:
        return "HOMEPORT_MQTT_USERNAME / HOMEPORT_MQTT_PASSWORD absents (voir /etc/homeport/mqtt.env)"

    _publisher = Publisher(settings, hostname)
    _publisher.connect(username, password)
    _task = asyncio.create_task(_loop(_publisher, state_provider), name="homeport-mqtt")
    return None


def stop() -> None:
    global _task, _publisher
    if _task is not None:
        _task.cancel()
        _task = None
    if _publisher is not None:
        _publisher.close()
        _publisher = None
