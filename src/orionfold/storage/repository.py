"""Persistence operations over the SQLite connection — datasets and proof reports.

Reports are stored as validated JSON of the :class:`ProofReport` so the receipt and the API
always read back exactly what was run. Nothing here writes secrets; the report itself only
carries provider ids and the local/cloud boundary.
"""

from __future__ import annotations

import re
import sqlite3

from pydantic import BaseModel

from orionfold.data import (
    BUNDLED_DOMAIN_TAGS,
    bundled_bench_datasets,
    bundled_corpora,
    bundled_datasets,
)
from orionfold.domain.models import Corpus, Dataset, Example, ProofReport


class DatasetMeta(BaseModel):
    """Display/management metadata for a dataset — lives on the DB row + API only, never on the
    domain Dataset model, so config_hash stays untouched."""

    is_sample: bool
    tags: list[str]
    created_at: str
    source: str
    check_hint: str | None


def _load_meta(r: sqlite3.Row) -> DatasetMeta:
    import json

    keys = r.keys()
    raw_tags = r["tags"] if "tags" in keys else "[]"
    tags = json.loads(raw_tags) if raw_tags else []
    if not isinstance(tags, list):
        tags = []
    hint = (r["check_hint"] or "") if "check_hint" in keys else ""
    return DatasetMeta(
        is_sample=bool(r["is_sample"]),
        tags=[str(t) for t in tags],
        created_at=r["created_at"] if "created_at" in keys else "",
        source=r["source"] if "source" in keys else "",
        check_hint=hint or None,
    )


def _backfill_domain_tags(conn: sqlite3.Connection, dataset_id: str) -> None:
    """Backfill a bundled dataset's display domain tags onto its row, but ONLY where the row carries
    none yet — so the Datasets screen's domain chips + coverage strip are meaningful on a fresh
    install while an operator's own tag edit is never overwritten. Tags are display metadata only
    (never on the domain model, never a config_hash input), so this is hash-inert. Self-heals on
    every startup seed, mirroring the system_prompt backfill in :func:`seed_bench_datasets`."""
    import json

    tags = BUNDLED_DOMAIN_TAGS.get(dataset_id)
    if not tags:
        return
    conn.execute(
        "UPDATE datasets SET tags = ? "
        "WHERE id = ? AND (tags IS NULL OR tags = '' OR tags = '[]')",
        (json.dumps(tags), dataset_id),
    )


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
        _backfill_domain_tags(conn, dataset.id)
    conn.commit()


def _dataset_from_row(r: sqlite3.Row) -> Dataset:
    """Build a domain Dataset from a row, carrying corpus_id when the column is present."""
    keys = r.keys()
    return Dataset.model_validate(
        {
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "examples": _load_examples(r["examples"]),
            "corpus_id": (r["corpus_id"] if "corpus_id" in keys else None),
            "system_prompt": (r["system_prompt"] if "system_prompt" in keys else None),
        }
    )


def seed_corpora(conn: sqlite3.Connection) -> None:
    """Insert bundled corpus manifests if absent (idempotent). Runs before any bench dataset so a
    bench binding can validate its citations against a known corpus."""
    for corpus in bundled_corpora():
        upsert_corpus(conn, corpus)
    conn.commit()


def list_datasets(conn: sqlite3.Connection) -> list[Dataset]:
    rows = conn.execute(
        "SELECT id, name, description, examples, corpus_id, system_prompt FROM datasets ORDER BY name"
    ).fetchall()
    return [_dataset_from_row(r) for r in rows]


def get_dataset(conn: sqlite3.Connection, dataset_id: str) -> Dataset | None:
    r = conn.execute(
        "SELECT id, name, description, examples, corpus_id, system_prompt FROM datasets WHERE id = ?",
        (dataset_id,),
    ).fetchone()
    return None if r is None else _dataset_from_row(r)


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


def insert_sample_dataset(
    conn: sqlite3.Connection,
    dataset: Dataset,
    *,
    created_at: str = "",
    source: str = "",
    check_hint: str = "",
) -> None:
    """Upsert a sample dataset (is_sample=1). Stable id makes re-seeding idempotent.

    Writes the same display metadata columns a user-imported dataset gets (created_at /
    source / check_hint), so the seeded card reads with the full metadata line + hint chip
    rather than the bare "N examples" — WS-F F1. Display-only columns; never on the domain
    Dataset, so config_hash is untouched.
    """
    conn.execute(
        "INSERT OR REPLACE INTO datasets "
        "(id, name, description, examples, is_sample, created_at, source, check_hint) "
        "VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
        (
            dataset.id,
            dataset.name,
            dataset.description,
            _examples_json(dataset),
            created_at,
            source,
            check_hint,
        ),
    )
    conn.commit()


