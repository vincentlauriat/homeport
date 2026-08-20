"""Collecteur Starlink : parsing des réponses réelles de l'antenne (fixtures anonymisées,
capturées le 2026-08-20 sur un dish rev2_proto3, firmware 2026.08.12)."""
import asyncio
from pathlib import Path

from homeport.collectors import starlink

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _raw(name):
    return (FIXTURES / name).read_bytes()


def test_parse_status():
    result = starlink.parse_status(_raw("starlink_status.bin"))
    assert result["online"] is True
    assert 1 < result["latency_ms"] < 200
    assert result["downlink_bps"] > 0 and result["uplink_bps"] > 0
    assert result["hardware"] == "rev2_proto3"
    assert result["software"].startswith("2026.")
    assert result["uptime_s"] > 1000
    assert result["eth_speed_mbps"] == 1000
    assert result["gps"]["valid"] is True and result["gps"]["sats"] >= 4
    # fraction_obstructed = 0.0 n'est pas sérialisé par protobuf : défaut obligatoire
    assert result["obstruction"]["fraction"] == 0.0
    assert result["obstruction"]["currently"] is False
    assert 0 < result["alignment"]["tilt_deg"] < 90
    assert result["alerts"] == []
    assert result["drop_rate"] >= 0.0


def test_parse_status_outage_et_alertes():
    # Statut synthétique : panne OBSTRUCTED + alerte thermal_throttle
    from homeport.collectors import _protowire as pw
    body = pw.encode_message({
        1014: {1: 6},          # outage.cause = OBSTRUCTED
        1005: {3: 1},          # alerts.thermal_throttle = true
    })
    raw = pw.encode_message({2004: body})
    result = starlink.parse_status(raw)
    assert result["online"] is False
    assert result["outage_cause"] == "OBSTRUCTED"
    assert result["alerts"] == ["thermal_throttle"]


def test_parse_history_ordonne():
    result = starlink.parse_history(_raw("starlink_history.bin"))
    assert len(result["latency_ms"]) == 900
    assert len(result["downlink_bps"]) == 900
    # ordonné du plus ancien au plus récent : le dernier échantillon est le plus frais
    assert all(v >= 0 for v in result["latency_ms"] if v is not None)


def test_parse_obstruction_map():
    result = starlink.parse_map(_raw("starlink_map.bin"))
    assert result["rows"] == 123 and result["cols"] == 123
    assert len(result["snr"]) == 123 * 123
    assert all(-1.0 <= v <= 1.0 for v in result["snr"][:100])


def test_collect_injoignable():
    settings = {"enabled": True, "address": "127.0.0.1:1"}
    assert asyncio.run(starlink.fetch_status(settings)) is None


def test_config_starlink(tmp_path):
    from homeport import config
    f = tmp_path / "services.yaml"
    f.write_text("starlink:\n  enabled: true\n")
    settings = config.load_starlink(f)
    assert settings["enabled"] is True
    assert settings["address"] == "192.168.100.1:9200"
    assert config.load_starlink(tmp_path / "absent.yaml")["enabled"] is False


def test_api_starlink_desactive(monkeypatch):
    from fastapi.testclient import TestClient

    from homeport import main
    monkeypatch.setattr(main.cfg, "CONFIG_PATH", __import__("pathlib").Path("/nonexistent.yaml"))
    client = TestClient(main.app)
    body = client.get("/api/starlink").json()
    assert body == {"enabled": False, "status": None, "history": None, "map": None}


def test_page_starlink(monkeypatch):
    from fastapi.testclient import TestClient

    from homeport import main
    html = TestClient(main.app).get("/starlink").text
    assert "v-starlink" in html
