"""Fichiers de déploiement macOS : syntaxe shell valide, plists bien formés, aucun chemin
personnel en dur (ce sont des gabarits substitués par install.sh, pas des fichiers instanciés).
`plutil -lint` (Apple, lecture seule) valide les plists sans rien installer sur la machine."""

import shutil
import subprocess
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parent.parent / "deploy" / "macos"

_PLUTIL_AVAILABLE = shutil.which("plutil") is not None


def test_install_sh_syntaxe():
    script = DEPLOY / "install.sh"
    assert script.exists()
    subprocess.run(["bash", "-n", str(script)], check=True)


def test_thermal_sh_syntaxe():
    script = DEPLOY / "homeport-thermal.sh"
    assert script.exists()
    subprocess.run(["bash", "-n", str(script)], check=True)


def test_thermal_sh_ne_lit_jamais_home():
    """Piège vérifié : un `LaunchDaemon` root a `$HOME=/var/root`, pas celui de l'utilisateur
    qui a installé Homeport. Le chemin de sortie doit toujours venir d'un argument explicite —
    seules les lignes de code comptent, le mot peut légitimement apparaître dans un commentaire
    qui explique le piège."""
    lines = (DEPLOY / "homeport-thermal.sh").read_text().splitlines()
    code_lines = [line for line in lines if not line.strip().startswith("#")]
    assert not any("$HOME" in line for line in code_lines)
    assert any("${1" in line for line in code_lines)  # l'argument, pas une valeur devinée


@pytest.mark.skipif(not _PLUTIL_AVAILABLE, reason="plutil indisponible (non-macOS)")
@pytest.mark.parametrize(
    "name",
    ["com.vincentlauriat.homeport.plist", "com.vincentlauriat.homeport.thermal.plist"],
)
def test_plist_est_valide(name):
    subprocess.run(["plutil", "-lint", str(DEPLOY / name)], check=True)


def test_plists_sont_des_gabarits_sans_chemin_personnel():
    """Ces fichiers sont versionnés et publics (dépôt GitHub) : aucun `/Users/<nom>` en dur,
    substitué par `install.sh` à l'installation — comme `sudoers.example` le fait déjà."""
    for name in ["com.vincentlauriat.homeport.plist", "com.vincentlauriat.homeport.thermal.plist"]:
        content = (DEPLOY / name).read_text()
        assert "/Users/" not in content
        assert "__" in content  # au moins un placeholder à substituer


def test_main_plist_porte_les_cles_attendues():
    content = (DEPLOY / "com.vincentlauriat.homeport.plist").read_text()
    assert "<key>Label</key>" in content
    assert "com.vincentlauriat.homeport</string>" in content
    assert "RunAtLoad" in content


def test_thermal_plist_reference_le_script_root():
    content = (DEPLOY / "com.vincentlauriat.homeport.thermal.plist").read_text()
    assert "homeport-thermal.sh" in content
    assert "StartInterval" in content
