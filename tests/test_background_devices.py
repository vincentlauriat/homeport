"""Le job réseau alimente l'inventaire ; le job mDNS enrichit les noms — sans jamais
toucher les colonnes de Alice (garanti par devices.update_meta/_META_FIELDS)."""
import asyncio
from pathlib import Path

from homeport import main
from homeport.collectors import devices


def test_network_and_track_upserte_les_voisins(tmp_path: Path, monkeypatch):
    db = tmp_path / "t.db"
    devices.init_db(db)
    monkeypatch.setattr(main.cfg, "DB_PATH", db)

    async def fake_collect():
        return {"lan_neighbors": [{"ip": "192.168.68.1", "mac": "9c:a2:f4:af:b4:f4", "interface": "eth0"}],
                "tailscale_peers": [], "tailscale_summary": {}}

    monkeypatch.setattr(main.network, "collect", fake_collect)
    result = asyncio.run(main._network_and_track())
    assert result["lan_neighbors"]                      # le snapshot réseau reste intact
    assert devices.list_devices(db)[0]["mac"] == "9c:a2:f4:af:b4:f4"


def test_network_and_track_survit_sans_base(tmp_path: Path, monkeypatch):
    """Base indisponible (ex. /mnt/ssd démonté) : le snapshot réseau doit sortir quand même."""
    monkeypatch.setattr(main.cfg, "DB_PATH", tmp_path / "nodir" / "t.db")

    async def fake_collect():
        return {"lan_neighbors": [{"ip": "1.1.1.1", "mac": "aa:aa:aa:aa:aa:aa", "interface": "eth0"}],
                "tailscale_peers": [], "tailscale_summary": {}}

    monkeypatch.setattr(main.network, "collect", fake_collect)
    result = asyncio.run(main._network_and_track())     # ne lève pas
    assert result["lan_neighbors"]


def test_refresh_mdns_met_en_cache(tmp_path: Path, monkeypatch):
    db = tmp_path / "t.db"
    devices.init_db(db)
    devices.upsert_seen(db, [{"ip": "192.168.68.27", "mac": "10:2c:b1:7c:d6:fb"}], now=1000)
    monkeypatch.setattr(main.cfg, "DB_PATH", db)

    async def fake_resolve_many(ips):
        return {"192.168.68.27": "MacBook-Air"}

    monkeypatch.setattr(main.mdns, "resolve_many", fake_resolve_many)
    resolved = asyncio.run(main._refresh_mdns())
    assert resolved == 1
    assert devices.list_devices(db)[0]["mdns_name"] == "MacBook-Air"
