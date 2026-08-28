"""Le scribe du livre de bord : amorce silencieuse, une transition = un événement,
jamais de fantômes au restart."""
from pathlib import Path

import pytest

from homeport import events_watch
from homeport.collectors import events


@pytest.fixture(autouse=True)
def _fresh_state():
    events_watch.reset()
    yield
    events_watch.reset()


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    path = tmp_path / "t.db"
    events.init_db(path)
    return path


def kinds(db: Path) -> list[str]:
    return [e["kind"] for e in events.query(db, days=365, now=20_000)]


def test_services_amorce_silencieuse_puis_transition(db: Path):
    assert events_watch.services(db, {"gitea": "up"}, now=1000) == 0
    assert events_watch.services(db, {"gitea": "up"}, now=1060) == 0  # état stable
    assert events_watch.services(db, {"gitea": "down"}, now=1120) == 1
    assert events_watch.services(db, {"gitea": "down"}, now=1180) == 0  # pas de doublon
    assert events_watch.services(db, {"gitea": "up"}, now=1240) == 1
    assert kinds(db) == ["service.up", "service.down"]


def test_services_nouveau_service_et_unknown_ignores(db: Path):
    events_watch.services(db, {"gitea": "up"}, now=1000)
    # jellyfin apparaît dans la config : pas une transition vécue
    assert events_watch.services(db, {"gitea": "up", "jellyfin": "down"}, now=1060) == 0
    # passage par unknown (pas de donnée) : silencieux dans les deux sens
    assert events_watch.services(db, {"gitea": "unknown", "jellyfin": "down"}, now=1120) == 0
    assert events_watch.services(db, {"gitea": "up", "jellyfin": "down"}, now=1180) == 0


def test_wan_panne_puis_retour_avec_duree(db: Path):
    assert events_watch.wan(db, True, now=1000) == 0
    assert events_watch.wan(db, False, now=1300) == 1
    assert events_watch.wan(db, False, now=1360) == 0
    assert events_watch.wan(db, True, now=1540) == 1
    rows = events.query(db, days=365, now=20_000)
    assert [r["kind"] for r in rows] == ["internet.up", "internet.down"]
    assert rows[0]["detail"] == "4 min"


def test_wan_amorce_en_panne_donne_une_duree_au_retour(db: Path):
    assert events_watch.wan(db, False, now=1000) == 0  # amorce : silencieux
    assert events_watch.wan(db, True, now=1240) == 1
    rows = events.query(db, days=365, now=20_000)
    assert rows[0]["detail"] == "4 min"


def test_livebox_panne_puis_retour_avec_duree(db: Path):
    assert events_watch.livebox(db, True, now=1000) == 0  # amorce : silencieux
    assert events_watch.livebox(db, False, now=1300) == 1
    assert events_watch.livebox(db, False, now=1360) == 0
    assert events_watch.livebox(db, True, now=1540) == 1
    rows = events.query(db, days=365, now=20_000)
    assert [r["kind"] for r in rows] == ["livebox.up", "livebox.down"]
    assert rows[0]["detail"] == "4 min"


def test_public_ip_changement(db: Path):
    assert events_watch.public_ip(db, "203.0.113.42", now=1000) == 0
    assert events_watch.public_ip(db, "203.0.113.42", now=2000) == 0
    assert events_watch.public_ip(db, None, now=3000) == 0  # échec de mesure : silencieux
    assert events_watch.public_ip(db, "198.51.100.7", now=4000) == 1
    rows = events.query(db, days=365, now=20_000)
    assert rows[0]["kind"] == "ip.changed"
    assert rows[0]["detail"] == "203.0.113.42 → 198.51.100.7"


def test_backups_transitions(db: Path):
    # Sans champ `file` (ancien contrat) : seules les transitions d'état comptent.
    ok = [{"name": "config", "state": "ok"}]
    stale = [{"name": "config", "state": "warn"}]
    assert events_watch.backups(db, ok, now=1000) == 0
    assert events_watch.backups(db, stale, now=2000) == 1
    assert events_watch.backups(db, stale, now=3000) == 0
    assert events_watch.backups(db, ok, now=4000) == 1
    assert kinds(db) == ["backup.ok", "backup.stale"]


def test_backups_nouveau_fichier_journalise_chaque_reussite(db: Path):
    # Une sauvegarde saine reste « ok » : c'est l'apparition d'un NOUVEAU fichier qui prouve
    # qu'une sauvegarde a tourné, et qui doit apparaître au livre de bord.
    j1 = [{"name": "SSD", "state": "ok", "file": "cfg-20260823.tar.gz"}]
    j2 = [{"name": "SSD", "state": "ok", "file": "cfg-20260824.tar.gz"}]
    assert events_watch.backups(db, j1, now=1000) == 0  # amorce silencieuse
    assert events_watch.backups(db, j1, now=2000) == 0  # même fichier : rien
    assert events_watch.backups(db, j2, now=3000) == 1  # nouvelle sauvegarde
    rows = events.query(db, days=365, now=20_000)
    assert rows[0]["kind"] == "backup.ok"
    assert rows[0]["detail"] == "cfg-20260824.tar.gz"


def test_backups_nouveau_fichier_apres_stale_recupere_une_seule_fois(db: Path):
    warn = [{"name": "SSD", "state": "warn", "file": "old.tar.gz"}]
    ok_new = [{"name": "SSD", "state": "ok", "file": "new.tar.gz"}]
    assert events_watch.backups(db, warn, now=1000) == 0  # amorce
    assert events_watch.backups(db, ok_new, now=2000) == 1  # nouveau fichier + rétabli
    assert kinds(db) == ["backup.ok"]  # un seul événement, pas de doublon


def test_throttling_apparition_labels(db: Path):
    assert events_watch.throttling(db, {"now": []}, now=1000) == 0
    assert events_watch.throttling(db, {"now": ["Under-voltage detected"]}, now=2000) == 1
    assert events_watch.throttling(db, {"now": ["Under-voltage detected"]}, now=3000) == 0
    rows = events.query(db, days=365, now=20_000)
    assert rows[0]["kind"] == "power.undervoltage"


def test_temperature_hysteresis(db: Path):
    assert events_watch.temperature(db, 70.0, now=1000) == 0
    assert events_watch.temperature(db, 81.0, now=2000) == 1
    assert events_watch.temperature(db, 82.0, now=3000) == 0  # toujours chaud : désarmé
    assert events_watch.temperature(db, 78.0, now=4000) == 0  # pas encore ré-armé
    assert events_watch.temperature(db, 74.0, now=5000) == 0  # ré-arme
    assert events_watch.temperature(db, 80.5, now=6000) == 1
    assert kinds(db) == ["temp.high", "temp.high"]


def test_boot_selon_uptime(db: Path):
    assert events_watch.boot(db, uptime_seconds=3600) == 0  # restart du service, pas un boot
    assert events_watch.boot(db, uptime_seconds=42) == 1
    assert kinds(db) == ["boot"]


def test_boot_avec_uptime_inconnu_ne_leve_pas(db: Path):
    """Un uptime introuvable (macOS sans /proc) ne doit ni planter ni fabriquer un boot."""
    assert events_watch.boot(db, uptime_seconds=None) == 0
    assert kinds(db) == []


def test_devices_new(db: Path):
    n = events_watch.devices_new(db, [{"mac": "aa:bb:cc:dd:ee:ff", "ip": "192.168.1.50"}], now=1000)
    assert n == 1
    rows = events.query(db, days=365, now=20_000)
    assert rows[0]["subject"] == "aa:bb:cc:dd:ee:ff"
    assert rows[0]["detail"] == "192.168.1.50"
