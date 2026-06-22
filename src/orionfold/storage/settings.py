"""Tiny key-value settings store (one row per setting). Local, per-install.

Booleans are stored as the strings "true"/"false". The only key today is
``sandbox_enabled`` (default off) — it gates the simulated Mock provider in the picker.
"""

from __future__ import annotations

import sqlite3

_SANDBOX_KEY = "sandbox_enabled"


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row is not None else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()


def get_sandbox_enabled(conn: sqlite3.Connection) -> bool:
    return get_setting(conn, _SANDBOX_KEY, "false") == "true"


def set_sandbox_enabled(conn: sqlite3.Connection, enabled: bool) -> None:
    set_setting(conn, _SANDBOX_KEY, "true" if enabled else "false")
