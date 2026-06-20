"""Storage: append-only migrations are idempotent and reports round-trip losslessly."""

from orionfold.data import load_dataset
from orionfold.domain.models import Candidate, ProofBrief, Rubric
from orionfold.proof.engine import run_proof
from orionfold.storage.db import apply_migrations, connect
from orionfold.storage.repository import (
    get_dataset,
    get_report,
    list_runs,
    save_report,
    seed_datasets,
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
