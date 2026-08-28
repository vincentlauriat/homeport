"""Métriques de la machine, lues directement dans /proc et /sys sur Linux.

Aucune dépendance (pas de psutil) : chaque dépendance en moins est une ligne en moins à figer
dans requirements.txt, et ces fichiers-là ne changent pas de format. macOS n'a pas de `/proc` :
`uptime()`/`memory()` y basculent sur `sysctl`/`vm_stat`, aussi rapides qu'une lecture de
fichier — pas la classe de commandes lentes que `background.py` sort du chemin de la requête.
`load()` n'a pas besoin de cette bascule : `os.getloadavg()` est POSIX, disponible et
équivalent à `/proc/loadavg` sur les deux OS.
"""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path


def _read(path: str) -> str | None:
    """`None` distingue une source absente d'une source présente mais vide — un appelant
    qui confondrait les deux rendrait un zéro là où la bonne réponse est « je ne sais pas »
    (ex. `/proc/*` n'existe pas sur macOS)."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return None


def hostname() -> str:
    return socket.gethostname()


def _unit(key: str) -> str:
    from .. import config as cfg
    from .. import i18n
    return i18n.t(key, cfg.load_language())


def _format_uptime(seconds: int) -> dict:
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    parts = []
    if days:
        parts.append(f"{days} {_unit('unit.days')}")
    if hours or days:
        parts.append(f"{hours} {_unit('unit.hours')}")
    parts.append(f"{minutes} {_unit('unit.minutes')}")
    return {"seconds": seconds, "human": " ".join(parts)}


def _run(*args: str) -> str | None:
    """`None` si le binaire est absent, échoue ou dépasse le délai — jamais d'exception."""
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


_BOOTTIME_RE = re.compile(r"sec\s*=\s*(\d+)")


def _boottime_seconds(text: str) -> int | None:
    match = _BOOTTIME_RE.search(text)
    return int(match.group(1)) if match else None


def _uptime_macos() -> dict:
    text = _run("sysctl", "-n", "kern.boottime")
    boot = _boottime_seconds(text) if text is not None else None
    if boot is None:
        return {"seconds": None, "human": None}
    return _format_uptime(max(int(time.time()) - boot, 0))


def _uptime_from_proc(path: str = "/proc/uptime") -> dict:
    text = _read(path)
    if text is None:
        return {"seconds": None, "human": None}
    raw = text.split()
    seconds = int(float(raw[0])) if raw else 0
    return _format_uptime(seconds)


def uptime() -> dict:
    if sys.platform == "darwin":
        return _uptime_macos()
    return _uptime_from_proc()


_VM_STAT_FIELD_RE = re.compile(r"^([A-Za-z][\w \"]*?):\s+(\d+)\.", re.MULTILINE)
_VM_STAT_PAGE_SIZE_RE = re.compile(r"page size of (\d+) bytes")


def _parse_vm_stat(text: str) -> tuple[int, dict[str, int]]:
    """`vm_stat` : un en-tête donnant la taille de page (4096 en repli si absent, valeur
    historique avant les pages 16 Ko d'Apple Silicon), puis un compte de pages par ligne."""
    size_match = _VM_STAT_PAGE_SIZE_RE.search(text)
    page_size = int(size_match.group(1)) if size_match else 4096
    pages = {name: int(count) for name, count in _VM_STAT_FIELD_RE.findall(text)}
    return page_size, pages


def _memory_macos() -> dict:
    """Mémoire « disponible » au sens où `free`/`inactive` (pages libérables sans E/S) comptent
    comme libres — la même convention que psutil sur macOS, faute de `MemAvailable` natif."""
    hw = _run("sysctl", "-n", "hw.memsize")
    vm = _run("vm_stat")
    if hw is None or vm is None:
        return {"total_mb": None, "used_mb": None, "percent": None}
    try:
        total_bytes = int(hw.strip())
    except ValueError:
        return {"total_mb": None, "used_mb": None, "percent": None}
    page_size, pages = _parse_vm_stat(vm)
    available_bytes = (pages.get("Pages free", 0) + pages.get("Pages inactive", 0)) * page_size
    total_mb = total_bytes // (1024 * 1024)
    used_mb = (total_bytes - available_bytes) // (1024 * 1024)
    return {
        "total_mb": total_mb,
        "used_mb": used_mb,
        "percent": round(used_mb / total_mb * 100, 1) if total_mb else None,
    }


def _memory_from_proc(path: str = "/proc/meminfo") -> dict:
    """Mémoire en Mio. `MemAvailable` est la bonne mesure du libre réel, pas `MemFree`."""
    text = _read(path)
    if text is None:
        return {"total_mb": None, "used_mb": None, "percent": None}
    values: dict[str, int] = {}
    for line in text.splitlines():
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


def memory() -> dict:
    if sys.platform == "darwin":
        return _memory_macos()
    return _memory_from_proc()


def load() -> dict:
    """`os.getloadavg()` est équivalent à `/proc/loadavg` sur Linux (même appel système) et
    fonctionne aussi sur macOS : une seule implémentation pour les deux OS."""
    cores = os.cpu_count() or 1
    try:
        avg1, avg5, avg15 = os.getloadavg()
    except OSError:
        return {"avg1": None, "avg5": None, "avg15": None, "cores": cores, "percent": None}
    return {
        "avg1": avg1,
        "avg5": avg5,
        "avg15": avg15,
        "cores": cores,
        "percent": round(min(avg1 / cores * 100, 100), 1),
    }


def temperature(path: str = "/sys/class/thermal/thermal_zone0/temp") -> float | None:
    """Température CPU en °C (le fichier contient des milli-degrés)."""
    raw = _read(path)
    if raw is None:
        return None
    try:
        return round(int(raw.strip()) / 1000, 1)
    except ValueError:
        return None


def _hwmon(root: str = "/sys/class/hwmon") -> dict[str, Path]:
    """Capteurs matériels indexés par nom : `cpu_thermal`, `nvme`, `pwmfan`, `rpi_volt`."""
    sensors: dict[str, Path] = {}
    try:
        for entry in Path(root).iterdir():
            name = _read(str(entry / "name"))
            if name and name.strip():
                sensors[name.strip()] = entry
    except OSError:
        pass
    return sensors


def _int_from(path: Path) -> int | None:
    raw = _read(str(path))
    if raw is None:
        return None
    try:
        return int(raw.strip())
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
