"""Âge de la dernière sauvegarde des répertoires surveillés.

Raison d'être : Home Assistant tourne ici en Core/Container, **sans Supervisor**. Rien ne
sauvegarde automatiquement, et rien n'affiche cette absence. Une tuile qui annonce « jamais »
est l'alerte la plus utile du tableau de bord.
"""

from __future__ import annotations

import time
from pathlib import Path

NEVER, OK, WARN = "never", "ok", "warn"


def _newest(directory: Path, pattern: str) -> Path | None:
    try:
        candidates = [p for p in directory.glob(pattern) if p.is_file()]
    except OSError:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def collect(entries: list[dict]) -> list[dict]:
    """entries : [{id, name, path, pattern, warn_after_days}]"""
    now = time.time()
    result = []

    for entry in entries:
        directory = Path(entry["path"])
        pattern = entry.get("pattern", "*")
        warn_after = float(entry.get("warn_after_days", 7))

        newest = _newest(directory, pattern) if directory.is_dir() else None

        if newest is None:
            result.append(
                {
                    "id": entry["id"],
                    "name": entry["name"],
                    "path": str(directory),
                    "state": NEVER,
                    "age_days": None,
                    "detail": "aucune sauvegarde" if directory.is_dir() else "répertoire absent",
                    "file": None,
                    "size_mb": None,
                }
            )
            continue

        stat = newest.stat()
        age_days = (now - stat.st_mtime) / 86400
        result.append(
            {
                "id": entry["id"],
                "name": entry["name"],
                "path": str(directory),
                "state": WARN if age_days > warn_after else OK,
                "age_days": round(age_days, 1),
                "detail": _humanize(age_days),
                "file": newest.name,
                "size_mb": round(stat.st_size / 1024**2, 1),
            }
        )
    return result


def _humanize(age_days: float) -> str:
    from .. import config as cfg
    from .. import i18n
    lang = cfg.load_language()
    if age_days < 1 / 24:
        return i18n.t("age.just_now", lang)
    if age_days < 1:
        return i18n.t("age.hours", lang, count=int(age_days * 24))
    if age_days < 2:
        return "hier"
    return i18n.t("age.days", lang, count=int(age_days))
