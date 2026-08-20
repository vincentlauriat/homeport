from homeport import main
from homeport.main import _safe_init_history_db


def test_safe_init_history_db_returns_true_on_success(tmp_path):
    assert _safe_init_history_db(tmp_path / "history.db") is True


def test_safe_init_history_db_returns_false_without_crashing_when_parent_is_unwritable(tmp_path):
    # Un fichier là où un dossier est attendu : `mkdir(parents=True)` sur son enfant échoue.
    # Reproduit le cas réel visé — /mnt/ssd non monté après reboot — sans dépendre du montage.
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("")
    db_path = blocked / "history.db"

    assert _safe_init_history_db(db_path) is False


def _write_minimal_services(tmp_path):
    config = tmp_path / "services.yaml"
    config.write_text(
        "groups:\n"
        "  - name: Domotique\n"
        "    services:\n"
        "      - id: homeassistant\n"
        "        name: Home Assistant\n"
        "        docker: homeassistant\n"
    )
    return config


def test_known_container_accepts_a_declared_container(tmp_path, monkeypatch):
    monkeypatch.setattr(main.cfg, "CONFIG_PATH", _write_minimal_services(tmp_path))
    assert main._known_container("homeassistant") is True


def test_known_container_rejects_unknown_and_path_traversal_names(tmp_path, monkeypatch):
    monkeypatch.setattr(main.cfg, "CONFIG_PATH", _write_minimal_services(tmp_path))
    assert main._known_container("nope") is False
    # Le point d'entrée de la sécurité : un nom forgé ne doit jamais atteindre l'URL Docker.
    assert main._known_container("../../version") is False
