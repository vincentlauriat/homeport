"""État électrique et thermique du Raspberry Pi.

`vcgencmd get_throttled` renvoie un masque de bits qui distingue deux choses très
différentes : ce qui se passe **maintenant** (bits 0-3) et ce qui s'est produit **depuis le
démarrage** (bits 16-19). Le second groupe est le plus précieux : une sous-tension qui a duré
trente secondes cette nuit n'apparaît nulle part ailleurs, et c'est la première cause de
corruption de carte SD sur Pi — bien avant l'usure.

Cette mesure passe par un sous-processus, elle est donc reléguée aux boucles de fond. Le
temps réel (alarme de sous-tension, températures, ventilateur) est lu directement dans
`/sys`, sans processus, par `collectors/system.py`.
"""

from __future__ import annotations

from . import _process

# bit -> (survenu depuis le démarrage ?, libellé)
FLAGS: dict[int, tuple[bool, str]] = {
    0: (False, "sous-tension détectée"),
    1: (False, "fréquence CPU bridée"),
    2: (False, "throttling actif"),
    3: (False, "limite de température atteinte"),
    16: (True, "sous-tension survenue"),
    17: (True, "bridage de fréquence survenu"),
    18: (True, "throttling survenu"),
    19: (True, "limite de température franchie"),
}


async def throttling() -> dict:
    stdout = await _process.run("vcgencmd", "get_throttled")
    if stdout is None:
        return {"available": False, "healthy": None, "now": [], "since_boot": [], "raw": None, "bits": None}
    raw = stdout.decode().strip()

    if "=" not in raw:
        return {"available": False, "healthy": None, "now": [], "since_boot": [], "raw": raw, "bits": None}

    try:
        bits = int(raw.split("=", 1)[1], 16)
    except ValueError:
        return {"available": False, "healthy": None, "now": [], "since_boot": [], "raw": raw, "bits": None}

    now, since_boot = [], []
    for bit, (historical, label) in FLAGS.items():
        if bits & (1 << bit):
            (since_boot if historical else now).append(label)

    return {
        "available": True,
        "healthy": bits == 0,
        "now": now,
        "since_boot": since_boot,
        "raw": raw.split("=", 1)[1],
        # Masque brut : les libellés ci-dessus sont faits pour être lus par un humain, pas
        # testés par du code. Un consommateur qui veut distinguer « sous-tension » de
        # « bridage thermique » interroge le bit, jamais le texte français.
        "bits": bits,
    }
