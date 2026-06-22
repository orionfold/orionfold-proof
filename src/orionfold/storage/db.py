"""Local SQLite persistence (ADR-0001 §4, enforced by .claude/rules/storage.md).

One single-file database per install holds datasets, runs, and results. Migrations are
**append-only**: never edit a past migration, only append a new one. ``apply_migrations`` is
idempotent and records what it has run in ``schema_migrations``.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

# Append-only. Each entry runs once, in order, tracked by index in ``schema_migrations``.
# To change the schema, APPEND a new statement — never edit an existing one.
MIGRATIONS: list[str] = [
    """
    CREATE TABLE datasets (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        examples    TEXT NOT NULL          -- JSON array of {input_text, expected_text}
    );
    """,
    """
    CREATE TABLE runs (
        id          TEXT PRIMARY KEY,
        created_at  TEXT NOT NULL,
        config_hash TEXT NOT NULL,
        report      TEXT NOT NULL          -- JSON of the full ProofReport
    );
    """,
    """
    ALTER TABLE datasets ADD COLUMN is_sample INTEGER NOT NULL DEFAULT 0;
    """,
    """
    ALTER TABLE runs ADD COLUMN is_sample INTEGER NOT NULL DEFAULT 0;
    """,
    """
    CREATE TABLE settings (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """,
]


def default_db_path() -> Path:
    """Per-install database location; override with ``ORIONFOLD_DB`` (used by tests)."""
    override = os.environ.get("ORIONFOLD_DB")
    if override:
        return Path(override)
    return Path.home() / ".orionfold" / "proof.db"


def connect(path: Path | str) -> sqlite3.Connection:
    """Open (creating parent dirs as needed) a SQLite connection with row access by name.

    The store can hold confidential client dataset text, so on a real filesystem the
    directory and file are restricted to the owner (local-first privacy posture).
    """
    path = Path(path)
    is_memory = str(path) == ":memory:"
    if not is_memory:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    conn = sqlite3.connect(str(path))
    if not is_memory and path.exists():
        path.chmod(0o600)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def apply_migrations(conn: sqlite3.Connection) -> int:
    """Apply any not-yet-run migrations. Returns how many were applied this call."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " idx INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    applied = {row["idx"] for row in conn.execute("SELECT idx FROM schema_migrations")}
    count = 0
    for idx, statement in enumerate(MIGRATIONS):
        if idx in applied:
            continue
        conn.executescript(statement)
        conn.execute("INSERT INTO schema_migrations (idx) VALUES (?)", (idx,))
        count += 1
    conn.commit()
    return count
