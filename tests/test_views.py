"""Les trois vues v1.0 : /controle, /journal, /mur — coquilles rendues côté client."""
import pytest
from fastapi.testclient import TestClient

from homeport import main


@pytest.fixture()
def client():
    # Pas de lifespan : ni jobs de fond ni MQTT dans les tests.
    return TestClient(main.app)


@pytest.mark.parametrize(
    ("path", "marker"),
    [
        ("/controle", "v-ctrl"),
        ("/journal", "v-edit"),
        ("/mur", "v-wall"),
    ],
)
def test_vue_repond_avec_son_marqueur(client, path, marker):
    response = client.get(path)
    assert response.status_code == 200
    assert marker in response.text


def test_les_trois_vues_portent_le_selecteur(client):
    for path in ("/controle", "/journal", "/mur"):
        assert 'class="view-switch"' in client.get(path).text


# La nav partagée (_nav.html) : chaque page mène à toutes les autres — Vincent doit pouvoir
# revenir à l'accueil depuis /reseau ou /starlink, et y aller depuis n'importe où.
def test_toutes_les_pages_portent_la_nav_complete(client):
    for path in ("/controle", "/journal", "/mur", "/reseau", "/historique", "/starlink", "/livre-de-bord"):
        text = client.get(path).text
        assert 'class="view-switch"' in text, path
        for target in ('href="/"', 'href="/reseau"', 'href="/historique"', 'href="/livre-de-bord"'):
            assert target in text, (path, target)


def test_livre_de_bord_repond(client):
    response = client.get("/livre-de-bord")
    assert response.status_code == 200
    assert 'id="lb-days"' in response.text
    assert "livrebord.js" in response.text


def test_nav_starlink_seulement_si_module_actif(client, tmp_path, monkeypatch):
    # Config par défaut : module désactivé → pas d'entrée Starlink dans la nav.
    assert 'href="/starlink"' not in client.get("/reseau").text
    config = tmp_path / "services.yaml"
    config.write_text("starlink: {enabled: true}\n", encoding="utf-8")
    monkeypatch.setattr(main.cfg, "CONFIG_PATH", config)
    assert 'href="/starlink"' in client.get("/reseau").text
