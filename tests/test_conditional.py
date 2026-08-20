"""Dégradation gracieuse hors Raspberry Pi / sans Tailscale / sans Docker (spec §4.2).

Chaque binaire absent (`_process.run` → None, comme le vrai comportement sur OSError) doit
retirer sa section sans jamais lever — le dashboard reste sain sur n'importe quel Linux.
"""
import asyncio

from homeport import actions
from homeport.collectors import _process, hardware, network


async def _missing_binary(*args, **kwargs):
    return None


def test_throttling_sans_vcgencmd(monkeypatch):
    monkeypatch.setattr(_process, "run", _missing_binary)
    result = asyncio.run(hardware.throttling())
    assert result["available"] is False
    assert result["healthy"] is None


def test_network_sans_tailscale_ni_ip(monkeypatch):
    monkeypatch.setattr(_process, "run", _missing_binary)
    result = asyncio.run(network.collect())
    assert result["tailscale_peers"] == []
    assert result["lan_neighbors"] == []
    assert result["tailscale_summary"]["peers_total"] == 0


def test_authorize_refuse_sans_tailscale(monkeypatch):
    monkeypatch.setattr(_process, "run", _missing_binary)
    # IP du tailnet mais binaire absent : impossible de vérifier l'identité → refus.
    assert asyncio.run(actions.authorize("100.100.1.1", "admin@example.com")) is False
