"""Storage: append-only migrations are idempotent and reports round-trip losslessly."""

import pytest

from orionfold.data import bundled_datasets, load_dataset
from orionfold.domain.models import Candidate, Example, ProofBrief, Rubric
from orionfold.proof.engine import run_proof
from orionfold.storage.db import apply_migrations, connect
from orionfold.storage.repository import (
    DatasetMeta,
    get_dataset,
    get_dataset_meta,
    get_report,
    list_dataset_rows,
    list_runs,
    save_dataset,
    save_report,
    seed_datasets,
    update_dataset_meta,
)


def _conn():
    conn = connect(":memory:")
    apply_migrations(conn)
    return conn


def test_migrations_are_idempotent():
    conn = connect(":memory:")
    first = apply_migrations(conn)
    second = apply_migrations(conn)
    assert first > 0
    assert second == 0  # nothing new to apply on the second call


def test_seed_is_idempotent():
    conn = _conn()
    seed_datasets(conn)
    seed_datasets(conn)
    count = conn.execute("SELECT COUNT(*) AS n FROM datasets").fetchone()["n"]
    assert count == len(bundled_datasets())  # INSERT OR IGNORE → no duplicates on re-seed
    assert get_dataset(conn, "investment-memo-summarization") is not None


def test_report_round_trips_through_storage():
    conn = _conn()
    seed_datasets(conn)
    report = run_proof(
        run_id="run_store",
        created_at="2026-06-19T12:00:00Z",
        brief=ProofBrief(task_name="t", decision_question="q"),
        dataset=load_dataset("investment-memo-summarization"),
        candidates=[Candidate(id="mock_good", label="g", provider_id="mock_good")],
        rubric=Rubric(),
    )
    save_report(conn, report)
    loaded = get_report(conn, "run_store")
    assert loaded is not None
    assert loaded.model_dump() == report.model_dump()
    assert len(list_runs(conn)) == 1


def test_save_dataset_persists_and_slugs_id(tmp_path):
    from orionfold.storage.db import apply_migrations, connect
    from orionfold.storage.repository import get_dataset, save_dataset
    from orionfold.domain.models import Example

    conn = connect(tmp_path / "t.db")
    apply_migrations(conn)
    saved = save_dataset(conn, "My Memo Set!", "", [Example(input_text="a", expected_text="b")])
    assert saved.id == "my-memo-set"
    assert get_dataset(conn, "my-memo-set").name == "My Memo Set!"


def test_save_dataset_rejects_duplicate_name_case_insensitively(tmp_path):
    from orionfold.storage.db import apply_migrations, connect
    from orionfold.storage.repository import DuplicateDatasetError, save_dataset
    from orionfold.domain.models import Example

    conn = connect(tmp_path / "t.db")
    apply_migrations(conn)
    save_dataset(conn, "Memos", "", [Example(input_text="a", expected_text="b")])
    with pytest.raises(DuplicateDatasetError):
        save_dataset(conn, "  memos ", "", [Example(input_text="c", expected_text="d")])


def test_save_dataset_dedups_id_for_distinct_names(tmp_path):
    from orionfold.storage.db import apply_migrations, connect
    from orionfold.storage.repository import save_dataset
    from orionfold.domain.models import Example

    conn = connect(tmp_path / "t.db")
    apply_migrations(conn)
    a = save_dataset(conn, "My Set", "", [Example(input_text="a", expected_text="b")])
    b = save_dataset(conn, "My Set!", "", [Example(input_text="c", expected_text="d")])
    assert a.id == "my-set"
    assert b.id == "my-set-2"


def test_save_dataset_persists_tags_source_created_and_check_hint():
    conn = _conn()
    ds = save_dataset(
        conn,
        "Tagged set",
        "",
        [Example(input_text="a", expected_text="b")],
        tags=["Legal", "Finance"],
        source="file:cases.xlsx",
        check_hint="substring",
        created_at="2026-06-22T10:00:00Z",
    )
    rows = {d.id: m for d, m in list_dataset_rows(conn)}
    meta = rows[ds.id]
    assert isinstance(meta, DatasetMeta)
    assert meta.tags == ["Legal", "Finance"]
    assert meta.source == "file:cases.xlsx"
    assert meta.created_at == "2026-06-22T10:00:00Z"
    assert meta.check_hint == "substring"
    assert meta.is_sample is False


