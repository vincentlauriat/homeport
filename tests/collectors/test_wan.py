"""Santé de la connexion Internet : joignabilité TCP de deux résolveurs publics + résolution
DNS, échantillonnée en fond et historisée — « la box a-t-elle coupé cette nuit ? »."""
import asyncio
import sqlite3
from pathlib import Path

import pytest

from homeport.collectors import wan

# --- Mesure ------------------------------------------------------------------------------

def test_measure_en_ligne(monkeypatch):
    async def fake_probe(host, port, timeout):
        return 12.5 if host == "1.1.1.1" else 18.1

    monkeypatch.setattr(wan, "_tcp_latency_ms", fake_probe)
    monkeypatch.setattr(wan, "_dns_resolves", lambda: True)
    result = asyncio.run(wan.measure())
    assert result["online"] is True
    assert result["latency_ms"] == 15.3        # médiane des deux sondes
    assert result["dns_ok"] is True


def test_measure_hors_ligne(monkeypatch):
    async def fake_probe(host, port, timeout):
        return None

    monkeypatch.setattr(wan, "_tcp_latency_ms", fake_probe)
    monkeypatch.setattr(wan, "_dns_resolves", lambda: False)
    result = asyncio.run(wan.measure())
    assert result["online"] is False
    assert result["latency_ms"] is None


def test_measure_degradee_un_seul_resolveur(monkeypatch):
    async def fake_probe(host, port, timeout):
        return 20.0 if host == "1.1.1.1" else None

    monkeypatch.setattr(wan, "_tcp_latency_ms", fake_probe)
    monkeypatch.setattr(wan, "_dns_resolves", lambda: True)
    result = asyncio.run(wan.measure())
    assert result["online"] is True            # un résolveur suffit : c'est l'autre qui a un souci
    assert result["latency_ms"] == 20.0


# --- Historique et coupures ---------------------------------------------------------------

@pytest.fixture()
def db(tmp_path: Path) -> Path:
    path = tmp_path / "t.db"
    wan.init_db(path)
    return path


def test_record_et_synthese(db: Path):
    for i, online in enumerate([1, 1, 0, 0, 0, 1, 1]):
        wan.record(db, {"online": bool(online), "latency_ms": 15.0 if online else None},
                   now=1000 + i * 60)
    summary = wan.summarize(db, hours=24, now=1000 + 7 * 60)
    assert summary["online"] is True                     # dernier échantillon
    assert summary["outages_24h"] == 1                   # une coupure (3 échantillons off)
    assert summary["last_outage_ts"] == 1000 + 2 * 60    # début de la coupure
    assert summary["last_outage_minutes"] == 3           # 3 échantillons × 60 s
    assert summary["latency_ms"] == 15.0                 # médiane des échantillons en ligne


def test_synthese_sans_donnees(db: Path):
    summary = wan.summarize(db, hours=24)
    assert summary["online"] is None
    assert summary["outages_24h"] == 0


def test_prune(db: Path):
    wan.record(db, {"online": True, "latency_ms": 10.0}, now=1000)
    wan.record(db, {"online": True, "latency_ms": 10.0}, now=800000)
    wan.prune(db, retention_days=7, now=800000)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM wan_samples").fetchone()[0] == 1


def test_outages_liste_detaillee(db: Path):
    for i, online in enumerate([1, 0, 0, 1, 0, 1]):
        wan.record(db, {"online": bool(online), "latency_ms": 10.0 if online else None},
                   now=1000 + i * 60)
    outages = wan.outages(db, hours=24, now=1000 + 6 * 60)
    assert len(outages) == 2
    assert outages[0] == {"start_ts": 1060, "minutes": 2}
    assert outages[1] == {"start_ts": 1240, "minutes": 1}
