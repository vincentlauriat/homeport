"""La config d'exemple charge, et l'absence totale de config reste saine (spec §8)."""
from pathlib import Path

from homeport import config


def test_config_example_charge():
    example = Path(__file__).resolve().parent.parent / "config.example" / "services.yaml"
    groups = config.load_groups(example)
    assert groups and all(g.services for g in groups)
    health = config.load_health(example)
    assert health["intervals"]["wan"] > 0
    assert config.load_mqtt(example)["enabled"] is False
    # Aucune identité réelle dans l'exemple : les actions sont désactivées par défaut.
    assert config.load_actions(example)["admin"] is None


def test_sans_fichier_de_config_dashboard_vide_mais_sain(tmp_path):
    absent = tmp_path / "services.yaml"
    assert config.load_groups(absent) == []
    health = config.load_health(absent)
    assert health["backups"] == []
    assert health["intervals"] == config.DEFAULT_INTERVALS
    assert config.load_actions(absent)["admin"] is None
    assert config.load_mqtt(absent)["enabled"] is False


def test_disks_configurables(tmp_path):
    f = tmp_path / "services.yaml"
    f.write_text("health:\n  disks: [\"/\", \"/srv\"]\n")
    assert config.load_health(f)["disks"] == ["/", "/srv"]


def test_disks_defaut_racine_seule(tmp_path):
    assert config.load_health(tmp_path / "absent.yaml")["disks"] == ["/"]


def test_status_files_configurables(tmp_path):
    f = tmp_path / "services.yaml"
    f.write_text("health:\n  status_files:\n    - {id: offsite, name: Offsite, path: /tmp/x.json, warn_after_hours: 48}\n")
    files = config.load_health(f)["status_files"]
    assert files[0]["id"] == "offsite"
    assert config.load_health(tmp_path / "absent.yaml")["status_files"] == []
