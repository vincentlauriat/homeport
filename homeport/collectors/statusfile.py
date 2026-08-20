"""Fichiers d'état génériques — le pont entre les jobs privilégiés et le dashboard.

Un script (sauvegarde hors-site, réplication, certificat…) écrit un petit JSON là où
Homeport, non privilégié, peut le lire. Homeport l'affiche en carte santé, l'intègre aux
alertes et le publie en capteur MQTT. Déclaration dans la config :

    health:
      status_files:
        - id: offsite            # unique — nom du capteur MQTT ({id}_age)
          name: Offsite backup   # libellé affiché
          path: /var/lib/homeport/offsite.json
          warn_after_hours: 48   # optionnel — au-delà, l'état passe en alerte

Contrat du fichier (tous les champs optionnels sauf `status`) :

    {"status": "ok" | "pending" | "error",
     "message": "one line for humans",
     "last_ts": 1787217794}        # ou `last_snapshot_ts` — l'horodatage du dernier succès
"""

from __future__ import annotations

import json
import time
from pathlib import Path

# Ordre de priorité des horodatages acceptés — `last_snapshot_ts` pour la compatibilité avec
# les scripts de sauvegarde existants, `last_ts` comme nom générique documenté.
_TS_KEYS = ("last_ts", "last_snapshot_ts")


def collect(entry: dict, now: float | None = None) -> dict:
    now = now if now is not None else time.time()
    warn_after = entry.get("warn_after_hours")

    try:
        data = json.loads(Path(entry["path"]).read_text(encoding="utf-8"))
        status = str(data.get("status") or "invalid")
        message = data.get("message") or ""
    except FileNotFoundError:
        data, status, message = {}, "missing", ""
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        data, status, message = {}, "invalid", ""

    age_hours = None
    for key in _TS_KEYS:
        if isinstance(data.get(key), (int, float)):
            age_hours = round(max(now - data[key], 0) / 3600, 1)
            break

    stale = bool(warn_after and age_hours is not None and age_hours > warn_after)

    if status == "error":
        level = "down"
    elif status == "ok" and not stale:
        level = "up"
    else:
        # pending, missing, invalid, ou ok-mais-en-retard : à surveiller, pas une panne.
        level = "warn"

    return {
        "id": entry["id"],
        "name": entry.get("name", entry["id"]),
        "status": status,
        "message": message,
        "age_hours": age_hours,
        "stale": stale,
        "level": level,
    }
