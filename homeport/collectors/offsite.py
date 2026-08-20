"""Sauvegarde hors machine — état lu depuis le JSON écrit par `homeport-restic.sh` (root).

Même séparation de privilèges que l'usure NVMe : restic et la clé SSH vivent côté root, le
service web se contente de lire un fichier d'état. Voir scripts/homeport-restic.sh.
"""

from __future__ import annotations

import json
import time
from pathlib import Path


def collect(path: Path, now: float | None = None) -> dict | None:
    """État de la sauvegarde hors-site, ou None si le fichier est absent/illisible."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    last_ts = raw.get("last_snapshot_ts")
    reference = now if now is not None else time.time()
    age_hours = round((reference - last_ts) / 3600, 1) if last_ts else None

    return {
        "status": raw.get("status", "unknown"),  # ok | pending | error
        "message": raw.get("message", ""),
        "last_snapshot_ts": last_ts,
        "age_hours": age_hours,
        "snapshots": raw.get("snapshots"),
        "verified_ts": raw.get("verified_ts"),
        "verified_ok": raw.get("verified_ok"),
    }
