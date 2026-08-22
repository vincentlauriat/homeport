"""Collecteur Livebox : normalisation des réponses sysbus, box injoignable, ring de latences."""
import asyncio
import json

import httpx
import pytest

from homeport.collectors import livebox

WAN_OK = {"status": True, "data": {
    "WanState": "up", "LinkType": "xgs-pon", "LinkState": "up",
    "GponState": "O5_Operation", "Protocol": "dhcp", "ConnectionState": "Bound",
    "LastConnectionError": "None", "ConnectionStateIPv6": "Bound",
}}
INFO_OK = {"status": {
    "ProductClass": "Livebox W7", "SerialNumber": "IG0000000000000",
    "SoftwareVersion": "SGW7-fr-G03.R08.C03_00", "BaseMAC": "c8:7f:2b:00:00:00",
}}


@pytest.fixture(autouse=True)
def _ring_propre():
    livebox.reset()
    yield
    livebox.reset()


def _collect(handler) -> dict:
    async def run():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            return await livebox._collect(client, "192.168.100.254")
    return asyncio.run(run())


def _handler_ok(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    if body["service"] == "NMC":
        return httpx.Response(200, json=WAN_OK)
    return httpx.Response(200, json=INFO_OK)


def test_nominal_normalise_et_mesure_la_latence():
    data = _collect(_handler_ok)
    assert data["reachable"] is True
    assert data["online"] is True
    assert data["link_type"] == "xgs-pon"
    assert data["gpon_state"] == "O5_Operation"
    assert data["connection_state_ipv6"] == "Bound"
    assert data["model"] == "Livebox W7"
    assert data["firmware"].startswith("SGW7")
    assert isinstance(data["latency_ms"], float)
    assert data["latency_history"] == [data["latency_ms"]]


def test_wan_coupe_reste_joignable():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["service"] == "NMC":
            down = {"status": True, "data": {**WAN_OK["data"], "WanState": "down", "LinkState": "down"}}
            return httpx.Response(200, json=down)
        return httpx.Response(200, json=INFO_OK)

    data = _collect(handler)
    assert data["reachable"] is True
    assert data["online"] is False
    assert data["wan_state"] == "down"


def test_box_injoignable_sans_exception():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route to host")

    data = _collect(handler)
    assert data == {"reachable": False, "online": False, "latency_ms": None, "latency_history": []}


def test_permission_denied_traite_comme_injoignable():
    # Un firmware qui verrouille getWANStatus renvoie errors sans status/data exploitables.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": None, "errors": [{"error": 13}]})

    data = _collect(handler)
    assert data["reachable"] is False


def test_ring_de_latences_s_accumule():
    _collect(_handler_ok)
    data = _collect(_handler_ok)
    assert len(data["latency_history"]) == 2
