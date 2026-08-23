"""GET /api/events : le livre de bord fusionne la table events et les actions admin."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from homeport import actions, main
from homeport.collectors import events


@pytest.fixture()
def client(tmp_path: Path, monkeypatch):
    db = tmp_path / "t.db"
    events.init_db(db)
    actions.init_db(db)
    monkeypatch.setattr(main.cfg, "DB_PATH", db)
    # Pas de lifespan : on ne veut ni jobs de fond ni MQTT dans les tests.
    return TestClient(main.app), db


def _allow(monkeypatch, allowed: bool):
    async def fake_authorize(ip, login):
        return allowed
    monkeypatch.setattr(main.actions, "authorize", fake_authorize)


def test_fusion_events_et_actions_triee(client, monkeypatch):
    http, db = client
    import time

    _allow(monkeypatch, True)  # admin : l'identité (detail) est visible
    now = time.time()
    events.record(db, "service.down", "down", "gitea", now=now - 300)
    actions.record(db, "vincent@tailnet", "restart", "gitea", True, now=now - 200)
    events.record(db, "service.up", "up", "gitea", detail="3 min", now=now - 100)

    data = http.get("/api/events?days=1").json()
    assert [e["kind"] for e in data["events"]] == ["service.up", "action.restart", "service.down"]
    action = data["events"][1]
    assert action["subject"] == "gitea"
    assert action["detail"] == "vincent@tailnet"
    assert action["severity"] == "up"


def test_identite_masquee_pour_lan(client, monkeypatch):
    http, db = client
    import time

    _allow(monkeypatch, False)  # lecteur LAN non authentifié
    actions.record(db, "vincent@tailnet", "restart", "gitea", True, now=time.time() - 100)
    action = http.get("/api/events?days=1").json()["events"][0]
    assert action["kind"] == "action.restart"
    assert action["subject"] == "gitea"  # l'événement reste visible
    assert action["detail"] is None       # mais pas l'identité de l'admin


def test_filtre_kinds_exclut_les_actions(client):
    http, db = client
    import time

    now = time.time()
    events.record(db, "service.down", "down", "gitea", now=now - 300)
    actions.record(db, "vincent@tailnet", "restart", "gitea", True, now=now - 200)

    data = http.get("/api/events?days=1&kinds=service.").json()
    assert [e["kind"] for e in data["events"]] == ["service.down"]

    data = http.get("/api/events?days=1&kinds=action.").json()
    assert [e["kind"] for e in data["events"]] == ["action.restart"]


def test_action_echouee_en_severite_down(client):
    http, db = client
    import time

    actions.record(db, "vincent@tailnet", "wake", "aa:bb:cc:dd:ee:ff", False, now=time.time() - 10)
    data = http.get("/api/events?days=1").json()
    assert data["events"][0]["severity"] == "down"


def test_fenetre_et_limite_bornees(client):
    http, db = client
    import time

    now = time.time()
    for i in range(5):
        events.record(db, "service.down", "down", f"svc{i}", now=now - 10 - i)
    data = http.get("/api/events?days=9999&limit=2").json()
    assert len(data["events"]) == 2

    old = now - 2 * 86400
    events.record(db, "boot", "warn", "system", now=old)
    data = http.get("/api/events?days=1").json()
    assert all(e["kind"] != "boot" for e in data["events"])


def test_base_indisponible_repond_vide(client, monkeypatch):
    http, _ = client
    monkeypatch.setattr(main.cfg, "DB_PATH", Path("/nonexistent/nope.db"))
    data = http.get("/api/events?days=1")
    assert data.status_code == 200
    assert data.json()["events"] == []
