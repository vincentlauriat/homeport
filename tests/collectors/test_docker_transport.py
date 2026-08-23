"""Le transport Docker est configurable : socket UNIX en direct (défaut, dev local) ou
proxy TCP lecture seule sur loopback (production, chantier B de la roadmap)."""
from homeport.collectors import docker_api


def test_client_par_defaut_passe_par_le_socket_unix(monkeypatch):
    monkeypatch.setattr(docker_api, "DOCKER_HOST", "unix:///var/run/docker.sock")
    client = docker_api.open_client(timeout=5.0)
    try:
        # Le transport UDS impose la destination ; l'hôte de l'URL est décoratif.
        assert str(client.base_url) == "http://docker"
    finally:
        # AsyncClient : la fermeture est asynchrone, mais ici aucune connexion n'a été ouverte.
        import asyncio
        asyncio.run(client.aclose())


def test_client_tcp_vise_le_proxy_loopback(monkeypatch):
    monkeypatch.setattr(docker_api, "DOCKER_HOST", "tcp://127.0.0.1:2375")
    client = docker_api.open_client(timeout=5.0)
    try:
        assert str(client.base_url) == "http://127.0.0.1:2375"
    finally:
        import asyncio
        asyncio.run(client.aclose())
