"""Rafraîchissement en tâche de fond des données lentes.

Le tableau de bord actuel répond en quelques millisecondes. Les trois nouveaux collecteurs,
eux, sont lents : `apt list` prend une seconde, une interrogation de registre Docker fait des
allers-retours sur Internet, `journalctl` peut brasser des milliers de lignes. Les appeler
depuis le chemin d'une requête ferait régresser une page qui marche pour lui ajouter des
fonctions.

Ils tournent donc en boucles indépendantes, chacune à sa cadence, et `/api/status` se contente
de lire le dernier résultat connu. Tant qu'une mesure n'est pas revenue, l'interface annonce
« pas encore mesuré » plutôt que d'attendre.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

_results: dict[str, dict] = {}
_tasks: list[asyncio.Task] = []


def snapshot() -> dict[str, dict]:
    """Dernières valeurs connues, sans jamais bloquer."""
    return dict(_results)


async def _loop(key: str, producer: Callable[[], Awaitable], interval: float) -> None:
    while True:
        try:
            value = await producer()
            _results[key] = {"data": value, "measured_at": int(time.time()), "error": None}
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # une source en panne ne doit pas tuer sa boucle
            previous = _results.get(key, {})
            _results[key] = {**previous, "error": f"{type(exc).__name__}: {exc}"}
        await asyncio.sleep(interval)


def start(jobs: dict[str, tuple[Callable[[], Awaitable], float]]) -> None:
    """jobs : {clé: (producteur, intervalle en secondes)}"""
    stop()
    for key, (producer, interval) in jobs.items():
        _tasks.append(asyncio.create_task(_loop(key, producer, interval), name=f"homeport-{key}"))


def stop() -> None:
    for task in _tasks:
        task.cancel()
    _tasks.clear()
