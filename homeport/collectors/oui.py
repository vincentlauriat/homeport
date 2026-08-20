"""Fabricant d'un appareil déduit du préfixe OUI de son adresse MAC.

Base IEEE embarquée dans le dépôt (`app/data/oui.tsv`, générée par `scripts/build-oui.py`) :
aucun appel réseau, jamais. Chargée paresseusement en un dict, une seule fois par process.
"""

from __future__ import annotations

import re
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "oui.tsv"

_HEX_PAIRS = re.compile(r"^[0-9a-f]{12}$")
_table_cache: dict[str, str] | None = None


def _load_table(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    table = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        prefix, _, org = line.partition("\t")
        if org:
            table[prefix] = org
    return table


def _normalize(mac: str) -> str | None:
    """`AA-BB-CC-DD-EE-FF` / `aa:bb:...` -> `aabbccddeeff`, ou None si malformée."""
    cleaned = mac.lower().replace(":", "").replace("-", "")
    return cleaned if _HEX_PAIRS.match(cleaned) else None


def vendor(mac: str, table: dict[str, str] | None = None) -> str | None:
    """Fabricant du préfixe OUI, ou None (préfixe inconnu, MAC malformée)."""
    global _table_cache
    if table is None:
        if _table_cache is None:
            _table_cache = _load_table(DATA_PATH)
        table = _table_cache
    normalized = _normalize(mac)
    return table.get(normalized[:6]) if normalized else None


def is_local_mac(mac: str) -> bool:
    """MAC « administrée localement » (bit 0x02 du premier octet) : typiquement une adresse
    privée randomisée (iOS, Android) — le fabricant n'a alors aucun sens."""
    normalized = _normalize(mac)
    return bool(normalized) and bool(int(normalized[0:2], 16) & 0x02)
