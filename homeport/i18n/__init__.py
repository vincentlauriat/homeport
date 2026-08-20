"""i18n minimaliste : un JSON plat par langue, `{var}` pour les variables, paires
`_one`/`_many` pour le pluriel. Une clé absente rend la clé elle-même — un libellé brut à
l'écran vaut mieux qu'une 500, et se voit immédiatement en développement."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

_DIR = Path(__file__).resolve().parent
DEFAULT_LANG = "en"


@cache
def catalog(lang: str) -> dict:
    path = _DIR / f"{lang}.json"
    if not path.exists():
        path = _DIR / f"{DEFAULT_LANG}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def t(key: str, lang: str = DEFAULT_LANG, **variables) -> str:
    template = catalog(lang).get(key, key)
    try:
        return template.format(**variables)
    except (KeyError, IndexError):
        return template


def tn(key: str, count: int, lang: str = DEFAULT_LANG, **variables) -> str:
    """Pluriel : `key_one` si count == 1, sinon `key_many` (repli : la clé nue)."""
    suffix = "_one" if count == 1 else "_many"
    plural_key = f"{key}{suffix}"
    if plural_key in catalog(lang):
        return t(plural_key, lang, count=count, **variables)
    return t(key, lang, count=count, **variables)
