"""Pression thermique macOS, via `powermetrics --samplers thermal`.

Sur les Mac récents (vérifié en root sur un Mac17,3, macOS 26), `powermetrics` ne rend plus
de température CPU en °C ni de vitesse de ventilateur — seulement un niveau qualitatif :
`Nominal`, `Moderate`, `Heavy`, `Trapping`, `Sleeping` (échelle documentée par Apple,
`NSProcessInfoThermalState`). `temperature_c`/`fan_rpm` (`collectors/system.py`) restent
`None` sur macOS : ce n'est pas une mesure manquante à combler, c'est une mesure d'une
autre nature, qui vit dans son propre champ plutôt que d'être forcée dans un °C inventé.

`powermetrics` exige root : impossible depuis le service web, qui tourne sans privilège. Un
LaunchDaemon root (`deploy/macos/`) l'exécute périodiquement et écrit sa sortie brute dans un
fichier que ce module se contente de LIRE — même schéma que le timer NVMe
(`collectors/nvme.py`) : aucun privilège requis côté Homeport.
"""

from __future__ import annotations

import re
from pathlib import Path

_LEVEL_RE = re.compile(r"Current pressure level:\s*(\w+)", re.IGNORECASE)

#: Échelle documentée par Apple (`NSProcessInfoThermalState`). Un niveau hors de cette liste
#: (nouvelle version de `powermetrics`, format modifié) rend `None` plutôt qu'une valeur
#: inconnue affichée comme si elle avait un sens.
LEVELS = ("nominal", "moderate", "heavy", "trapping", "sleeping")


def parse_thermal_pressure(raw_text: str) -> str | None:
    match = _LEVEL_RE.search(raw_text)
    if not match:
        return None
    level = match.group(1).lower()
    return level if level in LEVELS else None


def collect(path: Path) -> str | None:
    """Lit et parse le fichier écrit par le LaunchDaemon root. `None` si absent, illisible,
    ou introuvable dans la sortie — « pas encore relevé », pas « tout va bien »."""
    try:
        return parse_thermal_pressure(Path(path).read_text(encoding="utf-8"))
    except OSError:
        return None
