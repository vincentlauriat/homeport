"""L'API v1 : la poignée de main, le curseur d'événements et les métriques agrégées.

Ces tests portent sur les promesses que le contrat inter-dépôts fait à hpm — celles qu'un client
écrit en face suppose vraies. Voir `docs/api/homeport-api-v1.md` dans HomePortManager.
"""
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from homeport import actions, main
from homeport.collectors import events, identity, metrics


@pytest.fixture()
def client(tmp_path: Path, monkeypatch):
    db = tmp_path / "history.db"
    events.init_db(db)
    actions.init_db(db)
    identity.init_db(db)
    metrics.init_db(db)
    monkeypatch.setattr(main.cfg, "DB_PATH", db)
    return TestClient(main.app), db


# — capabilities ———————————————————————————————————————————————————————————————

def test_capabilities_annonce_le_contrat_et_les_surfaces(client):
    http, _ = client
    data = http.get("/api/v1/capabilities").json()

    assert data["contract"] == "1.0.0"
    assert data["features"] == ["events", "metrics"]
    assert data["epoch"]
    assert data["server"]


def test_capabilities_rend_un_epoch_stable(client):
    http, _ = client
    premier = http.get("/api/v1/capabilities").json()["epoch"]
    assert http.get("/api/v1/capabilities").json()["epoch"] == premier


def test_healthz_reste_independant_de_capabilities(client):
    """Les fusionner casserait le diagnostic interrogé par SSH."""
    http, _ = client
    sante = http.get("/healthz").json()
    assert set(sante) == {"status", "version"}
    assert "epoch" not in sante and "contract" not in sante


# — events ————————————————————————————————————————————————————————————————————

def test_evenements_servis_du_plus_ancien_au_plus_recent(client):
    """Un curseur avance : l'ordre décroissant de la route non versionnée ne conviendrait pas."""
    http, db = client
    now = time.time()
    for i in range(3):
        events.record(db, "service.down", "down", f"svc{i}", now=now - 10 + i)

    data = http.get("/api/v1/events").json()
    ids = [e["id"] for e in data["events"]]
    assert ids == sorted(ids)


def test_le_curseur_ne_rend_que_les_evenements_suivants(client):
    http, db = client
    for i in range(3):
        events.record(db, "boot", "warn", f"s{i}")

    tous = http.get("/api/v1/events").json()["events"]
    suite = http.get(f"/api/v1/events?since_id={tous[0]['id']}").json()["events"]
    assert [e["id"] for e in suite] == [e["id"] for e in tous[1:]]


def test_latest_id_ignore_le_filtre_et_la_limite(client):
    """C'est le garde-fou du contrat : il doit décrire la base, pas la page servie."""
    http, db = client
    for i in range(5):
        events.record(db, "backup.ok", "up", f"s{i}")

    data = http.get("/api/v1/events?limit=1&severity=critical").json()
    assert data["events"] == []
    assert data["latest_id"] == 5


def test_has_more_est_exact_meme_sous_filtre(client):
    http, db = client
    events.record(db, "service.down", "down", "a")
    for i in range(3):
        events.record(db, "backup.ok", "up", f"s{i}")

    # Un seul événement critical : la page n'est pas pleine, rien ne suit.
    data = http.get("/api/v1/events?severity=critical&limit=10").json()
    assert len(data["events"]) == 1
    assert data["has_more"] is False

    data = http.get("/api/v1/events?limit=2").json()
    assert data["has_more"] is True


def test_severites_normalisees_vers_le_vocabulaire_v1(client):
    http, db = client
    events.record(db, "service.up", "up", "a")
    events.record(db, "temp.high", "warn", "cpu")
    events.record(db, "service.down", "down", "a")

    severites = [e["severity"] for e in http.get("/api/v1/events").json()["events"]]
    assert severites == ["info", "warning", "critical"]


def test_severite_interne_inconnue_devient_warning(client):
    """La rabattre sur info la rendrait invisible ; sur critical elle réveillerait pour rien."""
    http, db = client
    events.record(db, "chose.inedite", "inconnue", "x")
    assert http.get("/api/v1/events").json()["events"][0]["severity"] == "warning"


def test_un_epoch_perime_repart_du_debut_sans_erreur(client):
    http, db = client
    for i in range(3):
        events.record(db, "boot", "warn", f"s{i}")

    reponse = http.get("/api/v1/events?since_id=2&since_epoch=unepochquinexistepas")
    assert reponse.status_code == 200
    data = reponse.json()
    assert [e["id"] for e in data["events"]] == [1, 2, 3], "le since_id doit être ignoré"
    assert data["epoch"] != "unepochquinexistepas"


def test_limite_hors_bornes_ramenee_sans_erreur(client):
    http, db = client
    for i in range(5):
        events.record(db, "boot", "warn", f"s{i}")

    assert http.get("/api/v1/events?limit=99999").status_code == 200
    assert len(http.get("/api/v1/events?limit=0").json()["events"]) == 1


