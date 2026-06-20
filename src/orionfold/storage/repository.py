"""Persistence operations over the SQLite connection — datasets and proof reports.

Reports are stored as validated JSON of the :class:`ProofReport` so the receipt and the API
always read back exactly what was run. Nothing here writes secrets; the report itself only
carries provider ids and the local/cloud boundary.
"""

from __future__ import annotations

import sqlite3

from orionfold.data import bundled_datasets
from orionfold.domain.models import Dataset, ProofReport


def seed_datasets(conn: sqlite3.Connection) -> None:
    """Insert bundled datasets if they are not present (idempotent)."""
    for dataset in bundled_datasets():
        conn.execute(
            "INSERT OR IGNORE INTO datasets (id, name, description, examples) "
            "VALUES (?, ?, ?, ?)",
            (
                dataset.id,
                dataset.name,
                dataset.description,
                _examples_json(dataset),
            ),
        )
    conn.commit()


def list_datasets(conn: sqlite3.Connection) -> list[Dataset]:
    rows = conn.execute(
        "SELECT id, name, description, examples FROM datasets ORDER BY name"
    ).fetchall()
    return [
        Dataset.model_validate(
            {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "examples": _load_examples(r["examples"]),
            }
        )
        for r in rows
    ]


def get_dataset(conn: sqlite3.Connection, dataset_id: str) -> Dataset | None:
    r = conn.execute(
        "SELECT id, name, description, examples FROM datasets WHERE id = ?", (dataset_id,)
    ).fetchone()
    if r is None:
        return None
    return Dataset.model_validate(
        {
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "examples": _load_examples(r["examples"]),
        }
    )


def save_report(conn: sqlite3.Connection, report: ProofReport) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO runs (id, created_at, config_hash, report) VALUES (?, ?, ?, ?)",
        (
            report.run.id,
            report.run.created_at,
            report.run.config_hash,
            report.model_dump_json(),
        ),
    )
    conn.commit()


def get_report(conn: sqlite3.Connection, run_id: str) -> ProofReport | None:
    r = conn.execute("SELECT report FROM runs WHERE id = ?", (run_id,)).fetchone()
    if r is None:
        return None
    return ProofReport.model_validate_json(r["report"])


def list_runs(conn: sqlite3.Connection) -> list[ProofReport]:
    """Most recent first. v0 keeps the full report inline — fine for single-user local use."""
    rows = conn.execute("SELECT report FROM runs ORDER BY created_at DESC").fetchall()
    return [ProofReport.model_validate_json(r["report"]) for r in rows]


def _examples_json(dataset: Dataset) -> str:
    import json

    return json.dumps([e.model_dump() for e in dataset.examples])


def _load_examples(raw: str) -> list[dict]:
    import json

    return json.loads(raw)
