"""Persistence operations over the SQLite connection — datasets and proof reports.

Reports are stored as validated JSON of the :class:`ProofReport` so the receipt and the API
always read back exactly what was run. Nothing here writes secrets; the report itself only
carries provider ids and the local/cloud boundary.
"""

from __future__ import annotations

import re
import sqlite3

from orionfold.data import bundled_datasets
from orionfold.domain.models import Dataset, Example, ProofReport


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


def save_report(conn: sqlite3.Connection, report: ProofReport, *, is_sample: bool = False) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO runs (id, created_at, config_hash, report, is_sample) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            report.run.id,
            report.run.created_at,
            report.run.config_hash,
            report.model_dump_json(),
            1 if is_sample else 0,
        ),
    )
    conn.commit()


def insert_sample_dataset(conn: sqlite3.Connection, dataset: Dataset) -> None:
    """Upsert a sample dataset (is_sample=1). Stable id makes re-seeding idempotent."""
    conn.execute(
        "INSERT OR REPLACE INTO datasets (id, name, description, examples, is_sample) "
        "VALUES (?, ?, ?, ?, 1)",
        (dataset.id, dataset.name, dataset.description, _examples_json(dataset)),
    )
    conn.commit()


def list_dataset_rows(conn: sqlite3.Connection) -> list[tuple[Dataset, bool]]:
    """Datasets plus their is_sample flag — for the API; the domain model stays flag-free."""
    rows = conn.execute(
        "SELECT id, name, description, examples, is_sample FROM datasets ORDER BY name"
    ).fetchall()
    out: list[tuple[Dataset, bool]] = []
    for r in rows:
        dataset = Dataset.model_validate(
            {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "examples": _load_examples(r["examples"]),
            }
        )
        out.append((dataset, bool(r["is_sample"])))
    return out


def remove_sample_data(conn: sqlite3.Connection) -> tuple[int, int]:
    """Delete only sample rows. Returns (datasets_deleted, runs_deleted)."""
    runs = conn.execute("DELETE FROM runs WHERE is_sample = 1").rowcount
    datasets = conn.execute("DELETE FROM datasets WHERE is_sample = 1").rowcount
    conn.commit()
    return datasets, runs


def clear_all_data(conn: sqlite3.Connection) -> tuple[int, int]:
    """Delete ALL datasets and runs (settings are untouched). Returns (datasets, runs)."""
    runs = conn.execute("DELETE FROM runs").rowcount
    datasets = conn.execute("DELETE FROM datasets").rowcount
    conn.commit()
    return datasets, runs


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


class DuplicateDatasetError(ValueError):
    """A dataset with the same name already exists — surfaced to the API as HTTP 409."""


def save_dataset(
    conn: sqlite3.Connection, name: str, description: str, examples: list[Example]
) -> Dataset:
    """Create a new dataset. Name must be unique (case-insensitive); id is a unique slug."""
    name = name.strip()
    if not name:
        raise ValueError("Dataset name is required.")
    clash = conn.execute(
        "SELECT 1 FROM datasets WHERE lower(name) = lower(?)", (name,)
    ).fetchone()
    if clash is not None:
        raise DuplicateDatasetError(f"A dataset named '{name}' already exists.")
    dataset = Dataset(
        id=_unique_id(conn, name),
        name=name,
        description=description.strip(),
        examples=examples,
    )
    conn.execute(
        "INSERT INTO datasets (id, name, description, examples) VALUES (?, ?, ?, ?)",
        (dataset.id, dataset.name, dataset.description, _examples_json(dataset)),
    )
    conn.commit()
    return dataset


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "dataset"


def _unique_id(conn: sqlite3.Connection, name: str) -> str:
    base = _slug(name)
    candidate, n = base, 1
    while conn.execute("SELECT 1 FROM datasets WHERE id = ?", (candidate,)).fetchone():
        n += 1
        candidate = f"{base}-{n}"
    return candidate
