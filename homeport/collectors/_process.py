"""Sous-processus courts, avec un timeout qui tue réellement l'enfant.

`asyncio.wait_for(process.communicate(), timeout=...)` seul annule l'*attente* au timeout mais
ne tue pas le process : celui-ci continue de tourner, jamais récupéré. Sur un collecteur appelé
chaque minute (`network.py`), une commande qui bloque (`tailscaled` coincé, par exemple) en
abandonnerait un par cycle — pression croissante sur la table des process de l'hôte.
"""

from __future__ import annotations

import asyncio


async def run(*args: str, timeout: float = 10.0) -> bytes | None:
    """Lance `args`, renvoie stdout brut. `None` si le binaire est absent ou si `timeout` est
    dépassé — l'enfant est alors tué et attendu (`wait()`), jamais laissé tourner seul."""
    try:
        process = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
    except OSError:
        return None

    try:
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except TimeoutError:
        process.kill()
        await process.wait()
        return None

    return stdout
