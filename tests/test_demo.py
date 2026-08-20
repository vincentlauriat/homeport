"""Le mode démo fournit le même contrat que status.build — sans aucun accès système."""
import asyncio

from homeport import demo


def test_demo_snapshot_contract():
    d = asyncio.run(demo.build("localhost"))
    for key in ("groups", "summary", "system", "health", "network", "nvme", "wan", "public_ip", "docker_available"):
        assert key in d, key
    assert d["summary"]["total"] == sum(len(g["services"]) for g in d["groups"])
    assert d["summary"]["total"] >= 12
    # Un warn pour montrer les états, le reste up : la démo raconte une maison saine.
    assert d["summary"]["warn"] == 1
    service = d["groups"][0]["services"][0]
    for key in ("id", "name", "icon", "state", "state_label", "sources", "extra",
                "uptime", "cpu_percent", "restartable", "availability", "url"):
        assert key in service, key
    assert d["health"]["alerts"] is not None
    assert d["system"]["hostname"] == "demo"


def test_demo_history_7_jours():
    samples = demo.history(hours=168)
    assert len(samples) > 500
    assert {"ts", "cpu_pct", "mem_pct", "temp_c", "nvme_temp_c"} <= set(samples[0])
    # Déterministe : deux appels identiques.
    assert samples[:10] == demo.history(hours=168)[:10]


def test_demo_devices_et_outages():
    devices = demo.devices()
    assert devices["summary"]["total"] == len(devices["devices"]) > 10
    assert devices["summary"]["new"] == 1
    outages = demo.outages(hours=24)
    assert len(outages["outages"]) == 1


def test_endpoints_en_mode_demo(monkeypatch):
    from fastapi.testclient import TestClient
    from homeport import main
    monkeypatch.setattr(main, "DEMO", True)
    client = TestClient(main.app)
    assert client.get("/api/status").json()["system"]["hostname"] == "demo"
    assert len(client.get("/api/history?hours=24").json()) > 100
    assert client.get("/api/devices").json()["summary"]["new"] == 1
    assert client.get("/").status_code == 200