def seed_bench_datasets(conn: sqlite3.Connection) -> None:
    """Seed the bundled bench datasets as selectable rows carrying their corpus binding (idempotent).

    Bench datasets ship with a governing corpus and a per-row governance contract, so they can't
    auto-seed through the plain :func:`seed_datasets` path (which writes no ``corpus_id``). They are
    seeded **non-sample** (``is_sample=0``) on purpose: they're a first-class, always-present part of
    the install — they survive the Settings "remove samples" action, and they don't collide with the
    guided-demo's ``find(is_sample)`` target. Run *after* :func:`seed_corpora` so the binding has a
    corpus to validate against. ``INSERT OR IGNORE`` on a stable id makes re-seeding a no-op and never
    clobbers an operator's later edits.

    Backfill: a row seeded BEFORE the bench shipped its governance ``system_prompt`` (migration 7 added
    the column nullable; ``INSERT OR IGNORE`` never touches an existing row) carries it NULL — so the
    cockpit's auto-fill has nothing to apply and a Run scores ~1/21 instead of the headline 18/21. The
    follow-up ``UPDATE`` backfills the bundled ``system_prompt`` + ``corpus_id`` onto such a row, but
    ONLY where the prompt is still NULL/empty, so an operator's edit is never overwritten. Hash-safe:
    the dataset's ``system_prompt`` is provenance, not a ``config_hash`` input (the *candidate's*
    applied prompt is what enters the hash)."""
    for dataset in bundled_bench_datasets():
        conn.execute(
            "INSERT OR IGNORE INTO datasets "
            "(id, name, description, examples, is_sample, source, corpus_id, system_prompt) "
            "VALUES (?, ?, ?, ?, 0, ?, ?, ?)",
            (
                dataset.id,
                dataset.name,
                dataset.description,
                _examples_json(dataset),
                "Bundled with Orionfold",
                dataset.corpus_id,
                dataset.system_prompt,
            ),
        )
        conn.execute(
            "UPDATE datasets SET system_prompt = ?, corpus_id = ? "
            "WHERE id = ? AND (system_prompt IS NULL OR system_prompt = '')",
            (dataset.system_prompt, dataset.corpus_id, dataset.id),
        )
        _backfill_domain_tags(conn, dataset.id)
    conn.commit()


