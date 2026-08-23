"""Sélection de langue par navigateur : le cookie `homeport_lang` gagne quand il est
connu, sinon la config serveur — chacun sa langue, y compris la tablette murale."""
from fastapi.testclient import TestClient

from homeport import main


def client() -> TestClient:
    # Pas de lifespan : ni jobs de fond ni MQTT dans les tests.
    return TestClient(main.app)


def test_cookie_fr_rend_la_page_en_francais():
    http = client()
    http.cookies.set("homeport_lang", "fr")
    text = http.get("/livre-de-bord").text
    assert "Livre de bord" in text
    assert 'lang="fr"' in text


def test_cookie_zh_retire_est_ignore():
    # `zh` n'est plus offert : un cookie posé avant le retrait doit être ignoré comme
    # n'importe quelle langue inconnue, pas rendre une page à moitié traduite.
    http = client()
    http.cookies.set("homeport_lang", "zh")
    text = http.get("/livre-de-bord").text
    assert 'lang="zh"' not in text


def test_cookie_inconnu_ignore():
    http = client()
    http.cookies.set("homeport_lang", "klingon")
    text = http.get("/livre-de-bord").text
    assert 'lang="klingon"' not in text  # repli sur la config serveur


def test_selecteurs_presents_sur_toutes_les_pages():
    http = client()
    for path in ("/", "/controle", "/journal", "/mur", "/reseau", "/historique", "/starlink", "/livebox", "/livre-de-bord"):
        text = http.get(path).text
        assert 'id="pref-lang"' in text, path
        assert 'id="pref-theme"' in text, path
        assert "homeport_theme" in text, path  # script anti-flash dans le <head>
