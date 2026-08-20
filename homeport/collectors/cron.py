"""Tâches planifiées lues dans les crontabs système — `/etc/crontab` et `/etc/cron.d/*`.

Le crontab de `alice` (`crontab -l`) est délibérément ignoré : ce compte n'en a pas, et le
lire demanderait un sous-processus pour un cas qui n'arrive jamais sur cet hôte. Les fichiers
système sont lus directement (`-rw-r--r-- root root`, aucun privilège requis).
"""

from __future__ import annotations

import re
from pathlib import Path

CRONTAB_PATHS = [Path("/etc/crontab")]
CRON_D_DIR = Path("/etc/cron.d")

# 5 champs horaires + utilisateur + commande. Les crontabs système (contrairement à ceux d'un
# utilisateur) portent toujours un champ utilisateur — c'est ce qui les distingue des lignes de
# commentaire ou d'affectation de variable (`SHELL=`, `PATH=`), qui n'ont pas cette forme.
_JOB_LINE = re.compile(
    r"^(?P<schedule>\S+\s+\S+\s+\S+\s+\S+\s+\S+)\s+(?P<user>\S+)\s+(?P<command>.+)$"
)


def parse_crontab(text: str) -> list[dict]:
    """Une entrée par ligne de tâche. Commentaires, lignes vides et affectations de variable
    ignorés — silencieusement, comme le ferait `cron` lui-même."""
    jobs = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" in line.split()[0]:
            continue
        match = _JOB_LINE.match(line)
        if not match:
            continue
        jobs.append(
            {
                "schedule": " ".join(match.group("schedule").split()),
                "user": match.group("user"),
                "command": match.group("command"),
            }
        )
    return jobs


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def collect() -> list[dict]:
    """Toutes les tâches système, `/etc/crontab` puis `/etc/cron.d/*` par ordre alphabétique."""
    jobs: list[dict] = []
    for path in CRONTAB_PATHS:
        jobs += parse_crontab(_read(path))
    try:
        files = sorted(CRON_D_DIR.iterdir())
    except OSError:
        files = []
    for path in files:
        if path.is_file():
            jobs += parse_crontab(_read(path))
    return jobs
