"""GET /api/devices : fusion inventaire SQLite + présence live du snapshot réseau."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from homeport import background, main
from homeport.collectors import devices


@pytest.fixture()
def client(tmp_path: Path, monkeypatch):
    db = tmp_path / "t.db"
    devices.init_db(db)
    monkeypatch.setattr(main.cfg, "DB_PATH", db)
    # Pas de lifespan : on ne veut ni jobs de fond ni MQTT dans les tests.
    return TestClient(main.app), db


def test_api_devices_fusionne_presence_et_metas(client, monkeypatch):
    http, db = client
    devices.upsert_seen(db, [{"ip": "192.168.68.1", "mac": "9c:a2:f4:af:b4:f4"}], now=1000)
    devices.update_meta(db, "9c:a2:f4:af:b4:f4", {"name": "Routeur Deco"})
    monkeypatch.setattr(
        background, "snapshot",
        lambda: {"network": {"data": {"lan_neighbors": [
            {"ip": "192.168.68.1", "mac": "9c:a2:f4:af:b4:f4", "interface": "eth0"}
        ], "tailscale_peers": []}, "measured_at": 1}},
    )
    body = http.get("/api/devices").json()
    device = body["devices"][0]
    assert device["online"] is True
    assert device["display_name"] == "Routeur Deco"
    assert device["name_source"] == "manual"
    assert body["summary"]["total"] == 1
    assert body["summary"]["online"] == 1


def test_patch_nomme_un_appareil(client):
    http, db = client
    devices.upsert_seen(db, [{"ip": "1.1.1.1", "mac": "aa:bb:cc:dd:ee:ff"}], now=1000)
    response = http.patch(
        "/api/devices/aa:bb:cc:dd:ee:ff", json={"name": "Imprimante", "category": "media"}
    )
    assert response.status_code == 200
    row = devices.list_devices(db)[0]
    assert row["name"] == "Imprimante"
    assert row["category"] == "media"


def test_patch_acquitte(client):
    http, db = client
    devices.upsert_seen(db, [{"ip": "1.1.1.1", "mac": "aa:aa:aa:aa:aa:aa"}], now=1000)
    devices.upsert_seen(db, [{"ip": "2.2.2.2", "mac": "bb:bb:bb:bb:bb:bb"}], now=2000)
    http.patch("/api/devices/bb:bb:bb:bb:bb:bb", json={"acknowledged": True})
    assert devices.unacknowledged(db) == []


def test_patch_valide_strictement(client):
    http, db = client
    devices.upsert_seen(db, [{"ip": "1.1.1.1", "mac": "aa:bb:cc:dd:ee:ff"}], now=1000)
    assert http.patch("/api/devices/pas-une-mac", json={"name": "x"}).status_code == 404
    assert http.patch("/api/devices/00:00:00:00:00:00", json={"name": "x"}).status_code == 404
    assert http.patch("/api/devices/aa:bb:cc:dd:ee:ff", json={"name": "x" * 65}).status_code == 422
    assert http.patch("/api/devices/aa:bb:cc:dd:ee:ff", json={"note": "x" * 501}).status_code == 422
    assert http.patch("/api/devices/aa:bb:cc:dd:ee:ff", json={"category": "licorne"}).status_code == 422
    assert http.patch("/api/devices/aa:bb:cc:dd:ee:ff", json={"first_seen": 1}).status_code == 422


def test_patch_efface_avec_null(client):
    http, db = client
    devices.upsert_seen(db, [{"ip": "1.1.1.1", "mac": "aa:bb:cc:dd:ee:ff"}], now=1000)
    http.patch("/api/devices/aa:bb:cc:dd:ee:ff", json={"name": "X"})
    http.patch("/api/devices/aa:bb:cc:dd:ee:ff", json={"name": None})
    assert devices.list_devices(db)[0]["name"] is None


def test_api_devices_base_indisponible(client, monkeypatch):
    """Jamais de 500 : base morte -> inventaire vide + drapeau, le live reste."""
    http, _ = client
    monkeypatch.setattr(main.cfg, "DB_PATH", Path("/nonexistent/dir/x.db"))
    monkeypatch.setattr(background, "snapshot", lambda: {})
    response = http.get("/api/devices")
    assert response.status_code == 200
    assert response.json()["devices"] == []
    assert response.json()["inventory_available"] is False


def test_page_reseau_repond(client, monkeypatch):
    http, _ = client
    monkeypatch.setattr(background, "snapshot", lambda: {})
    response = http.get("/reseau")
    assert response.status_code == 200
    assert "Network" in response.text


def test_api_outages(client, monkeypatch, tmp_path):
    from homeport.collectors import wan as wan_collector
    http, db = client
    wan_collector.init_db(db)
    wan_collector.record(db, {"online": False, "latency_ms": None}, now=1000)
    wan_collector.record(db, {"online": True, "latency_ms": 10.0}, now=1060)
    body = http.get("/api/outages?hours=24000000").json()
    assert body["outages"][0]["minutes"] == 1


def test_page_historique_repond(client, monkeypatch):
    http, _ = client
    monkeypatch.setattr(background, "snapshot", lambda: {})
    response = http.get("/historique")
    assert response.status_code == 200
    assert "History" in response.text
