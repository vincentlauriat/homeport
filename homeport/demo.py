"""Mode démo : le tableau de bord complet sur des données simulées, sans aucun accès système.

Activé par `HOMEPORT_DEMO=1` (voir main.py). Fournit le même contrat que `status.build()` et
les endpoints d'historique/appareils/coupures — les vues ne savent pas qu'elles regardent une
maison imaginaire. Les séries sont déterministes (fonctions du temps, pas d'aléa) : la page
vit, les captures d'écran sont reproductibles.
"""

from __future__ import annotations

import math
import time

from . import config as cfg
from . import i18n

_START = 1_700_000_000  # époque fictive stable pour les séries déterministes


def _wave(t: float, period: float, low: float, high: float, phase: float = 0.0) -> float:
    """Sinusoïde bornée — la matière première de toutes les métriques « vivantes »."""
    return low + (high - low) * (0.5 + 0.5 * math.sin(2 * math.pi * (t / period) + phase))


_SERVICES = [
    # (groupe, id, nom, icône, description, docker, port sonde, cpu, restartable)
    ("Home automation", "homeassistant", "Home Assistant", "🏠", "Automations, zones and devices", True, 8123, 6.2, True),
    ("Home automation", "mosquitto", "Mosquitto", "📡", "MQTT broker", True, 1883, 0.4, False),
    ("Home automation", "zigbee2mqtt", "Zigbee2MQTT", "💡", "Zigbee gateway", True, 8080, 1.1, True),
    ("Home automation", "camera-gw", "Camera gateway", "🎥", "RTSP restreamer", True, 8554, 3.8, True),
    ("Infrastructure", "portainer", "Portainer", "🐋", "Container administration", True, 9443, 0.3, True),
    ("Infrastructure", "adguard", "AdGuard Home", "🛡️", "DNS filtering for the LAN", True, 3000, 0.9, True),
    ("Infrastructure", "gitea", "Gitea", "🗃️", "Self-hosted git", True, 3001, 0.6, False),
    ("Infrastructure", "jellyfin", "Jellyfin", "🎬", "Media server", True, 8096, 2.4, True),
    ("System", "docker", "Docker Engine", "🐳", "Container runtime", False, None, None, False),
    ("System", "ssh", "SSH", "🔑", "Remote access", False, 22, None, False),
    ("System", "tailscale", "Tailscale", "🔐", "Private network (VPN)", False, None, None, False),
    ("System", "avahi", "Avahi (mDNS)", "📣", "Local name resolution", False, None, None, False),
    ("System", "cron", "Cron", "⏱️", "Scheduled tasks", False, None, None, False),
    ("System", "auto-updates", "Automatic updates", "🛡️", "unattended-upgrades", False, None, None, False),
    ("System", "backup", "Nightly backup", "🛟", "Config archive at 03:30", False, None, None, False),
]

_DEVICE_VENDORS = [
    ("Router", "TP-Link"), ("Laptop", "Apple"), ("Phone", "Apple"), ("Tablet", "Samsung"),
    ("TV", "LG Electronics"), ("Printer", "Brother"), ("Doorbell", "Ring"), ("Thermostat", "Netatmo"),
    ("Speaker", "Sonos"), ("Camera", "Reolink"), ("Plug", "Shelly"), ("E-reader", "Amazon"),
]


