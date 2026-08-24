"""Les quatre échelles de l'API v1 : grille régulière, trous explicites, stockage borné."""
from pathlib import Path

import pytest

from homeport.collectors import metrics


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    path = tmp_path / "history.db"
    metrics.init_db(path)
    return path


def test_les_quatre_echelles_ont_la_longueur_annoncee(db: Path):
    """Le contrat annonce 1440 / 2016 / 720 / 365 points : la grille doit les produire."""
    attendu = {"24h": 1440, "7d": 2016, "30d": 720, "1y": 365}
    for scale, count in attendu.items():
        data = metrics.series(db, scale, now=1_700_000_000)
        assert len(data["series"]["cpu_pct"]) == count, scale
        assert (data["to"] - data["from"]) == count * data["step_s"], scale


def test_toutes_les_series_ont_la_meme_longueur(db: Path):
    data = metrics.series(db, "24h", now=1_700_000_000)
    longueurs = {name: len(values) for name, values in data["series"].items()}
    assert len(set(longueurs.values())) == 1, longueurs
    assert set(data["series"]) == set(metrics.SERIES)


def test_les_bornes_sont_alignees_sur_le_pas(db: Path):
    """Sans alignement, `from + i * step_s` ne retomberait pas sur les instants réels."""
    data = metrics.series(db, "7d", now=1_700_000_123.7)
    assert data["from"] % data["step_s"] == 0
    assert data["to"] % data["step_s"] == 0


def test_un_echantillon_atterrit_dans_son_seau(db: Path):
    now = 1_700_000_000
    metrics.record(db, {"cpu_pct": 12.0, "mem_pct": 40.0, "disk_pct": 67.0, "temp_c": 48.0}, now=now)

    data = metrics.series(db, "24h", now=now + 120)
    index = (metrics._bucket(now, 60) - data["from"]) // 60
    assert data["series"]["cpu_pct"][index] == 12.0
    assert data["series"]["temp_c"][index] == 48.0


def test_plusieurs_echantillons_dans_un_seau_sont_moyennes(db: Path):
    now = 1_700_000_000
    for value in (10.0, 20.0, 30.0):
        metrics.record(db, {"cpu_pct": value}, now=now)

    data = metrics.series(db, "24h", now=now + 120)
    index = (metrics._bucket(now, 60) - data["from"]) // 60
    assert data["series"]["cpu_pct"][index] == 20.0


def test_une_serie_absente_reste_vide_sans_devenir_zero(db: Path):
    """Un Pi sans capteur thermique doit servir trois séries pleines et une série vide —
    pas quatre séries dont une à zéro, qui se lirait comme une mesure."""
    now = 1_700_000_000
    metrics.record(db, {"cpu_pct": 12.0, "temp_c": None}, now=now)

    data = metrics.series(db, "24h", now=now + 120)
    index = (metrics._bucket(now, 60) - data["from"]) // 60
    assert data["series"]["cpu_pct"][index] == 12.0
    assert data["series"]["temp_c"][index] is None


def test_les_seaux_sans_mesure_sont_none(db: Path):
    now = 1_700_000_000
    metrics.record(db, {"cpu_pct": 12.0}, now=now)
    data = metrics.series(db, "24h", now=now + 3600)
    assert data["series"]["cpu_pct"].count(None) == len(data["series"]["cpu_pct"]) - 1


def test_le_seau_courant_est_exclu(db: Path):
    """Il se remplit encore : l'inclure ferait osciller sa valeur d'un appel à l'autre."""
    now = 1_700_000_030
    seau_courant = metrics._bucket(now, 60)  # 1_700_000_000 n'est pas un multiple de 60
    metrics.record(db, {"cpu_pct": 99.0}, now=now)
    data = metrics.series(db, "24h", now=now)
    assert data["to"] == seau_courant, "la fenêtre s'arrête au seau en cours, qui reste exclu"
    assert 99.0 not in [v for v in data["series"]["cpu_pct"] if v is not None]


def test_prune_borne_le_stockage(db: Path):
    now = 1_700_000_000
    metrics.record(db, {"cpu_pct": 1.0}, now=now - 2 * 365 * 86400)  # deux ans en arrière
    metrics.record(db, {"cpu_pct": 2.0}, now=now)
    metrics.prune(db, now=now)

    import sqlite3
    with sqlite3.connect(db) as conn:
        restant = conn.execute("SELECT COUNT(*) FROM metric_rollups").fetchone()[0]
    # Un seul instant survit, dans les quatre échelles.
    assert restant == len(metrics.SCALES)


def test_un_echantillon_alimente_les_quatre_echelles(db: Path):
    now = 1_700_000_000
    metrics.record(db, {"cpu_pct": 42.0}, now=now)
    for scale in metrics.SCALES:
        data = metrics.series(db, scale, now=now + metrics.SCALES[scale][0] * 2)
        assert 42.0 in [v for v in data["series"]["cpu_pct"] if v is not None], scale
