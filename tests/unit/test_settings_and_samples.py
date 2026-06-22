import sqlite3

from orionfold.storage.db import apply_migrations
from orionfold.storage import settings


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    apply_migrations(conn)
    return conn


def test_sandbox_defaults_false_and_round_trips():
    conn = _db()
    assert settings.get_sandbox_enabled(conn) is False
    settings.set_sandbox_enabled(conn, True)
    assert settings.get_sandbox_enabled(conn) is True
    settings.set_sandbox_enabled(conn, False)
    assert settings.get_sandbox_enabled(conn) is False


def test_setting_get_default_and_set():
    conn = _db()
    assert settings.get_setting(conn, "missing", "fallback") == "fallback"
    settings.set_setting(conn, "k", "v")
    assert settings.get_setting(conn, "k") == "v"


def test_migrations_are_idempotent_and_add_is_sample():
    conn = _db()
    assert apply_migrations(conn) == 0  # re-apply adds nothing
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(datasets)")}
    assert "is_sample" in cols
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(runs)")}
    assert "is_sample" in cols


def test_seed_creates_flagged_sample_dataset_and_receipt():
    from orionfold.storage import repository
    from orionfold import sample_data

    conn = _db()
    repository.seed_datasets(conn)  # bundled (real) datasets exist
    datasets, receipts = sample_data.seed_sample_data(conn)
    assert (datasets, receipts) == (1, 1)
    rows = repository.list_dataset_rows(conn)
    samples = [d for d, meta in rows if meta.is_sample]
    assert [d.id for d in samples] == [sample_data.SAMPLE_DATASET_ID]
    run = conn.execute("SELECT id, is_sample FROM runs").fetchone()
    assert run["id"] == sample_data.SAMPLE_RUN_ID and run["is_sample"] == 1


def test_seed_is_idempotent():
    from orionfold.storage import repository
    from orionfold import sample_data

    conn = _db()
    repository.seed_datasets(conn)
    sample_data.seed_sample_data(conn)
    sample_data.seed_sample_data(conn)  # re-seed
    assert conn.execute("SELECT COUNT(*) c FROM runs WHERE is_sample=1").fetchone()["c"] == 1
    assert conn.execute("SELECT COUNT(*) c FROM datasets WHERE is_sample=1").fetchone()["c"] == 1


def test_remove_samples_keeps_real_data():
    from orionfold.storage import repository
    from orionfold import sample_data

    conn = _db()
    repository.seed_datasets(conn)
    real_before = conn.execute("SELECT COUNT(*) c FROM datasets WHERE is_sample=0").fetchone()["c"]
    sample_data.seed_sample_data(conn)
    ds, runs = repository.remove_sample_data(conn)
    assert ds == 1 and runs == 1
    assert conn.execute("SELECT COUNT(*) c FROM datasets WHERE is_sample=0").fetchone()["c"] == real_before
    assert conn.execute("SELECT COUNT(*) c FROM runs").fetchone()["c"] == 0


def test_clear_all_wipes_datasets_and_runs_but_not_settings():
    from orionfold.storage import repository
    from orionfold import sample_data

    conn = _db()
    repository.seed_datasets(conn)
    sample_data.seed_sample_data(conn)
    settings.set_sandbox_enabled(conn, True)
    ds, runs = repository.clear_all_data(conn)
    assert ds >= 1 and runs == 1
    assert conn.execute("SELECT COUNT(*) c FROM datasets").fetchone()["c"] == 0
    assert conn.execute("SELECT COUNT(*) c FROM runs").fetchone()["c"] == 0
    assert settings.get_sandbox_enabled(conn) is True  # settings preserved
