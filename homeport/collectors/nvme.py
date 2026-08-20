"""Usure du SSD NVMe, à partir du journal SMART de `nvme-cli`.

`nvme smart-log` exige les privilèges d'administration du périphérique : impossible depuis le
service web, qui tourne sans privilège (et à qui on ne veut surtout pas en donner). Un timer
systemd **root** (`deploy/homeport-nvme.timer`) exécute la commande périodiquement et écrit sa
sortie JSON dans `/mnt/ssd/homeport-data/nvme.json` ; ce module ne fait que **lire** ce fichier —
même schéma que l'historique SQLite, aucun privilège requis côté Homeport.

L'usure bouge très lentement : un relevé quotidien suffit largement.
"""

from __future__ import annotations

import json
from pathlib import Path

# 1 « data unit » NVMe = 1000 × 512 octets (spec NVMe), pas 1024.
_BYTES_PER_UNIT = 512_000


def parse_smart_log(raw_json: str) -> dict:
    data = json.loads(raw_json)
    kelvin = data.get("temperature")
    units = data.get("data_units_written", 0)
    return {
        "percent_used": data.get("percent_used"),
        "power_on_hours": data.get("power_on_hours"),
        "written_gb": round(units * _BYTES_PER_UNIT / 1e9, 1) if units else None,
        "temperature_c": round(kelvin - 273) if kelvin is not None else None,
        "spare_percent": data.get("avail_spare"),
        # `critical_warning` est un masque de bits : tout bit posé signale un problème.
        "healthy": data.get("critical_warning", 0) == 0,
    }


def collect(path: Path) -> dict | None:
    """Lit et parse le fichier écrit par le timer root. `None` si absent ou illisible —
    « pas encore relevé », pas « rien à signaler »."""
    try:
        return parse_smart_log(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
