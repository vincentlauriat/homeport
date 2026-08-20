"""Les vues rendent dans la langue configurée — EN par défaut, FR fourni."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from homeport import main


def _client(monkeypatch, lang):
    monkeypatch.setenv("HOMEPORT_LANG", lang)
    monkeypatch.setattr(main, "DEMO", True)
    return TestClient(main.app)


@pytest.mark.parametrize("path", ["/", "/controle", "/journal", "/mur", "/reseau", "/historique"])
def test_pages_en_sans_francais(monkeypatch, path):
    html = _client(monkeypatch, "en").get(path).text
    for mot in ("Mémoire", "Sauvegarde", "actualisé", "chargement", "cœurs", "Appareils"):
        assert mot not in html, f"{mot!r} dans {path} en anglais"
    assert 'lang="en"' in html


@pytest.mark.parametrize("path", ["/", "/controle", "/journal", "/mur"])
def test_pages_fr(monkeypatch, path):
    html = _client(monkeypatch, "fr").get(path).text
    assert 'lang="fr"' in html
    assert "HOMEPORT_I18N" in html


def test_catalogue_serialise_dans_la_page(monkeypatch):
    html = _client(monkeypatch, "fr").get("/controle").text
    assert "Tout va bien." in html  # le catalogue FR embarqué pour le JS


ACCENT = re.compile(r"[éèêàçùœÉÈÀ]")
STATIC = Path(__file__).resolve().parent.parent / "homeport" / "static"
TEMPLATES = Path(__file__).resolve().parent.parent / "homeport" / "templates"


def test_plus_de_francais_en_dur_dans_les_sources():
    """Garde-fou : plus aucune chaîne accentuée hors catalogues dans les JS et templates."""
    offenders = []
    for f in list(STATIC.glob("*.js")) + list(TEMPLATES.glob("*.html")):
        for i, line in enumerate(f.read_text().split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith(("//", "*", "/*", "#", "{#")):
                continue  # les commentaires du code restent en français
            stripped = re.sub(r"//.*$", "", stripped)  # commentaire en fin de ligne
            if ACCENT.search(stripped):
                offenders.append(f"{f.name}:{i}")
    assert not offenders, offenders
