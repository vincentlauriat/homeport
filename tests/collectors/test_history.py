from homeport.collectors import history

SAMPLE = {"cpu_pct": 12.5, "mem_pct": 40.0, "temp_c": 55.0, "nvme_temp_c": 38.0}


def test_record_inserts_a_sample_retrievable_by_query_range(tmp_path):
    db = tmp_path / "history.db"
    history.init_db(db)

    history.record(db, SAMPLE, now=1000.0)

    rows = history.query_range(db, hours=1, now=1000.0)
    assert rows == [{"ts": 1000, **SAMPLE}]


def test_query_range_excludes_samples_older_than_the_window(tmp_path):
    db = tmp_path / "history.db"
    history.init_db(db)
    history.record(db, {**SAMPLE, "cpu_pct": 1.0}, now=0.0)
    history.record(db, {**SAMPLE, "cpu_pct": 2.0}, now=7200.0)

    rows = history.query_range(db, hours=1, now=7200.0)

    assert [r["cpu_pct"] for r in rows] == [2.0]


def test_prune_deletes_samples_older_than_retention(tmp_path):
    db = tmp_path / "history.db"
    history.init_db(db)
    history.record(db, {**SAMPLE, "cpu_pct": 1.0}, now=0.0)
    history.record(db, {**SAMPLE, "cpu_pct": 2.0}, now=8 * 86400)

    deleted = history.prune(db, retention_days=7, now=8 * 86400)

    assert deleted == 1
    remaining = history.query_range(db, hours=24 * 30, now=8 * 86400)
    assert [r["cpu_pct"] for r in remaining] == [2.0]


def test_init_db_is_idempotent(tmp_path):
    db = tmp_path / "history.db"
    history.init_db(db)
    history.init_db(db)

    history.record(db, SAMPLE, now=0.0)

    assert len(history.query_range(db, hours=1, now=0.0)) == 1


def test_le_trace_garde_sa_densite_quand_la_cadence_augmente(tmp_path):
    """Le job écrit une fois par minute depuis que l'API v1 réclame une échelle 24 h @ 1 min.
    Sans décimation, la fenêtre 7 jours du front passerait de 2 016 à 10 080 points par requête."""
    db = tmp_path / "history.db"
    history.init_db(db)
    base = 1_700_000_000
    for i in range(60):  # une heure d'échantillons à la minute
        history.record(db, {"cpu_pct": float(i)}, now=base + i * 60)

    rows = history.query_range(db, hours=1, now=base + 3600)
    # La grille des tranches est absolue (`ts // pas`), pas relative à l'instant de la requête :
    # une tranche de bord est donc partielle. Ce qui doit tenir, c'est l'unicité par tranche.
    tranches = [row["ts"] // history.GRAPH_STEP_S for row in rows]
    assert len(tranches) == len(set(tranches)), "deux points dans la même tranche"
    assert len(rows) < 60 / 4, f"la décimation n'a pas eu lieu : {len(rows)} points pour 60 mesures"


def test_une_tranche_ne_rend_qu_une_ligne_meme_a_seconde_egale(tmp_path):
    """`ts` n'est pas unique : deux écritures peuvent tomber sur la même seconde. La requête
    s'appuie sur les « bare columns » de SQLite — ce test vérifie cette garantie plutôt que
    de la supposer."""
    db = tmp_path / "history.db"
    history.init_db(db)
    base = 1_700_000_000
    history.record(db, {"cpu_pct": 11.0}, now=base)
    history.record(db, {"cpu_pct": 22.0}, now=base)  # même seconde
    history.record(db, {"cpu_pct": 33.0}, now=base + 10)  # même tranche

    rows = history.query_range(db, hours=1, now=base + 600)
    assert len(rows) == 1
    assert rows[0]["ts"] == base
    assert rows[0]["cpu_pct"] == 11.0, "les colonnes nues suivent la ligne du MIN(ts)"


def test_la_decimation_ne_deplace_pas_les_instants(tmp_path):
    """Un point rendu doit être une mesure réelle, à son instant réel — pas un instant de grille
    reconstruit, qui décalerait la courbe par rapport aux événements du livre de bord."""
    db = tmp_path / "history.db"
    history.init_db(db)
    base = 1_700_000_000
    instants = [base + 137, base + 301, base + 899]
    for i, ts in enumerate(instants):
        history.record(db, {"cpu_pct": float(i)}, now=ts)

    rendus = [row["ts"] for row in history.query_range(db, hours=1, now=base + 1200)]
    assert set(rendus) <= set(instants), "aucun instant inventé"
