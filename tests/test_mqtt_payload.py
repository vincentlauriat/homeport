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
    snapshot = {"summary": {}, "system": {}, "health": {},
                "offsite": {"age_hours": 6.5, "verified_ok": True, "snapshots": 12}}
    payload = mqtt.build_payload(snapshot)
    assert payload["offsite"]["age_hours"] == 6.5
    assert payload["offsite"]["verified_ok"] is True


def test_payload_sans_hors_site():
    payload = mqtt.build_payload({"summary": {}, "system": {}, "health": {}})
    assert payload["offsite"]["age_hours"] is None


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
