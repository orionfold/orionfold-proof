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


def test_powermetrics_optin_defaults_false_and_round_trips():
    conn = _db()
    assert settings.get_powermetrics_optin(conn) is False
    settings.set_powermetrics_optin(conn, True)
    assert settings.get_powermetrics_optin(conn) is True
    settings.set_powermetrics_optin(conn, False)
    assert settings.get_powermetrics_optin(conn) is False


def test_threshold_defaults_fall_back_to_builtin_map():
    from orionfold.scoring.rubric import DEFAULT_THRESHOLDS

    conn = _db()
    got = settings.get_threshold_defaults(conn)
    assert got == {k: DEFAULT_THRESHOLDS[k] for k in ("similarity", "keypoint", "judge")}


def test_threshold_overrides_round_trip_and_clamp():
    conn = _db()
    settings.set_threshold_defaults(conn, {"similarity": 0.42, "judge": 1.5, "keypoint": -0.2})
    got = settings.get_threshold_defaults(conn)
    assert got["similarity"] == 0.42
    assert got["judge"] == 1.0  # clamped high
    assert got["keypoint"] == 0.0  # clamped low


def test_threshold_partial_override_keeps_builtin_for_untouched():
    from orionfold.scoring.rubric import DEFAULT_THRESHOLDS

    conn = _db()
    settings.set_threshold_defaults(conn, {"similarity": 0.6})
    got = settings.get_threshold_defaults(conn)
    assert got["similarity"] == 0.6
    assert got["keypoint"] == DEFAULT_THRESHOLDS["keypoint"]  # untouched


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


def test_seed_creates_flagged_sample_datasets_and_receipts():
    from orionfold.storage import repository
    from orionfold import sample_data

    conn = _db()
    repository.seed_datasets(conn)  # bundled (real) datasets exist
    n = len(sample_data._SAMPLES)
    datasets, receipts = sample_data.seed_sample_data(conn)
    assert (datasets, receipts) == (n, n)
    rows = repository.list_dataset_rows(conn)
    samples = {d.id: meta for d, meta in rows if meta.is_sample}
    assert set(samples) == {spec.sample_id for spec in sample_data._SAMPLES}
    runs = {r["id"]: r["is_sample"] for r in conn.execute("SELECT id, is_sample FROM runs")}
    assert runs == {spec.run_id: 1 for spec in sample_data._SAMPLES}
    # WS-F F1 / B3: each seeded sample carries the same display metadata a user dataset gets,
    # so its card reads with a full metadata line + hint chip (not a bare "N examples"). The
    # per-spec check_hint round-trips (drives both the chip and the seeded receipt's scoring).
    for spec in sample_data._SAMPLES:
        meta = samples[spec.sample_id]
        assert meta.created_at == sample_data.SAMPLE_CREATED_AT
        assert meta.source == sample_data.SAMPLE_SOURCE
        # An empty hint normalizes to None on read (no chip) — see _load_meta.
        assert meta.check_hint == (spec.check_hint or None)


def test_seed_is_idempotent():
    from orionfold.storage import repository
    from orionfold import sample_data

    conn = _db()
    repository.seed_datasets(conn)
    n = len(sample_data._SAMPLES)
    sample_data.seed_sample_data(conn)
    sample_data.seed_sample_data(conn)  # re-seed
    assert conn.execute("SELECT COUNT(*) c FROM runs WHERE is_sample=1").fetchone()["c"] == n
    assert conn.execute("SELECT COUNT(*) c FROM datasets WHERE is_sample=1").fetchone()["c"] == n


def test_remove_samples_keeps_real_data():
    from orionfold.storage import repository
    from orionfold import sample_data

    conn = _db()
    repository.seed_datasets(conn)
    n = len(sample_data._SAMPLES)
    real_before = conn.execute("SELECT COUNT(*) c FROM datasets WHERE is_sample=0").fetchone()["c"]
    sample_data.seed_sample_data(conn)
    ds, runs = repository.remove_sample_data(conn)
    assert ds == n and runs == n
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
    assert ds >= 1 and runs == len(sample_data._SAMPLES)
    assert conn.execute("SELECT COUNT(*) c FROM datasets").fetchone()["c"] == 0
    assert conn.execute("SELECT COUNT(*) c FROM runs").fetchone()["c"] == 0
    assert settings.get_sandbox_enabled(conn) is True  # settings preserved