def insert_pack_dataset(conn: sqlite3.Connection, dataset: Dataset, *, source: str) -> bool:
    """Install a pack's dataset under its OWN stable id (idempotent; non-sample).

    Mirrors :func:`seed_bench_datasets` (``INSERT OR IGNORE`` on a stable id, carrying
    ``corpus_id`` + ``system_prompt``) rather than :func:`save_dataset` (which slugs a *new* id and
    rejects a name clash) — a pack must install under the id its reference receipt + leaderboard
    already reference, and re-unlocking must be a no-op that never clobbers operator edits. Returns
    True iff a new row was inserted (False when it already existed)."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO datasets "
        "(id, name, description, examples, is_sample, source, corpus_id, system_prompt) "
        "VALUES (?, ?, ?, ?, 0, ?, ?, ?)",
        (
            dataset.id,
            dataset.name,
            dataset.description,
            _examples_json(dataset),
            source,
            dataset.corpus_id,
            dataset.system_prompt,
        ),
    )
    conn.commit()
    return cur.rowcount > 0


def list_dataset_rows(conn: sqlite3.Connection) -> list[tuple[Dataset, DatasetMeta]]:
    """Datasets plus display metadata — for the API; the domain model stays flag-free."""
    rows = conn.execute(
        "SELECT id, name, description, examples, is_sample, tags, created_at, source, check_hint, "
        "corpus_id, system_prompt FROM datasets ORDER BY name"
    ).fetchall()
    return [(_dataset_from_row(r), _load_meta(r)) for r in rows]


def get_dataset_meta(conn: sqlite3.Connection, dataset_id: str) -> DatasetMeta | None:
    r = conn.execute(
        "SELECT is_sample, tags, created_at, source, check_hint FROM datasets WHERE id = ?",
        (dataset_id,),
    ).fetchone()
    return None if r is None else _load_meta(r)


def update_dataset_meta(
    conn: sqlite3.Connection,
    dataset_id: str,
    *,
    tags: list[str] | None = None,
    description: str | None = None,
    check_hint: str | None = None,
) -> bool:
    """Update only the provided metadata fields. Never touches examples. False if id unknown."""
    import json

    if conn.execute("SELECT 1 FROM datasets WHERE id = ?", (dataset_id,)).fetchone() is None:
        return False
    sets: list[str] = []
    params: list[object] = []
    if tags is not None:
        sets.append("tags = ?")
        params.append(json.dumps([str(t).strip() for t in tags if str(t).strip()]))
    if description is not None:
        sets.append("description = ?")
        params.append(description.strip())
    if check_hint is not None:
        sets.append("check_hint = ?")
        params.append(check_hint.strip())
    if sets:
        params.append(dataset_id)
        conn.execute(f"UPDATE datasets SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()
    return True


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
    """Most recent first. Un-picked quick-compare runs are hidden — the pick is the proof, so a
    quick run without one is an abandoned draft, not a receipt."""
    rows = conn.execute("SELECT report FROM runs ORDER BY created_at DESC").fetchall()
    reports = [ProofReport.model_validate_json(r["report"]) for r in rows]
    return [
        rep for rep in reports
        if not (rep.run.mode == "quick" and rep.run.chosen_winner is None)
    ]


def _examples_json(dataset: Dataset) -> str:
    import json

    return json.dumps([e.model_dump() for e in dataset.examples])


def _load_examples(raw: str) -> list[dict]:
    import json

    return json.loads(raw)


class DuplicateDatasetError(ValueError):
    """A dataset with the same name already exists — surfaced to the API as HTTP 409."""


def save_dataset(
    conn: sqlite3.Connection,
    name: str,
    description: str,
    examples: list[Example],
    *,
    tags: list[str] | None = None,
    source: str = "",
    check_hint: str | None = None,
    created_at: str = "",
    corpus_id: str | None = None,
) -> Dataset:
    """Create a new dataset. Name must be unique (case-insensitive); id is a unique slug.

    A ``corpus_id`` binds a bench dataset to its governing corpus; the binding's integrity (the
    corpus exists and every cited id is drawn from it) is validated by the caller via
    :func:`validate_bench_binding` before this is reached.
    """
    import json

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
        corpus_id=corpus_id,
    )
    clean_tags = [str(t).strip() for t in (tags or []) if str(t).strip()]
    conn.execute(
        "INSERT INTO datasets "
        "(id, name, description, examples, tags, created_at, source, check_hint, corpus_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            dataset.id,
            dataset.name,
            dataset.description,
            _examples_json(dataset),
            json.dumps(clean_tags),
            created_at,
            source,
            (check_hint or "").strip(),
            corpus_id,
        ),
    )
    conn.commit()
    return dataset


# ─── Corpus CRUD + bench-binding integrity gate (spec §4) ─────────────────────────────


def upsert_corpus(conn: sqlite3.Connection, corpus: Corpus) -> Corpus:
    """Insert or replace a corpus by id. Idempotent — used to seed the bundled corpus."""
    import json

    conn.execute(
        "INSERT OR REPLACE INTO corpora (id, name, description, source_ids) VALUES (?, ?, ?, ?)",
        (corpus.id, corpus.name, corpus.description, json.dumps(corpus.source_ids)),
    )
    conn.commit()
    return corpus


def get_corpus(conn: sqlite3.Connection, corpus_id: str) -> Corpus | None:
    r = conn.execute(
        "SELECT id, name, description, source_ids FROM corpora WHERE id = ?", (corpus_id,)
    ).fetchone()
    if r is None:
        return None
    import json

    return Corpus(
        id=r["id"], name=r["name"], description=r["description"],
        source_ids=list(json.loads(r["source_ids"] or "[]")),
    )


def list_corpora(conn: sqlite3.Connection) -> list[Corpus]:
    import json

    rows = conn.execute(
        "SELECT id, name, description, source_ids FROM corpora ORDER BY name"
    ).fetchall()
    return [
        Corpus(
            id=r["id"], name=r["name"], description=r["description"],
            source_ids=list(json.loads(r["source_ids"] or "[]")),
        )
        for r in rows
    ]


class BenchBindingError(ValueError):
    """A bench dataset's corpus binding is invalid — surfaced to the API as HTTP 400."""


def validate_bench_binding(
    conn: sqlite3.Connection, corpus_id: str | None, examples: list[Example]
) -> Corpus:
    """Validate a bench dataset's binding: the corpus exists and every cited id is drawn from it.

    The integrity gate of spec §4 — provenance, not retrieval. Raises :class:`BenchBindingError`
    when ``corpus_id`` is missing/unknown or any expected/accepted id is outside the corpus.
    """
    if not corpus_id:
        raise BenchBindingError("A bench dataset must bind a corpus (corpus_id is required).")
    corpus = get_corpus(conn, corpus_id)
    if corpus is None:
        raise BenchBindingError(f"Unknown corpus '{corpus_id}'.")
    known = set(corpus.source_ids)
    cited: set[str] = set()
    for ex in examples:
        cited.update(ex.expected_citations)
        cited.update(ex.accepted_source_ids)
    unknown = sorted(cited - known)
    if unknown:
        raise BenchBindingError(
            f"Citations not in corpus '{corpus_id}': {', '.join(unknown)}."
        )
    return corpus


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
