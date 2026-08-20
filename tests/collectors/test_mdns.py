"""Noms mDNS via avahi-resolve-address — la plupart des IoT ne s'annoncent pas : l'échec
est le cas normal, silencieux."""
import asyncio

from homeport.collectors import mdns


def test_parse_sortie_normale():
    assert mdns.parse_avahi_output("192.168.68.27\tMacBook-Air.local\n") == "MacBook-Air"


def test_parse_conserve_les_points_internes():
    assert mdns.parse_avahi_output("10.0.0.1\timprimante.bureau.local\n") == "imprimante.bureau"


def test_parse_sortie_vide_ou_erreur():
    assert mdns.parse_avahi_output("") is None
    assert mdns.parse_avahi_output("Failed to resolve address\n") is None


def test_resolve_many_ignore_les_echecs(monkeypatch):
    async def fake_resolve(ip):
        return "MacBook-Air" if ip == "192.168.68.27" else None

    monkeypatch.setattr(mdns, "resolve", fake_resolve)
    result = asyncio.run(mdns.resolve_many(["192.168.68.27", "192.168.68.99"]))
    assert result == {"192.168.68.27": "MacBook-Air"}
