"""Livre de bord : les événements marquants sont enregistrés une fois, relus par fenêtre
et par famille, et oubliés après la rétention — la mémoire longue du port."""
from pathlib import Path

import pytest

from homeport.collectors import events


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    path = tmp_path / "t.db"
    events.init_db(path)
    return path


def test_record_et_query_ordre_antichronologique(db: Path):
    events.record(db, "service.down", "down", "jellyfin", now=1000)
    events.record(db, "service.up", "up", "jellyfin", detail="4 min", now=1240)
    rows = events.query(db, days=7, now=2000)
    assert [r["kind"] for r in rows] == ["service.up", "service.down"]
    assert rows[0] == {
        "ts": 1240,
        "kind": "service.up",
        "severity": "up",
        "subject": "jellyfin",
        "detail": "4 min",
    }
    assert rows[1]["detail"] is None


def test_query_filtre_par_famille(db: Path):
    events.record(db, "service.down", "down", "gitea", now=1000)
    events.record(db, "internet.down", "down", "wan", now=1001)
    events.record(db, "device.new", "warn", "aa:bb:cc:dd:ee:ff", now=1002)
    rows = events.query(db, days=7, kinds=["service.", "internet."], now=2000)
    assert {r["kind"] for r in rows} == {"service.down", "internet.down"}


def test_query_fenetre_et_limite(db: Path):
    old = 2000 - 8 * 86400
    events.record(db, "boot", "warn", "system", now=old)
    for i in range(5):
        events.record(db, "service.down", "down", f"svc{i}", now=1000 + i)
    rows = events.query(db, days=7, now=2000)
    assert len(rows) == 5  # l'événement vieux de 8 jours est hors fenêtre
    rows = events.query(db, days=7, limit=2, now=2000)
    assert [r["subject"] for r in rows] == ["svc4", "svc3"]


def test_prune(db: Path):
    import sqlite3

    now = 400 * 86400
    events.record(db, "boot", "warn", "system", now=now - 370 * 86400)
    events.record(db, "service.down", "down", "gitea", now=now - 10)
    events.prune(db, retention_days=365, now=now)
    with sqlite3.connect(db) as conn:
        remaining = conn.execute("SELECT kind FROM events").fetchall()
    assert remaining == [("service.down",)]


def test_init_db_idempotent(db: Path):
    events.init_db(db)  # une seconde initialisation ne détruit rien
    events.record(db, "boot", "warn", "system", now=1000)
    events.init_db(db)
    assert len(events.query(db, days=7, now=2000)) == 1
