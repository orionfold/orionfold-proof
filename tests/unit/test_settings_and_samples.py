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
