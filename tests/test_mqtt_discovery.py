"""Découverte Home Assistant : identifiants dérivés du base_topic (continuité d'instance,
plusieurs Homeport possibles sur un même broker) et noms de capteurs dans la langue configurée."""
from homeport import mqtt


def _payload():
    return mqtt.build_payload({
        "summary": {"up": 1, "warn": 0, "down": 0},
        "health": {"alerts": [], "backups": [], "apt": None, "images": None, "journal": None},
        "system": {"hostname": "h", "uptime": {"seconds": 1}, "load": {"percent": 1.0},
                    "memory": {"percent": 1.0}, "temperature_c": 40.0,
                    "storage_temperature_c": None, "undervoltage": False, "disks": []},
        "wan": None,
        "network": {"new_devices": {"count": 0, "names": []}},
        "nvme": None,
        "public_ip": None,
    })


def test_unique_ids_et_topics_derivent_du_base_topic():
    messages = mqtt.build_discovery(_payload(), "h", base="raspweb", prefix="homeassistant")
    topics = [t for t, _ in messages]
    configs = [c for _, c in messages]
    assert all("/raspweb/" in t for t in topics), topics[:3]
    assert any(c.get("unique_id") == "raspweb_services_down" for c in configs)
    assert not any("homeport" in (c.get("unique_id") or "") for c in configs)


def test_base_topic_par_defaut():
    messages = mqtt.build_discovery(_payload(), "h", base="homeport", prefix="homeassistant")
    assert any(c.get("unique_id") == "homeport_services_down" for _, c in messages)
