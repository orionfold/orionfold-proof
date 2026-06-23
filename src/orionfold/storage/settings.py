"""Tiny key-value settings store (one row per setting). Local, per-install.

Booleans are stored as the strings "true"/"false"; thresholds as their float repr. Keys today:
``sandbox_enabled`` (default off — gates the simulated Mock provider), and per-kind scoring
threshold overrides ``threshold_<kind>`` (default *unset* → the built-in DEFAULT_THRESHOLDS map).
"""

from __future__ import annotations

import sqlite3

from orionfold.scoring.rubric import DEFAULT_THRESHOLDS

_SANDBOX_KEY = "sandbox_enabled"
# Only these kinds expose a tunable default-threshold slider in Settings.
_THRESHOLD_KINDS = ("similarity", "keypoint", "judge")
_THRESHOLD_KEY = "threshold_{kind}"


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


def get_threshold_defaults(conn: sqlite3.Connection) -> dict[str, float]:
    """Resolved per-kind default thresholds: a persisted override per kind, else the built-in map.

    Always returns every tunable kind so the UI can render a slider for each without a second
    fallback. Out-of-range or corrupt stored values are ignored in favor of the built-in default.
    """
    out: dict[str, float] = {}
    for kind in _THRESHOLD_KINDS:
        builtin = DEFAULT_THRESHOLDS[kind]
        raw = get_setting(conn, _THRESHOLD_KEY.format(kind=kind))
        if raw is None:
            out[kind] = builtin
            continue
        try:
            value = float(raw)
        except ValueError:
            value = builtin
        out[kind] = value if 0.0 <= value <= 1.0 else builtin
    return out


def set_threshold_defaults(conn: sqlite3.Connection, thresholds: dict[str, float]) -> None:
    """Persist per-kind threshold overrides. Unknown kinds are ignored; values are clamped to 0..1."""
    for kind in _THRESHOLD_KINDS:
        if kind not in thresholds:
            continue
        value = min(1.0, max(0.0, float(thresholds[kind])))
        set_setting(conn, _THRESHOLD_KEY.format(kind=kind), repr(value))
