"""Actions authentifiées par identité Tailscale : l'identité vient du réseau (tailscale whois
sur l'IP source), jamais d'un login. Le LAN reste strictement lecture seule."""
import asyncio
import json
from pathlib import Path

from homeport import actions


# --- Qui a le droit ---------------------------------------------------------------------

def test_is_tailnet_ip():
    assert actions.is_tailnet_ip("100.102.102.102") is True     # CGNAT 100.64.0.0/10
    assert actions.is_tailnet_ip("100.63.255.255") is False    # juste sous la plage
    assert actions.is_tailnet_ip("192.168.68.44") is False     # LAN
    assert actions.is_tailnet_ip("127.0.0.1") is False
    assert actions.is_tailnet_ip("pas-une-ip") is False


def test_parse_whois_login():
    raw = json.dumps({"Node": {"Name": "mba13m5."}, "UserProfile": {"LoginName": "admin@example.com"}})
    assert actions.parse_whois_login(raw) == "admin@example.com"
    assert actions.parse_whois_login("{}") is None
    assert actions.parse_whois_login("pas du json") is None


def test_authorize_refuse_hors_tailnet(monkeypatch):
    called = []

    async def fake_run(*args, **kwargs):
        called.append(args)
        return b"{}"

    monkeypatch.setattr(actions._process, "run", fake_run)
    assert asyncio.run(actions.authorize("192.168.68.44", "admin@example.com")) is False
    assert called == []      # whois n'est même pas consulté pour une IP hors tailnet


def test_authorize_verifie_l_identite(monkeypatch):
    async def fake_run(*args, **kwargs):
        return json.dumps({"UserProfile": {"LoginName": "admin@example.com"}}).encode()

    monkeypatch.setattr(actions._process, "run", fake_run)
    assert asyncio.run(actions.authorize("100.102.102.102", "admin@example.com")) is True
    assert asyncio.run(actions.authorize("100.102.102.102", "intrus@example.com")) is False


# --- Journal des actions ----------------------------------------------------------------

def test_journal_enregistre_et_relit(tmp_path: Path):
    db = tmp_path / "t.db"
    actions.init_db(db)
    actions.record(db, "admin@example.com", "restart", "homeassistant", True, now=1000)
    actions.record(db, "admin@example.com", "wake", "aa:bb:cc:dd:ee:ff", False, now=2000)
    rows = actions.recent(db, limit=10)
    assert len(rows) == 2
    assert rows[0]["target"] == "aa:bb:cc:dd:ee:ff"   # plus récent d'abord
    assert rows[0]["ok"] == 0
    assert rows[1]["kind"] == "restart"


# --- Configuration ----------------------------------------------------------------------

def test_service_restartable_et_admin(tmp_path: Path):
    from homeport import config as cfg
    yaml_file = tmp_path / "services.yaml"
    yaml_file.write_text(
        "actions:\n  admin: admin@example.com\n"
        "groups:\n  - name: G\n    services:\n"
        "      - {id: ha, name: HA, docker: homeassistant, restartable: true}\n"
        "      - {id: mq, name: MQ, docker: mosquitto}\n"
    )
    groups = cfg.load_groups(yaml_file)
    services = {s.id: s for s in cfg.all_services(groups)}
    assert services["ha"].restartable is True
    assert services["mq"].restartable is False          # défaut : rien n'est redémarrable
    assert cfg.load_actions(yaml_file) == {"admin": "admin@example.com"}


def test_load_actions_sans_section(tmp_path: Path):
    from homeport import config as cfg
    yaml_file = tmp_path / "services.yaml"
    yaml_file.write_text("groups: []\n")
    assert cfg.load_actions(yaml_file) == {"admin": None}
