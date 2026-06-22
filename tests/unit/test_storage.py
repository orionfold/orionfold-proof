"""Storage: append-only migrations are idempotent and reports round-trip losslessly."""

import pytest

from orionfold.data import load_dataset
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
    assert count == 1
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
