"""Sessions SSH actives, lues via `who`.

Sur cet hôte, `who` affiche le nom du service PAM à la place d'un tty pour les sessions sans
terminal (Tailscale SSH, console locale) : le filtrage se fait donc sur le mot « sshd » présent
dans la ligne, pas sur la position d'une colonne — une colonne « tty » suppose un format que cet
hôte ne respecte pas toujours.
"""

from __future__ import annotations

import re

from . import _process

_HOST = re.compile(r"\(([^)]+)\)\s*$")


def parse_who(raw_output: str) -> list[dict]:
    sessions = []
    for line in raw_output.splitlines():
        tokens = line.split()
        if "sshd" not in tokens:
            continue
        match = _HOST.search(line)
        if not match:
            continue
        sessions.append({"user": tokens[0], "host": match.group(1)})
    return sessions


async def collect() -> list[dict]:
    stdout = await _process.run("who")
    if stdout is None:
        return []
    return parse_who(stdout.decode("utf-8", "replace"))
