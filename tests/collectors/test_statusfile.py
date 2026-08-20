"""Fichiers d'état génériques : un JSON écrit par n'importe quel job (root ou non), affiché
en carte santé et publié en capteur MQTT. Contrat du fichier : voir docs/configuration.md."""
import json
import time

from homeport.collectors import statusfile

ENTRY = {"id": "offsite", "name": "Sauvegarde hors-site", "path": "", "warn_after_hours": 48}


def _write(tmp_path, payload):
    f = tmp_path / "state.json"
    f.write_text(json.dumps(payload))
    return {**ENTRY, "path": str(f)}


def test_ok_recent(tmp_path):
    now = time.time()
    entry = _write(tmp_path, {"status": "ok", "message": "sauvegarde poussée",
                              "last_snapshot_ts": now - 7200})
    result = statusfile.collect(entry, now=now)
    assert result["id"] == "offsite"
    assert result["level"] == "up"
    assert result["age_hours"] == 2.0
    assert result["message"] == "sauvegarde poussée"


def test_ok_mais_en_retard(tmp_path):
    now = time.time()
    entry = _write(tmp_path, {"status": "ok", "last_ts": now - 60 * 3600})
    result = statusfile.collect(entry, now=now)
    assert result["level"] == "warn"
    assert result["stale"] is True


def test_error(tmp_path):
    entry = _write(tmp_path, {"status": "error", "message": "dépôt injoignable"})
    assert statusfile.collect(entry)["level"] == "down"


def test_pending(tmp_path):
    entry = _write(tmp_path, {"status": "pending", "message": "clé à autoriser"})
    result = statusfile.collect(entry)
    assert result["level"] == "warn"
    assert result["age_hours"] is None


def test_fichier_absent(tmp_path):
    result = statusfile.collect({**ENTRY, "path": str(tmp_path / "nope.json")})
    assert result["level"] == "warn"
    assert result["status"] == "missing"


def test_json_illisible(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("pas du json")
    result = statusfile.collect({**ENTRY, "path": str(f)})
    assert result["level"] == "warn"
    assert result["status"] == "invalid"