def test_parametre_numerique_illisible_retombe_sur_le_defaut(client):
    """Le contrat exige une réponse servie, pas le 422 que la validation automatique produirait."""
    http, db = client
    events.record(db, "boot", "warn", "s")

    reponse = http.get("/api/v1/events?limit=abc&since_id=xyz")
    assert reponse.status_code == 200
    assert len(reponse.json()["events"]) == 1


def test_filtre_de_severite_inconnu_est_ignore(client):
    http, db = client
    events.record(db, "boot", "warn", "s")
    data = http.get("/api/v1/events?severity=bogus").json()
    assert len(data["events"]) == 1


def test_les_actions_admin_ne_sont_pas_fusionnees(client):
    """Elles ont leur propre séquence d'identifiants : les mêler casserait le curseur."""
    http, db = client
    actions.record(db, "vincent@tailnet", "restart", "gitea", True)
    events.record(db, "service.up", "up", "gitea")

    kinds = [e["kind"] for e in http.get("/api/v1/events").json()["events"]]
    assert kinds == ["service.up"]
    # La route non versionnée, elle, continue de les fusionner.
    assert any(k.startswith("action.") for k in
               [e["kind"] for e in http.get("/api/events?days=1").json()["events"]])


# — metrics ———————————————————————————————————————————————————————————————————

@pytest.mark.parametrize("scale,step,count", [("24h", 60, 1440), ("7d", 300, 2016),
                                              ("30d", 3600, 720), ("1y", 86400, 365)])
def test_chaque_plage_sert_son_echelle(client, scale, step, count):
    http, _ = client
    data = http.get(f"/api/v1/metrics?range={scale}").json()

    assert data["range"] == scale
    assert data["step_s"] == step
    assert (data["to"] - data["from"]) == count * step
    for name in ("cpu_pct", "mem_pct", "disk_pct", "temp_c"):
        assert len(data["series"][name]) == count, name


def test_une_plage_inconnue_est_le_seul_400(client):
    http, _ = client
    reponse = http.get("/api/v1/metrics?range=42x")
    assert reponse.status_code == 400
    assert "42x" in reponse.json()["error"]


def test_les_bornes_sont_alignees_sur_le_pas(client):
    http, _ = client
    data = http.get("/api/v1/metrics?range=7d").json()
    assert data["from"] % data["step_s"] == 0
    assert data["to"] % data["step_s"] == 0


def test_une_mesure_apparait_dans_la_serie(client):
    http, db = client
    now = time.time() - 120
    metrics.record(db, {"cpu_pct": 33.0, "disk_pct": 67.0}, now=now)

    data = http.get("/api/v1/metrics?range=24h").json()
    assert 33.0 in [v for v in data["series"]["cpu_pct"] if v is not None]
    assert 67.0 in [v for v in data["series"]["disk_pct"] if v is not None]
    # Les séries jamais alimentées restent entièrement vides, pas absentes.
    assert set(data["series"]["temp_c"]) == {None}


def test_metrics_porte_le_meme_epoch_que_events(client):
    http, _ = client
    assert (http.get("/api/v1/metrics").json()["epoch"]
            == http.get("/api/v1/events").json()["epoch"])


# — dégradation ————————————————————————————————————————————————————————————————

def test_base_inaccessible_repond_503_pas_une_trace(client, monkeypatch):
    http, _ = client
    monkeypatch.setattr(main.cfg, "DB_PATH", Path("/nonexistent/nope.db"))
    for route in ("/api/v1/capabilities", "/api/v1/events", "/api/v1/metrics"):
        reponse = http.get(route)
        assert reponse.status_code == 503, route
        assert "error" in reponse.json(), route


def test_toute_surface_annoncee_repond(client):
    """§8 du contrat : annoncer une surface qui répond 404 est une faute serveur. La liste étant
    dérivée des routes montées, ce test échouerait si la dérivation se remettait à mentir."""
    http, _ = client
    for nom in http.get("/api/v1/capabilities").json()["features"]:
        assert http.get(f"/api/v1/{nom}").status_code != 404, nom


def test_aucune_route_v1_servie_n_est_tue(client):
    """L'autre sens : une route ajoutée sans être annoncée resterait invisible au client."""
    http, _ = client
    annoncees = set(http.get("/api/v1/capabilities").json()["features"])
    montees = {
        route.path[len("/api/v1/"):]
        for route in main.app.routes
        if getattr(route, "path", "").startswith("/api/v1/")
    } - {"capabilities"}
    assert annoncees == montees


def test_la_version_de_contrat_est_un_semver_strict(client):
    """hpm refuse une version qu'il ne sait pas lire, et n'accepte ni pré-version ni zéro initial.
    Servir « 1.0 » ou « 01.0.0 » ferait échouer la poignée de main côté client."""
    http, _ = client
    contrat = http.get("/api/v1/capabilities").json()["contract"]
    morceaux = contrat.split(".")
    assert len(morceaux) == 3, contrat
    for morceau in morceaux:
        assert morceau.isdigit(), contrat
        assert morceau == "0" or not morceau.startswith("0"), contrat
    assert int(morceaux[0]) >= 1, "la plage consommée par hpm commence à 1.0.0"
