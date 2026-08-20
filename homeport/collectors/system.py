"""Métriques de la machine, lues directement dans /proc et /sys.

Aucune dépendance (pas de psutil) : chaque dépendance en moins est une ligne en moins à figer
dans requirements.txt, et ces fichiers-là ne changent pas de format.
"""

from __future__ import annotations

import os
import re
import shutil
import socket
import time
from pathlib import Path


def _read(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def hostname() -> str:
    return socket.gethostname()


def _unit(key: str) -> str:
    from .. import i18n
    from .. import config as cfg
    return i18n.t(key, cfg.load_language())


def uptime() -> dict:
    raw = _read("/proc/uptime").split()
    seconds = float(raw[0]) if raw else 0.0
    days, rest = divmod(int(seconds), 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    parts = []
    if days:
        parts.append(f"{days} {_unit('unit.days')}")
    if hours or days:
        parts.append(f"{hours} {_unit('unit.hours')}")
    parts.append(f"{minutes} {_unit('unit.minutes')}")
    return {"seconds": int(seconds), "human": " ".join(parts)}


def memory() -> dict:
    """Mémoire en Mio. `MemAvailable` est la bonne mesure du libre réel, pas `MemFree`."""
    values: dict[str, int] = {}
    for line in _read("/proc/meminfo").splitlines():
        match = re.match(r"^(\w+):\s+(\d+) kB", line)
        if match:
            values[match.group(1)] = int(match.group(2))
    total = values.get("MemTotal", 0) // 1024
    available = values.get("MemAvailable", 0) // 1024
    used = total - available
    return {
        "total_mb": total,
        "used_mb": used,
        "percent": round(used / total * 100, 1) if total else 0.0,
    }


def load() -> dict:
    raw = _read("/proc/loadavg").split()
    cores = os.cpu_count() or 1
    one = float(raw[0]) if raw else 0.0
    return {
        "avg1": one,
        "avg5": float(raw[1]) if len(raw) > 1 else 0.0,
        "avg15": float(raw[2]) if len(raw) > 2 else 0.0,
        "cores": cores,
        "percent": round(min(one / cores * 100, 100), 1),
    }


def temperature() -> float | None:
    """Température CPU en °C (le fichier contient des milli-degrés)."""
    raw = _read("/sys/class/thermal/thermal_zone0/temp").strip()
    try:
        return round(int(raw) / 1000, 1)
    except ValueError:
        return None


def _hwmon() -> dict[str, Path]:
    """Capteurs matériels indexés par nom : `cpu_thermal`, `nvme`, `pwmfan`, `rpi_volt`."""
    sensors: dict[str, Path] = {}
    try:
        for entry in Path("/sys/class/hwmon").iterdir():
            name = _read(str(entry / "name")).strip()
            if name:
                sensors[name] = entry
    except OSError:
        pass
    return sensors


def _int_from(path: Path) -> int | None:
    raw = _read(str(path)).strip()
    try:
        return int(raw)
    except ValueError:
        return None


def storage_temperature() -> float | None:
    """Température du SSD NVMe, sans `smartctl` ni `nvme-cli` : le pilote l'expose en hwmon."""
    sensor = _hwmon().get("nvme")
    if sensor is None:
        return None
    value = _int_from(sensor / "temp1_input")
    return round(value / 1000, 1) if value is not None else None


def fan_rpm() -> int | None:
    sensor = _hwmon().get("pwmfan")
    return _int_from(sensor / "fan1_input") if sensor else None


def undervoltage() -> bool | None:
    """Alarme de sous-tension **instantanée**, lue sans sous-processus.

    `None` si le capteur n'existe pas ; `True` signifie que l'alimentation ne tient pas la
    charge en ce moment — cause première de corruption de carte SD sur Raspberry Pi.
    """
    sensor = _hwmon().get("rpi_volt")
    if sensor is None:
        return None
    value = _int_from(sensor / "in0_lcrit_alarm")
    return bool(value) if value is not None else None


def disks(mountpoints: list[str]) -> list[dict]:
    result = []
    for mountpoint in mountpoints:
        if not os.path.ismount(mountpoint) and mountpoint != "/":
            continue
        try:
            usage = shutil.disk_usage(mountpoint)
        except OSError:
            continue
        result.append(
            {
                "mount": mountpoint,
                "total_gb": round(usage.total / 1024**3, 1),
                "used_gb": round(usage.used / 1024**3, 1),
                "percent": round(usage.used / usage.total * 100, 1) if usage.total else 0.0,
            }
        )
    return result


def collect(mountpoints: list[str] | None = None) -> dict:
    return {
        "hostname": hostname(),
        "uptime": uptime(),
        "memory": memory(),
        "load": load(),
        "temperature_c": temperature(),
        "storage_temperature_c": storage_temperature(),
        "fan_rpm": fan_rpm(),
        "undervoltage": undervoltage(),
        "disks": disks(mountpoints or ["/", "/mnt/ssd"]),
        "timestamp": int(time.time()),
    }