async def build(hostname: str) -> dict:
    now = time.time()
    groups: dict[str, list] = {}
    counters = {"up": 0, "warn": 0, "down": 0, "unknown": 0}

    for i, (group, sid, name, icon, desc, docker, port, cpu, restartable) in enumerate(_SERVICES):
        # Un seul service dégradé — camera-gw : conteneur vivant, sonde muette.
        state = "warn" if sid == "camera-gw" else "up"
        counters[state] += 1
        sources = []
        if docker:
            sources.append({"label": "docker", "value": "running", "ok": True})
        else:
            sources.append({"label": "systemd", "value": "active", "ok": True})
        if port:
            ok = state == "up"
            sources.append({"label": f"port {port}", "value": "answers" if ok else "silent", "ok": ok})
        item = {
            "id": sid,
            "name": name,
            "icon": icon,
            "description": desc,
            "state": state,
            "state_label": i18n.t(f"state.{state}", cfg.load_language()),
            "sources": sources,
            "extra": [],
            "uptime": f"{2 + i % 5} days" if docker else "",
            "image": f"demo/{sid}:latest" if docker else "",
            "ports": [],
            "cpu_percent": round(_wave(now, 300, max(cpu * 0.5, 0.1), cpu * 1.5, i), 1) if cpu is not None else None,
            "container": sid if docker else None,
            "restartable": restartable,
            "availability": {"uptime_pct": 99.8 if sid == "camera-gw" else 100.0,
                             "incidents": 1 if sid == "camera-gw" else 0,
                             "longest_minutes": 12 if sid == "camera-gw" else 0},
            "url": None,
        }
        groups.setdefault(group, []).append(item)

    cpu_now = round(_wave(now, 240, 3.0, 11.0), 1)
    mem_pct = round(_wave(now, 3600, 24.0, 31.0), 1)
    temp = round(_wave(now, 600, 51.0, 58.0), 1)
    nvme_temp = round(_wave(now, 900, 44.0, 49.0), 1)

    return {
        "groups": [{"name": g, "services": items} for g, items in groups.items()],
        "summary": {**counters, "total": len(_SERVICES)},
        "system": {
            "hostname": "demo",
            "uptime": {"seconds": 4 * 86400 + 6 * 3600, "human": "4 d 6 h"},
            "memory": {"total_mb": 8192, "used_mb": int(8192 * mem_pct / 100), "percent": mem_pct},
            "load": {"avg1": round(cpu_now / 25, 2), "avg5": 0.3, "avg15": 0.28, "cores": 4, "percent": cpu_now},
            "temperature_c": temp,
            "storage_temperature_c": nvme_temp,
            "fan_rpm": 2350,
            "undervoltage": False,
            "disks": [
                {"mount": "/", "total_gb": 58.0, "used_gb": 26.5, "percent": 45.7},
                {"mount": "/srv", "total_gb": 915.8, "used_gb": 208.4, "percent": 22.8},
            ],
            "timestamp": int(now),
        },
        "docker_available": True,
        "health": {
            "backups": [
                {"id": "config", "name": "Config", "path": "/var/backups", "state": "ok",
                 "age_days": 0.3, "detail": "7 h ago", "file": "config-2026-08-20.tar.gz", "size_mb": 42.7},
            ],
            "backups_measured_at": now - 60,
            "journal": {"counted": 2, "muted": 5, "by_source": [{"source": "systemd-udevd", "count": 2}]},
            "journal_measured_at": now - 60,
            "apt": {"available": True, "total": 3, "security": 2, "lists_age_days": 0.1,
                    "packages": ["libssl3", "openssh-client", "curl"]},
            "apt_measured_at": now - 300,
            "images": {"checked": 8, "outdated": 1,
                       "images": [{"image": "demo/jellyfin:latest", "state": "outdated"}]},
            "images_measured_at": now - 600,
            "throttling": {"available": True, "healthy": True, "now": [], "since_boot": [], "raw": "0x0", "bits": 0},
            "alerts": [{"level": "warn", "text": "2 security update(s) pending"}],
        },
        "network": {
            "tailscale_peers": [
                {"hostname": "laptop", "online": True, "os": "macOS", "tailscale_ip": "100.101.1.2"},
                {"hostname": "phone", "online": True, "os": "iOS", "tailscale_ip": "100.101.1.3"},
                {"hostname": "nas", "online": False, "os": "linux", "tailscale_ip": "100.101.1.4"},
            ],
            "tailscale_summary": {"version": "1.102.0", "peers_online": 2, "peers_total": 3},
            "lan_neighbors": [{"ip": f"192.168.1.{10 + i}", "mac": f"02:00:00:00:00:{i:02x}", "interface": "eth0"}
                              for i in range(len(_DEVICE_VENDORS))],
            "measured_at": now - 30,
            "new_devices": {"count": 1, "names": ["Reolink camera"]},
        },
        "nvme": {"percent_used": 1, "written_gb": 1843, "power_on_hours": 2160,
                 "temperature_c": nvme_temp, "available": True},
        "wan": {"online": True, "latency_ms": round(_wave(now, 120, 18.0, 32.0), 1),
                "outages_24h": 1, "last_outage_ts": now - 6 * 3600, "last_outage_minutes": 4},
        "public_ip": {"ip": "203.0.113.42", "changed_ts": now - 12 * 86400},
        "update": {"current": "0.1.0", "latest": None, "available": False},
    }


def history(hours: float = 24.0) -> list[dict]:
    """Échantillons toutes les 5 min, déterministes (base de temps fictive fixe)."""
    step = 300
    count = int(hours * 3600 / step)
    samples = []
    for i in range(count):
        ts = _START + i * step
        samples.append({
            "ts": ts,
            "cpu_pct": round(_wave(ts, 7200, 3.0, 10.0) + _wave(ts, 947, 0.0, 14.0 if ts % 40000 < 2500 else 2.0), 1),
            "mem_pct": round(_wave(ts, 43200, 24.0, 31.0), 1),
            "temp_c": round(_wave(ts, 7200, 51.0, 58.5), 1),
            "nvme_temp_c": round(_wave(ts, 10800, 44.0, 49.5), 1),
        })
    return samples


def devices() -> dict:
    result = []
    for i, (kind, vendor) in enumerate(_DEVICE_VENDORS):
        mac = f"02:00:00:00:00:{i:02x}"
        new = kind == "Camera"
        result.append({
            "mac": mac,
            "name": None if new else kind,
            "note": None,
            "category": None,
            "first_seen": _START,
            "last_seen": int(time.time()),
            "last_ip": f"192.168.1.{10 + i}",
            "mdns_name": None,
            "acknowledged": 0 if new else 1,
            "online": i % 5 != 4,
            "vendor": vendor,
            "local_mac": True,
            "display_name": f"{vendor} {kind.lower()}" if new else kind,
            "name_source": "fabricant" if new else "manuel",
        })
    online = sum(1 for d in result if d["online"])
    return {
        "devices": result,
        "tailscale_peers": [],
        "summary": {"total": len(result), "online": online, "new": 1},
        "inventory_available": True,
    }


def outages(hours: float = 24.0) -> dict:
    now = time.time()
    return {"outages": [{"start_ts": now - 6 * 3600, "end_ts": now - 6 * 3600 + 240, "minutes": 4}]}
