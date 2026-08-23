

# --- vérification de nouvelle version (system de mise à jour, opt-out) ---

def test_parse_latest_release():
    from homeport.collectors import updates
    assert updates.parse_latest_release('{"tag_name": "v0.2.0"}') == "0.2.0"
    assert updates.parse_latest_release('{"message": "Not Found"}') is None
    assert updates.parse_latest_release('pas du json') is None


def test_update_summary():
    from homeport.collectors import updates
    assert updates.update_summary("0.1.0", "0.2.0") == {
        "current": "0.1.0", "latest": "0.2.0", "available": True,
    }
    assert updates.update_summary("0.2.0", "0.2.0")["available"] is False
    assert updates.update_summary("0.1.0", None) == {
        "current": "0.1.0", "latest": None, "available": False,
    }


# --- fraîcheur des images Docker : le refus du proxy ne doit pas passer pour une vérité ---

class _FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class _FakeDocker:
    """Docker vu à travers un socket-proxy qui n'expose que `CONTAINERS: 1` : les conteneurs
    se listent, `/images/…` est refusé par un 403 — un vrai code HTTP, pas une exception."""

    def __init__(self, images_status):
        self.images_status = images_status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, path, **kwargs):
        if path == "/containers/json":
            return _FakeResponse(200, [{"Image": "eclipse-mosquitto:latest"}])
        if path.startswith("/images/"):
            return _FakeResponse(self.images_status, {"RepoDigests": []})
        raise AssertionError(f"chemin inattendu : {path}")


def test_images_refusees_par_le_proxy_ne_passent_pas_pour_locales(monkeypatch):
    """Sans distinction, un 403 laisse `RepoDigests` vide et l'image est classée « locale » :
    la vue annoncerait un contrôle de fraîcheur qui n'a jamais eu lieu. Le produit préfère
    déclarer la fonctionnalité indisponible plutôt que rendre une liste fausse."""
    import asyncio

    from homeport.collectors import updates

    monkeypatch.setattr(updates.docker_api, "open_client", lambda timeout: _FakeDocker(403))
    result = asyncio.run(updates.docker_images())

    assert result["available"] is False
    assert result["images"] == []
    assert result["checked"] == 0


def test_images_lisibles_sans_digest_restent_locales(monkeypatch):
    """Le cas légitime : une image construite sur place n'a pas de `RepoDigests`. Elle doit
    rester « locale », et la fonctionnalité disponible."""
    import asyncio

    from homeport.collectors import updates

    monkeypatch.setattr(updates.docker_api, "open_client", lambda timeout: _FakeDocker(200))
    result = asyncio.run(updates.docker_images())

    assert result["available"] is True
    assert [i["state"] for i in result["images"]] == ["local"]
