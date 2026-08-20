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
