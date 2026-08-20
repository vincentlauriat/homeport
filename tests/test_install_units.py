"""Fichiers de déploiement : syntaxe shell valide, clés d'unité systemd obligatoires."""
import subprocess
from pathlib import Path

DEPLOY = Path(__file__).resolve().parent.parent / "deploy"


def test_install_sh_syntaxe():
    script = DEPLOY / "install.sh"
    assert script.exists()
    subprocess.run(["bash", "-n", str(script)], check=True)


def test_unite_principale():
    unit = (DEPLOY / "homeport.service").read_text()
    assert "User=homeport" in unit
    assert "ExecStart=" in unit
    assert "AmbientCapabilities=CAP_NET_BIND_SERVICE" in unit
    assert "WantedBy=multi-user.target" in unit
    # Aucune valeur d'instance : tout vient de /etc/homeport et des variables HOMEPORT_*.
    assert "/mnt/" not in unit


def test_unites_nvme_optionnelles():
    service = (DEPLOY / "nvme" / "homeport-nvme.service").read_text()
    timer = (DEPLOY / "nvme" / "homeport-nvme.timer").read_text()
    assert "homeport-nvme.sh" in service
    assert "OnCalendar=" in timer or "OnUnitActiveSec=" in timer
    subprocess.run(["bash", "-n", str(DEPLOY / "nvme" / "homeport-nvme.sh")], check=True)


def test_sudoers_exemple_sans_identite():
    sudoers = (DEPLOY / "sudoers.example").read_text()
    assert "NOPASSWD" in sudoers
    assert "homeport" in sudoers
