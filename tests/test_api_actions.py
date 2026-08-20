"""Routes d'action : refusées sans identité Tailscale valide, journalisées sinon.
L'autorisation elle-même est testée dans test_actions.py — ici on teste le câblage HTTP."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from homeport import actions, main
from homeport.collectors import devices, wol


@pytest.fixture()
def client(tmp_path: Path, monkeypatch):
    db = tmp_path / "t.db"
    devices.init_db(db)
    actions.init_db(db)
    monkeypatch.setattr(main.cfg, "DB_PATH", db)
    yaml_file = tmp_path / "services.yaml"
    yaml_file.write_text(
        "actions:\n  admin: admin@example.com\n"
        "groups:\n  - name: G\n    services:\n"
        "      - {id: ha, name: HA, docker: homeassistant, restartable: true}\n"
        "      - {id: mq, name: MQ, docker: mosquitto}\n"
    )
    monkeypatch.setattr(main.cfg, "CONFIG_PATH", yaml_file)
    return TestClient(main.app), db


def _allow(monkeypatch, allowed: bool):
    async def fake_authorize(ip, login):
        return allowed
    monkeypatch.setattr(main.actions, "authorize", fake_authorize)


def test_restart_refuse_sans_identite(client, monkeypatch):
    http, db = client
    _allow(monkeypatch, False)
    assert http.post("/api/actions/restart/ha").status_code == 403
    assert actions.recent(db) == []          # un refus n'est pas une action


def test_restart_refuse_service_non_declare(client, monkeypatch):
    http, _ = client
    _allow(monkeypatch, True)
    assert http.post("/api/actions/restart/mq").status_code == 404       # pas restartable
    assert http.post("/api/actions/restart/inconnu").status_code == 404


def test_restart_execute_et_journalise(client, monkeypatch):
    http, db = client
    _allow(monkeypatch, True)
    calls = []

    async def fake_restart(service):
        calls.append(service.docker)
        return True

    monkeypatch.setattr(main.actions, "restart", fake_restart)
    response = http.post("/api/actions/restart/ha")
    assert response.status_code == 200
    assert calls == ["homeassistant"]
    journal = actions.recent(db)
    assert journal[0]["kind"] == "restart" and journal[0]["target"] == "ha" and journal[0]["ok"] == 1


def test_wake_refuse_sans_identite(client, monkeypatch):
    http, _ = client
    _allow(monkeypatch, False)
    assert http.post("/api/actions/wake/aa:bb:cc:dd:ee:ff").status_code == 403


def test_wake_envoie_le_paquet(client, monkeypatch):
    http, db = client
    devices.upsert_seen(db, [{"ip": "1.1.1.1", "mac": "aa:bb:cc:dd:ee:ff"}], now=1000)
    _allow(monkeypatch, True)
    sent = []
    monkeypatch.setattr(wol, "send", lambda mac: sent.append(mac))
    assert http.post("/api/actions/wake/aa:bb:cc:dd:ee:ff").status_code == 200
    assert sent == ["aa:bb:cc:dd:ee:ff"]
    assert http.post("/api/actions/wake/00:00:00:00:00:00").status_code == 404  # inconnu


def test_whoami(client, monkeypatch):
    http, _ = client
    _allow(monkeypatch, True)
    body = http.get("/api/whoami").json()
    assert body["can_act"] is True
    _allow(monkeypatch, False)
    assert http.get("/api/whoami").json()["can_act"] is False


def test_journal_expose(client, monkeypatch):
    http, db = client
    actions.record(db, "admin@example.com", "restart", "ha", True, now=1000)
    body = http.get("/api/actions").json()
    assert body["actions"][0]["target"] == "ha"
