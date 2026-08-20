"""build_payload : la partie MQTT testable sans courtier."""
from homeport import mqtt


def test_payload_nouveaux_appareils():
    snapshot = {
        "summary": {},
        "system": {},
        "health": {},
        "network": {"new_devices": {"count": 2, "names": ["Espressif", "aa:bb:…"]}},
    }
    payload = mqtt.build_payload(snapshot)
    assert payload["network"]["new_devices"] == 2
    assert payload["network"]["new_names"] == ["Espressif", "aa:bb:…"]


def test_payload_sans_inventaire():
    payload = mqtt.build_payload({"summary": {}, "system": {}, "health": {}})
    assert payload["network"]["new_devices"] is None


def test_payload_sauvegarde_hors_site():
    snapshot = {"summary": {}, "system": {}, "health": {}}
    payload = mqtt.build_payload(snapshot)
    assert "offsite" not in payload


def test_payload_sans_hors_site():
    payload = mqtt.build_payload({"summary": {}, "system": {}, "health": {}})
    assert "offsite" not in payload


def test_payload_usure_ssd_et_ip_publique():
    snapshot = {"summary": {}, "system": {}, "health": {},
                "nvme": {"percent_used": 3},
                "public_ip": {"ip": "82.65.10.20", "changed_ts": 1000}}
    payload = mqtt.build_payload(snapshot)
    assert payload["system"]["ssd_wear_pct"] == 3
    assert payload["public_ip"] == "82.65.10.20"


def test_payload_sans_nvme_ni_ip():
    payload = mqtt.build_payload({"summary": {}, "system": {}, "health": {}})
    assert payload["system"]["ssd_wear_pct"] is None
    assert payload["public_ip"] is None


def test_payload_et_decouverte_des_fichiers_detat():
    from homeport import mqtt
    snapshot = {
        "summary": {"up": 1, "warn": 0, "down": 0},
        "health": {"alerts": [], "backups": [], "apt": None, "images": None, "journal": None},
        "system": {"hostname": "h", "uptime": {"seconds": 1}, "load": {"percent": 1.0},
                    "memory": {"percent": 1.0}, "temperature_c": 40.0,
                    "storage_temperature_c": None, "undervoltage": False, "disks": []},
        "wan": None, "network": {"new_devices": {"count": 0, "names": []}},
        "nvme": None, "public_ip": None,
        "status_files": [{"id": "offsite", "name": "Hors-site", "status": "ok",
                          "message": "", "age_hours": 11.0, "stale": False, "level": "up"}],
    }
    payload = mqtt.build_payload(snapshot)
    assert payload["status_files"]["offsite"]["age_hours"] == 11.0
    messages = mqtt.build_discovery(payload, "h", base="raspweb", prefix="homeassistant")
    assert any(c.get("unique_id") == "raspweb_offsite_age" for _, c in messages)