def test_legacy_dataset_reads_empty_meta_defaults():
    conn = _conn()
    ds = save_dataset(conn, "Bare", "", [Example(input_text="a", expected_text="b")])
    meta = get_dataset_meta(conn, ds.id)
    assert meta is not None
    assert meta.tags == []
    assert meta.check_hint is None
    assert meta.source == ""


def test_update_dataset_meta_changes_only_provided_fields():
    conn = _conn()
    ds = save_dataset(conn, "Editable", "old desc", [Example(input_text="a", expected_text="b")])
    assert update_dataset_meta(conn, ds.id, tags=["Support"], check_hint="numeric") is True
    meta = get_dataset_meta(conn, ds.id)
    assert meta is not None
    assert meta.tags == ["Support"]
    assert meta.check_hint == "numeric"
    after = {d.id: d for d, _ in list_dataset_rows(conn)}[ds.id]
    assert after.description == "old desc"


def test_update_dataset_meta_unknown_id_returns_false():
    conn = _conn()
    assert update_dataset_meta(conn, "nope", tags=["x"]) is False


# ─── Migration 6: Corpus + nullable corpus_id binding ─────────────────────────────────


def test_migration_six_adds_corpora_and_corpus_id():
    conn = _conn()
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(datasets)")}
    assert "corpus_id" in cols
    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "corpora" in tables


def test_corpus_crud_round_trip():
    from orionfold.domain.models import Corpus
    from orionfold.storage.repository import get_corpus, list_corpora, upsert_corpus

    conn = _conn()
    c = Corpus(id="field-notes", name="Field notes", description="d", source_ids=["a", "b"])
    upsert_corpus(conn, c)
    back = get_corpus(conn, "field-notes")
    assert back is not None and back.source_ids == ["a", "b"]
    assert [x.id for x in list_corpora(conn)] == ["field-notes"]
    # Idempotent replace.
    upsert_corpus(conn, c.model_copy(update={"source_ids": ["a", "b", "c"]}))
    assert get_corpus(conn, "field-notes").source_ids == ["a", "b", "c"]


def test_bench_dataset_corpus_id_round_trips():
    conn = _conn()
    from orionfold.storage.repository import save_dataset

    ds = save_dataset(
        conn, "Bench set", "d",
        [Example(input_text="q", expected_text="", expected_behavior="refuse")],
        corpus_id="field-notes",
    )
    assert ds.corpus_id == "field-notes"
    assert get_dataset(conn, ds.id).corpus_id == "field-notes"
    # A non-bench dataset keeps corpus_id None.
    plain = save_dataset(conn, "Plain set", "d", [Example(input_text="q", expected_text="e")])
    assert get_dataset(conn, plain.id).corpus_id is None


def test_validate_bench_binding_requires_known_corpus_and_in_corpus_citations():
    from orionfold.domain.models import Corpus
    from orionfold.storage.repository import (
        BenchBindingError,
        upsert_corpus,
        validate_bench_binding,
    )

    conn = _conn()
    upsert_corpus(conn, Corpus(id="fn", name="FN", source_ids=["src_a", "src_b"]))
    good = [Example(input_text="q", expected_text="", expected_behavior="answer",
                    expected_citations=["src_a"])]
    assert validate_bench_binding(conn, "fn", good).id == "fn"
    # Missing corpus_id.
    with pytest.raises(BenchBindingError):
        validate_bench_binding(conn, None, good)
    # Unknown corpus.
    with pytest.raises(BenchBindingError):
        validate_bench_binding(conn, "nope", good)
    # A cited id outside the corpus.
    bad = [Example(input_text="q", expected_text="", expected_behavior="answer",
                   expected_citations=["src_z"])]
    with pytest.raises(BenchBindingError):
        validate_bench_binding(conn, "fn", bad)


