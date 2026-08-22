"""Sélection de langue par navigateur : le cookie `homeport_lang` gagne quand il est
connu, sinon la config serveur — chacun sa langue, y compris la tablette murale."""
from fastapi.testclient import TestClient

from homeport import main


def client() -> TestClient:
    # Pas de lifespan : ni jobs de fond ni MQTT dans les tests.
    return TestClient(main.app)


def test_cookie_zh_rend_la_page_en_chinois():
    http = client()
    http.cookies.set("homeport_lang", "zh")
    text = http.get("/livre-de-bord").text
    assert "航海日志" in text
    assert 'lang="zh"' in text


def test_cookie_inconnu_ignore():
    http = client()
    http.cookies.set("homeport_lang", "klingon")
    text = http.get("/livre-de-bord").text
    assert 'lang="klingon"' not in text  # repli sur la config serveur


def test_selecteurs_presents_sur_toutes_les_pages():
    http = client()
    for path in ("/", "/controle", "/journal", "/mur", "/reseau", "/historique", "/starlink", "/livre-de-bord"):
        text = http.get(path).text
        assert 'id="pref-lang"' in text, path
        assert 'id="pref-theme"' in text, path
        assert "homeport_theme" in text, path  # script anti-flash dans le <head>
