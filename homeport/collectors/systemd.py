"""État des unités systemd de l'hôte.

Deux pièges évités ici :

1. `systemctl is-active` **sort avec le code 3** quand l'unité est inactive — exactement le cas
   qu'on cherche à afficher. Un `check=True` lèverait une exception sur le cas nominal.
2. Un `systemctl` par unité et par rafraîchissement, c'est N processus toutes les quelques
   secondes. On utilise donc **un seul appel** `systemctl show` pour toutes les unités : il sort
   avec le code 0 et renvoie un bloc `clé=valeur` par unité, séparés par une ligne vide.
"""

from __future__ import annotations

import asyncio
import re

PROPERTIES = (
    "Id", "ActiveState", "SubState", "Description", "ActiveEnterTimestamp",
    # Vides pour toute unité qui n'est pas un minuteur — sans coût pour les autres, une seule
    # commande couvre toujours tout le monde (voir le commentaire de tête du module).
    "NextElapseUSecRealtime", "LastTriggerUSec",
)

_TIMESTAMP = re.compile(r"^\w{3}\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}):\d{2}\s+\S+$")


def _clean_timestamp(raw: str) -> str:
    """`systemctl show` rend `Thu 2026-08-20 03:32:38 CEST` ; on ne garde que ce qui se lit
    d'un coup d'œil. `n/a` (minuteur jamais déclenché) et l'absence de valeur rendent ''."""
    match = _TIMESTAMP.match(raw)
    return match.group(1) if match else ""


async def collect(units: list[str]) -> dict[str, dict]:
    """Retourne {nom_unite: {active_state, sub_state, description, since}}."""
    if not units:
        return {}

    args = ["systemctl", "show", "--no-pager"]
    for prop in PROPERTIES:
        args += ["-p", prop]
    args += list(units)

    try:
        process = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5.0)
    except Exception:
        return {}

    result: dict[str, dict] = {}
    for block in stdout.decode("utf-8", "replace").split("\n\n"):
        fields: dict[str, str] = {}
        for line in block.splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                fields[key] = value
        unit_id = fields.get("Id")
        if not unit_id:
            continue
        result[unit_id] = {
            "active_state": fields.get("ActiveState", "unknown"),  # active | inactive | failed
            "sub_state": fields.get("SubState", ""),
            "description": fields.get("Description", ""),
            "since": _clean_timestamp(fields.get("ActiveEnterTimestamp", "")),
            "next_run": _clean_timestamp(fields.get("NextElapseUSecRealtime", "")),
            "last_run": _clean_timestamp(fields.get("LastTriggerUSec", "")),
        }
    return result
