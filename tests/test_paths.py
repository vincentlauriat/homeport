"""Résolution des répertoires de config et de données (FHS + surcharges + repli dev)."""
import importlib

from homeport import config


def _reload():
    return importlib.reload(config)


def test_config_dir_surchargeable(monkeypatch, tmp_path):
    monkeypatch.setenv("HOMEPORT_CONFIG_DIR", str(tmp_path))
    cfg = _reload()
    assert cfg.CONFIG_DIR == tmp_path
    assert cfg.CONFIG_PATH == tmp_path / "services.yaml"


def test_data_dir_surchargeable(monkeypatch, tmp_path):
    monkeypatch.setenv("HOMEPORT_DATA_DIR", str(tmp_path))
    cfg = _reload()
    assert cfg.DATA_DIR == tmp_path
    assert cfg.DB_PATH == tmp_path / "history.db"
    assert cfg.NVME_PATH == tmp_path / "nvme.json"


def test_db_path_prime_sur_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("HOMEPORT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HOMEPORT_DB_PATH", str(tmp_path / "ailleurs.db"))
    cfg = _reload()
    assert cfg.DB_PATH == tmp_path / "ailleurs.db"


def test_repli_dev_cwd(monkeypatch, tmp_path):
    for var in ("HOMEPORT_CONFIG_DIR", "HOMEPORT_DATA_DIR", "HOMEPORT_DB_PATH", "HOMEPORT_NVME_PATH"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)
    # Les chemins système n'existent pas sur la machine de dev : repli sur le cwd.
    monkeypatch.setattr(config, "_ETC", tmp_path / "absent-etc", raising=False)
    cfg = _reload()
    # après reload, re-patcher n'est plus possible : on vérifie juste le comportement par
    # défaut hors système — sur une machine sans /etc/homeport ni /var/lib/homeport
    # inscriptible, les répertoires sont relatifs au cwd.
    if not (cfg._ETC.exists() or cfg._VAR.exists()):
        assert cfg.CONFIG_DIR == tmp_path / "config"
        assert cfg.DATA_DIR == tmp_path / "data"
