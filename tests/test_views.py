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
