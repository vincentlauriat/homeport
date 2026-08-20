"""État de la sauvegarde hors machine — lu depuis le JSON écrit par homeport-restic.sh (root),
même motif que nvme.json : le service web ne lance jamais restic lui-même."""
import json
from pathlib import Path

from homeport.collectors import offsite


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "restic.json"
    path.write_text(json.dumps(payload))
    return path


def test_collect_snapshot_ok(tmp_path: Path):
    path = _write(tmp_path, {
        "status": "ok", "message": "sauvegarde poussée",
        "last_snapshot_ts": 1_000_000, "snapshots": 12, "checked_ts": 1_000_100,
        "verified_ts": 900_000, "verified_ok": True,
    })
    data = offsite.collect(path, now=1_000_000 + 7200)
    assert data["status"] == "ok"
    assert data["age_hours"] == 2.0
    assert data["snapshots"] == 12
    assert data["verified_ok"] is True


def test_collect_pending_sans_snapshot(tmp_path: Path):
    path = _write(tmp_path, {
        "status": "pending", "message": "dépôt pas encore initialisé",
        "last_snapshot_ts": None, "snapshots": None, "checked_ts": 1_000_000,
    })
    data = offsite.collect(path)
    assert data["status"] == "pending"
    assert data["age_hours"] is None
    assert data["verified_ok"] is None


def test_collect_fichier_absent(tmp_path: Path):
    assert offsite.collect(tmp_path / "nope.json") is None


def test_collect_json_corrompu(tmp_path: Path):
    path = tmp_path / "restic.json"
    path.write_text("{pas du json")
    assert offsite.collect(path) is None