def test_seed_bench_datasets_lists_with_corpus_and_validates():
    """The bundled bench dataset seeds as a selectable DB row carrying its corpus binding, so the
    cockpit's Governance-bench card surfaces and the binding passes validation. Idempotent."""
    from orionfold.data import bundled_bench_datasets
    from orionfold.storage.repository import (
        seed_bench_datasets,
        seed_corpora,
        validate_bench_binding,
    )

    conn = _conn()
    seed_corpora(conn)  # corpora must exist before a bench binding can validate
    seed_bench_datasets(conn)
    seed_bench_datasets(conn)  # idempotent: no duplicate rows on re-seed

    bench = bundled_bench_datasets()
    assert bench, "expected at least one bundled bench dataset"
    for ds in bench:
        row = get_dataset(conn, ds.id)
        assert row is not None, f"{ds.id} not listed after seeding"
        # The corpus binding is what makes the FE offer the Governance bench card.
        assert row.corpus_id == ds.corpus_id and row.corpus_id is not None
        # Per-row governance contract survives the round-trip (drives the deterministic scorer).
        assert any(ex.expected_behavior is not None for ex in row.examples)
        # The binding's integrity holds against the seeded corpus.
        assert validate_bench_binding(conn, ds.corpus_id, ds.examples).id == ds.corpus_id

    # Listed alongside the always-on datasets, not hidden.
    listed_ids = {row[0].id for row in list_dataset_rows(conn)}
    assert {ds.id for ds in bench} <= listed_ids

    # Seeded non-sample: it's a first-class always-present dataset, so the Settings
    # "remove samples" action must not delete it (it only returns on restart otherwise).
    from orionfold.storage.repository import remove_sample_data

    remove_sample_data(conn)
    survivors = {row[0].id for row in list_dataset_rows(conn)}
    assert {ds.id for ds in bench} <= survivors


def test_seed_backfills_domain_tags_onto_bundled_datasets():
    """Bundled dataset JSONs carry no tags (domain is implicit in their names), so the seed backfills
    display domain tags onto a fresh row — making the Datasets screen's domain chips + coverage strip
    meaningful out of the box. Both the plain and bench seed paths backfill."""
    from orionfold.data import BUNDLED_DOMAIN_TAGS
    from orionfold.storage.repository import seed_bench_datasets, seed_corpora

    conn = _conn()
    seed_datasets(conn)
    seed_corpora(conn)
    seed_bench_datasets(conn)

    metas = {row[0].id: row[1] for row in list_dataset_rows(conn)}
    for dataset_id, tags in BUNDLED_DOMAIN_TAGS.items():
        assert dataset_id in metas, f"{dataset_id} not seeded"
        assert metas[dataset_id].tags == tags, f"{dataset_id} should carry domain tags {tags}"


def test_seed_tag_backfill_never_clobbers_an_operator_edit():
    """The backfill mirrors the system_prompt backfill: it only fills a row that has no tags yet, so
    an operator who has edited a bundled dataset's tags keeps their edit across the next startup seed."""
    conn = _conn()
    seed_datasets(conn)
    # Operator retags a bundled dataset by hand.
    assert update_dataset_meta(conn, "support-ticket-triage", tags=["My Team", "Tier 1"]) is True
    # A subsequent startup re-seed must NOT overwrite that edit.
    seed_datasets(conn)
    meta = get_dataset_meta(conn, "support-ticket-triage")
    assert meta is not None and meta.tags == ["My Team", "Tier 1"]


def test_bundled_bench_dataset_carries_governance_system_prompt():
    """A bench dataset ships its governance contract as `system_prompt`, so selecting it +
    a model + Run reproduces the published verdict turnkey (no manual Task-instruction paste).
    The prompt round-trips through storage."""
    from orionfold.data import bundled_bench_datasets
    from orionfold.storage.repository import seed_bench_datasets, seed_corpora

    conn = _conn()
    seed_corpora(conn)
    seed_bench_datasets(conn)
    for ds in bundled_bench_datasets():
        assert ds.system_prompt and "Citations:" in ds.system_prompt, (
            f"{ds.id} must bundle the governance system prompt"
        )
        row = get_dataset(conn, ds.id)
        assert row is not None and row.system_prompt == ds.system_prompt


