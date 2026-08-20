"""IP publique : relevée une fois par heure, historisée seulement quand elle change."""
import sqlite3
from pathlib import Path

import pytest

from homeport.collectors import public_ip


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    path = tmp_path / "t.db"
    public_ip.init_db(path)
    return path


def test_parse_ip():
    assert public_ip.parse_ip("82.65.10.20\n") == "82.65.10.20"
    assert public_ip.parse_ip("<html>erreur</html>") is None
    assert public_ip.parse_ip("") is None


def test_track_premiere_ip(db: Path):
    changed = public_ip.track(db, "82.65.10.20", now=1000)
    assert changed is True
    assert public_ip.current(db) == {"ip": "82.65.10.20", "changed_ts": 1000}


def test_track_ip_stable_puis_changement(db: Path):
    public_ip.track(db, "82.65.10.20", now=1000)
    assert public_ip.track(db, "82.65.10.20", now=2000) is False       # pas de nouvelle ligne
    assert public_ip.current(db)["changed_ts"] == 1000                 # date du VRAI changement
    assert public_ip.track(db, "90.1.2.3", now=3000) is True
    assert public_ip.current(db) == {"ip": "90.1.2.3", "changed_ts": 3000}
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM public_ip_history").fetchone()[0] == 2


def test_current_sans_donnees(db: Path):
    assert public_ip.current(db) is None
