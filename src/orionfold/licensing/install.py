"""install_pack — assemble a verified :class:`Pack` into the local store (the unlock core fn).

A thin orchestration over **existing** store primitives (``upsert_corpus`` / ``insert_pack_dataset`` /
``save_report`` + the ``models.json`` overlay) — it adds no migration and never touches a scoring or
``config_hash`` path, so the mock matrix freeze ``467ddd96c9a5`` and the similarity freeze
``87531228f132`` cannot move. Idempotent: re-unlocking the same pack is a no-op that never clobbers
operator edits (every write is INSERT-OR-IGNORE / upsert by stable id).

This is the ADR-0004 §3 core fn; the ``orionfold unlock`` CLI verb is a thin shell over it.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from orionfold.licensing.pack import Pack
from orionfold.storage.repository import (
    insert_pack_dataset,
    save_report,
    upsert_corpus,
    validate_bench_binding,
)

PACK_SOURCE = "Unlocked pack"


@dataclass(frozen=True)
class InstallResult:
    """What an install landed — for the CLI's one-line confirmation."""

    pack_id: str
    pack_name: str
    corpus_id: str | None
    dataset_id: str | None
    dataset_name: str | None
    dataset_was_new: bool
    reference_run_id: str | None
    model_repo_id: str | None


def install_pack(conn: sqlite3.Connection, pack: Pack) -> InstallResult:
    """Install a verified pack's artifacts into the store + model overlay. Idempotent.

    Order matters: the corpus must exist before :func:`validate_bench_binding` can confirm the
    dataset's citations are drawn from it, which must pass before the dataset is inserted."""
    corpus_id = None
    if pack.corpus is not None:
        upsert_corpus(conn, pack.corpus)
        corpus_id = pack.corpus.id

    dataset_id = dataset_name = None
    dataset_was_new = False
    if pack.dataset is not None:
        ds = pack.dataset
        # A pack dataset binds a governing corpus; validate the citation provenance before install
        # (the same integrity gate a bench dataset passes at seed time).
        if ds.corpus_id:
            validate_bench_binding(conn, ds.corpus_id, ds.examples)
        dataset_was_new = insert_pack_dataset(conn, ds, source=PACK_SOURCE)
        dataset_id, dataset_name = ds.id, ds.name

    reference_run_id = None
    if pack.reference_receipt is not None:
        save_report(conn, pack.reference_receipt)
        reference_run_id = pack.reference_receipt.run.id

    model_repo_id = None
    if pack.manifest.model is not None:
        model_repo_id = _register_model(pack.manifest.model)

    return InstallResult(
        pack_id=pack.manifest.pack_id,
        pack_name=pack.manifest.name,
        corpus_id=corpus_id,
        dataset_id=dataset_id,
        dataset_name=dataset_name,
        dataset_was_new=dataset_was_new,
        reference_run_id=reference_run_id,
        model_repo_id=model_repo_id,
    )


def _register_model(pointer) -> str:
    """Record the pack's GGUF pointer in the ~/.orionfold/models.json overlay (spec-#1 path).

    Reuses the curated catalog entry for a known repo (so a roster model keeps its display name /
    tier); otherwise synthesizes a generic local entry — the same resolution ``orionfold pull`` uses.
    The pack only records *intent*; ``GET /api/tags`` is still truth, so an un-pulled model self-
    corrects to "Pull to enable" in the panel."""
    from orionfold.catalog.models import CatalogModel
    from orionfold.catalog.overlay import add_to_overlay
    from orionfold.cli import _overlay_model_for

    model: CatalogModel = _overlay_model_for(pointer.repo_id)
    if pointer.display_name:
        model = model.model_copy(update={"display_name": pointer.display_name})
    add_to_overlay(model)
    return pointer.repo_id
