"""Disponibilité par service : les états sont échantillonnés en fond ; le « ça marche là »
devient « 99,8 % sur 7 j · 2 incidents »."""
from pathlib import Path

import pytest

from homeport.collectors import service_history


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    path = tmp_path / "t.db"
    service_history.init_db(path)
    return path


def test_record_et_stats(db: Path):
    # 10 échantillons : ha passe down sur 2 échantillons (1 incident), mq reste up.
    sequence = ["up", "up", "up", "down", "down", "up", "up", "up", "up", "up"]
    for i, state in enumerate(sequence):
        service_history.record_states(db, {"ha": state, "mq": "up"}, now=1000 + i * 60)

    stats = service_history.stats(db, hours=24, now=1000 + 10 * 60)
    assert stats["mq"]["uptime_pct"] == 100.0
    assert stats["mq"]["incidents"] == 0
    assert stats["ha"]["uptime_pct"] == 80.0
    assert stats["ha"]["incidents"] == 1
    assert stats["ha"]["longest_minutes"] == 2          # 2 échantillons × 60 s


def test_warn_compte_comme_incident_mais_pas_down(db: Path):
    for i, state in enumerate(["up", "warn", "up"]):
        service_history.record_states(db, {"svc": state}, now=1000 + i * 60)
    stats = service_history.stats(db, hours=24, now=1000 + 3 * 60)
    assert stats["svc"]["incidents"] == 1
    assert round(stats["svc"]["uptime_pct"], 1) == 66.7  # warn n'est pas « up »


def test_stats_sans_donnees(db: Path):
    assert service_history.stats(db, hours=24) == {}


def test_prune(db: Path):
    service_history.record_states(db, {"svc": "up"}, now=1000)
    service_history.record_states(db, {"svc": "up"}, now=800000)
    service_history.prune(db, retention_days=7, now=800000)
    stats = service_history.stats(db, hours=24 * 30, now=800000)
    assert stats["svc"]["uptime_pct"] == 100.0
    import sqlite3
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM service_samples").fetchone()[0] == 1