def test_seed_bench_datasets_backfills_a_null_governance_prompt_on_an_existing_row():
    """The turnkey bench-prompt regression: a bench row seeded BEFORE the dataset shipped its
    governance `system_prompt` (or a dev/user DB row from before that fix) carries `system_prompt`
    NULL. `INSERT OR IGNORE` on the stable id never updates it, so the cockpit auto-fill has nothing
    to apply and a Run scores ~1/21 instead of the headline 18/21. Re-seeding must BACKFILL the
    bundled prompt (and corpus binding) onto such a row, while never clobbering an operator's edit."""
    from orionfold.data import bundled_bench_datasets
    from orionfold.storage.repository import _examples_json, seed_bench_datasets, seed_corpora

    conn = _conn()
    seed_corpora(conn)
    bench = bundled_bench_datasets()
    assert bench, "expected at least one bundled bench dataset"

    # Simulate the pre-fix install: the bench row exists with NULL system_prompt + NULL corpus_id,
    # exactly the state observed in a real ~/.orionfold/proof.db.
    for ds in bench:
        conn.execute(
            "INSERT INTO datasets (id, name, description, examples, is_sample, system_prompt, "
            "corpus_id) VALUES (?, ?, ?, ?, 0, NULL, NULL)",
            (ds.id, ds.name, ds.description, _examples_json(ds)),
        )
    conn.commit()
    for ds in bench:
        pre = get_dataset(conn, ds.id)
        assert pre is not None and pre.system_prompt is None  # precondition: the gotcha state

    seed_bench_datasets(conn)

    for ds in bench:
        row = get_dataset(conn, ds.id)
        assert row is not None
        assert row.system_prompt == ds.system_prompt, f"{ds.id} prompt not backfilled"
        assert row.corpus_id == ds.corpus_id, f"{ds.id} corpus binding not backfilled"


def test_seed_bench_datasets_never_clobbers_an_operator_edited_prompt():
    """Backfill must only fill a NULL/empty prompt — an operator who edited the bench prompt keeps it
    across restarts (re-seed is a no-op on a non-empty prompt, same guarantee `INSERT OR IGNORE` gave)."""
    from orionfold.data import bundled_bench_datasets
    from orionfold.storage.repository import seed_bench_datasets, seed_corpora

    conn = _conn()
    seed_corpora(conn)
    seed_bench_datasets(conn)  # seed the real rows
    edited = "OPERATOR EDIT — Citations: [override]"
    for ds in bundled_bench_datasets():
        conn.execute("UPDATE datasets SET system_prompt = ? WHERE id = ?", (edited, ds.id))
    conn.commit()

    seed_bench_datasets(conn)  # restart re-seed must not overwrite the edit

    for ds in bundled_bench_datasets():
        row = get_dataset(conn, ds.id)
        assert row is not None and row.system_prompt == edited


def test_dataset_system_prompt_is_not_a_config_hash_input():
    """`system_prompt` is dataset provenance, not a run-identity input (like corpus_id) — adding it
    must NOT move existing dataset hashes. The candidate's applied prompt is what enters the hash."""
    from orionfold.domain.models import Candidate, Dataset, Example, Rubric
    from orionfold.proof.engine import config_hash

    examples = [Example(input_text="q", expected_text="a")]
    cands = [Candidate(id="m", label="m", provider_id="mock_good")]
    rubric = Rubric(kind="similarity")
    without = Dataset(id="d", name="D", examples=examples)
    withp = Dataset(id="d", name="D", examples=examples, system_prompt="You are an advisor. Citations: []")
    assert config_hash(without, cands, rubric) == config_hash(withp, cands, rubric)
