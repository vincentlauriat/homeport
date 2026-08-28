"""Bug trouvé en vérifiant Contrôle/Classic sur un Mac sans `journalctl` (28/08) : le
chemin « indisponible » de `collect()` n'avait pas la même forme que le chemin réussi — il
manquait `counted`, lu sans garde par `controle.js` (→ littéralement « undefined » affiché)
et par `index.html` (→ valeur vide, silencieuse mais tout aussi fausse)."""

import asyncio

from homeport.collectors import journal

# Clés produites par le chemin réussi (voir collect(), fin de fonction) : le chemin
# indisponible doit rendre exactement les mêmes, sans quoi un consommateur qui lit l'une
# d'elles reçoit `undefined` plutôt qu'une valeur de repli.
_EXPECTED_KEYS = {"available", "total", "muted", "counted", "by_source", "recent", "since"}


def test_collect_returns_the_same_shape_when_journalctl_is_unavailable(monkeypatch):
    async def boom(*args, **kwargs):
        raise FileNotFoundError("journalctl introuvable")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", boom)

    result = asyncio.run(journal.collect())

    assert result["available"] is False
    assert set(result.keys()) == _EXPECTED_KEYS
    assert result["counted"] == 0
