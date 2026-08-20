"""Inventaire des appareils : la MAC est l'identité, l'IP un attribut du moment."""
from pathlib import Path

import pytest

from homeport.collectors import devices


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    devices.init_db(path)
    return path


def test_normalize_mac():
    assert devices.normalize_mac("9C-A2-F4-AF-B4-F4") == "9c:a2:f4:af:b4:f4"
    assert devices.normalize_mac("9c:a2:f4:af:b4:f4") == "9c:a2:f4:af:b4:f4"
    assert devices.normalize_mac("zz:zz:zz:zz:zz:zz") is None
    assert devices.normalize_mac("9c:a2:f4") is None


def test_peuplement_initial_acquitte(db: Path):
    """Table vide -> les appareils déjà là ne sont PAS « nouveaux » (anti-avalanche HA)."""
    devices.upsert_seen(db, [{"ip": "192.168.68.1", "mac": "9c:a2:f4:af:b4:f4"}], now=1000)
    rows = devices.list_devices(db)
    assert len(rows) == 1
    assert rows[0]["acknowledged"] == 1
    assert rows[0]["first_seen"] == 1000


def test_nouvel_appareil_non_acquitte(db: Path):
    devices.upsert_seen(db, [{"ip": "192.168.68.1", "mac": "9c:a2:f4:af:b4:f4"}], now=1000)
    devices.upsert_seen(db, [{"ip": "192.168.68.99", "mac": "aa:bb:cc:dd:ee:ff"}], now=2000)
    new = devices.unacknowledged(db)
    assert [d["mac"] for d in new] == ["aa:bb:cc:dd:ee:ff"]
    assert new[0]["first_seen"] == 2000


def test_upsert_met_a_jour_presence_sans_toucher_les_metas(db: Path):
    devices.upsert_seen(db, [{"ip": "192.168.68.1", "mac": "9c:a2:f4:af:b4:f4"}], now=1000)
    devices.update_meta(db, "9c:a2:f4:af:b4:f4", {"name": "Routeur Deco", "category": "réseau"})
    devices.upsert_seen(db, [{"ip": "192.168.68.2", "mac": "9c:a2:f4:af:b4:f4"}], now=5000)
    row = devices.list_devices(db)[0]
    assert row["last_seen"] == 5000
    assert row["last_ip"] == "192.168.68.2"
    assert row["first_seen"] == 1000          # jamais réécrit
    assert row["name"] == "Routeur Deco"      # jamais touché par l'upsert
    assert row["category"] == "réseau"


def test_update_meta_mac_inconnue(db: Path):
    assert devices.update_meta(db, "aa:aa:aa:aa:aa:aa", {"name": "x"}) is False


def test_update_meta_champs_filtres(db: Path):
    """Seuls name/note/category/acknowledged/mdns_name sont modifiables — pas first_seen."""
    devices.upsert_seen(db, [{"ip": "1.2.3.4", "mac": "aa:bb:cc:dd:ee:ff"}], now=1000)
    devices.update_meta(db, "aa:bb:cc:dd:ee:ff", {"first_seen": 1, "name": "ok"})
    row = devices.list_devices(db)[0]
    assert row["first_seen"] == 1000
    assert row["name"] == "ok"


def test_display_name_priorites():
    base = {"name": None, "mdns_name": None, "mac": "9c:a2:f4:af:b4:f4"}
    assert devices.display_name({**base, "name": "Routeur"}, "TP-Link") == ("Routeur", "manuel")
    assert devices.display_name({**base, "mdns_name": "deco"}, "TP-Link") == ("deco", "mdns")
    assert devices.display_name(base, "TP-Link") == ("TP-Link", "fabricant")
    assert devices.display_name(base, None) == ("9c:a2:f4:af:b4:f4", "inconnu")


def test_list_trie_par_derniere_activite(db: Path):
    devices.upsert_seen(db, [{"ip": "1.1.1.1", "mac": "aa:aa:aa:aa:aa:aa"}], now=1000)
    devices.upsert_seen(db, [{"ip": "2.2.2.2", "mac": "bb:bb:bb:bb:bb:bb"}], now=3000)
    assert [d["mac"] for d in devices.list_devices(db)] == [
        "bb:bb:bb:bb:bb:bb", "aa:aa:aa:aa:aa:aa",
    ]
