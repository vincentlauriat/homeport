"""Détection des transitions — le scribe du livre de bord.

Les boucles de fond mesurent ; ce module compare chaque mesure à la précédente et ne
consigne que les changements. L'état de référence vit en RAM : au démarrage de
l'application, le premier passage de chaque source « amorce » silencieusement, donc un
simple restart du service Homeport ne produit aucun événement fantôme. Seul le boot de la
machine est consigné, détecté par un uptime système plus jeune que le seuil.

Chaque fonction retourne le nombre d'événements écrits — la matière des tests.
"""

from __future__ import annotations

import time
from pathlib import Path

from homeport.collectors import events

_BOOT_MAX_UPTIME_S = 300
_TEMP_HIGH_C = 80.0
# Ré-armement sous 75 °C : sans hystérésis, une température qui oscille autour du seuil
# écrirait un événement par passage de boucle.
_TEMP_REARM_C = 75.0

_state: dict[str, object] = {}

_SERVICE_KINDS = {
    "up": ("service.up", "up"),
    "warn": ("service.degraded", "warn"),
    "down": ("service.down", "down"),
}


def reset() -> None:
    """Oublie l'état de référence (tests, rechargement)."""
    _state.clear()


def services(path: Path, states: dict[str, str], now: float | None = None) -> int:
    prev = _state.get("services")
    _state["services"] = dict(states)
    if prev is None:
        return 0
    written = 0
    for service_id, state in states.items():
        old = prev.get(service_id)
        # Service absent du passage précédent (ajout dans la config) ou état inconnu
        # d'un côté ou de l'autre : pas une transition vécue, pas d'événement.
        if old is None or state == old or state not in _SERVICE_KINDS or old not in _SERVICE_KINDS:
            continue
        kind, severity = _SERVICE_KINDS[state]
        events.record(path, kind, severity, service_id, now=now)
        written += 1
    return written


def wan(path: Path, online: bool, now: float | None = None) -> int:
    ts = now if now is not None else time.time()
    prev = _state.get("wan_online")
    _state["wan_online"] = online
    if prev is None:
        if not online:
            _state["wan_down_ts"] = ts  # amorcé en panne : mémorise le début pour la durée
        return 0
    if online == prev:
        return 0
    if not online:
        _state["wan_down_ts"] = ts
        events.record(path, "internet.down", "down", "internet", now=now)
    else:
        down_ts = _state.pop("wan_down_ts", None)
        detail = f"{max(1, round((ts - down_ts) / 60))} min" if down_ts is not None else None
        events.record(path, "internet.up", "up", "internet", detail=detail, now=now)
    return 1


def public_ip(path: Path, ip: str | None, now: float | None = None) -> int:
    prev = _state.get("public_ip")
    if ip:
        _state["public_ip"] = ip
    if prev is None or not ip or ip == prev:
        return 0
    events.record(path, "ip.changed", "warn", ip, detail=f"{prev} → {ip}", now=now)
    return 1


def backups(path: Path, entries: list[dict], now: float | None = None) -> int:
    prev = _state.get("backups")
    current = {e["name"]: e["state"] for e in entries}
    _state["backups"] = current
    if prev is None:
        return 0
    written = 0
    for name, state in current.items():
        old = prev.get(name)
        if old is None or state == old:
            continue
        if state == "never":
            events.record(path, "backup.failed", "down", name, now=now)
        elif state == "warn":
            events.record(path, "backup.stale", "warn", name, now=now)
        elif state == "ok":
            events.record(path, "backup.ok", "up", name, now=now)
        else:
            continue
        written += 1
    return written


def throttling(path: Path, data: dict, now: float | None = None) -> int:
    current = set(data.get("now") or [])
    prev = _state.get("throttling")
    _state["throttling"] = current
    if prev is None:
        return 0
    written = 0
    for label in sorted(current - prev):
        if "volt" in label.lower():
            events.record(path, "power.undervoltage", "down", label, now=now)
        else:
            events.record(path, "temp.high", "warn", label, now=now)
        written += 1
    return written


def temperature(path: Path, temp_c: float | None, now: float | None = None) -> int:
    if temp_c is None:
        return 0
    armed = _state.get("temp_armed", True)
    if armed and temp_c >= _TEMP_HIGH_C:
        _state["temp_armed"] = False
        events.record(path, "temp.high", "warn", "cpu", detail=f"{round(temp_c)} °C", now=now)
        return 1
    if not armed and temp_c <= _TEMP_REARM_C:
        _state["temp_armed"] = True
    return 0


def boot(path: Path, uptime_seconds: float, now: float | None = None) -> int:
    """Appelé une fois au démarrage de l'app : un uptime machine plus jeune que le seuil
    signifie que ce démarrage suit un boot, pas un simple restart du service."""
    if uptime_seconds >= _BOOT_MAX_UPTIME_S:
        return 0
    events.record(path, "boot", "warn", "system", now=now)
    return 1


def devices_new(path: Path, new_devices: list[dict], now: float | None = None) -> int:
    written = 0
    for device in new_devices:
        events.record(
            path, "device.new", "warn", device.get("mac", "?"), detail=device.get("ip"), now=now
        )
        written += 1
    return written
