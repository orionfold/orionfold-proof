"""Receipt presents a calm 'No clear winner' state when nothing passed."""

from __future__ import annotations

from orionfold.domain.models import (
    Candidate,
    LeaderboardEntry,
    ProofBrief,
    ProofReport,
    ProofRun,
    ResultRow,
    Rubric,
)
from orionfold.receipts.export import build_receipt, to_markdown


def _report(*, pass_count: int, error_count: int) -> ProofReport:
    cand = Candidate(id="erro", label="Erro", provider_id="erro")
    run = ProofRun(
        id="run_test01",
        brief=ProofBrief(task_name="t", decision_question="q?"),
        dataset_id="d",
        dataset_name="D",
        rubric=Rubric(threshold=0.8),
        candidates=[cand],
        config_hash="hash",
        created_at="2026-06-20T00:00:00Z",
    )
    entry = LeaderboardEntry(
        candidate_id="erro", label="Erro", provider_id="erro", privacy="local",
        total=5, pass_count=pass_count, pass_rate=pass_count / 5,
        avg_score=0.0, avg_latency_ms=0, total_estimated_cost_usd=0.0,
        failure_count=5 - pass_count, error_count=error_count,
    )
    rows = [
        ResultRow(candidate_id="erro", example_index=i, input_text="in",
                  expected_text="exp", output_text="", score=0.0, passed=False,
                  latency_ms=0, estimated_cost_usd=0.0, privacy="local", error="boom")
        for i in range(5)
    ]
    return ProofReport(run=run, leaderboard=[entry], results=rows)


def test_no_winner_verdict_and_reason():
    data = build_receipt(_report(pass_count=0, error_count=5))
    assert data["receipt_version"] == 4
    assert data["verdict"] == "No clear winner"
    assert "No candidate passed the rubric" in data["recommendation"]
    assert "0.80" in data["recommendation"]


def test_markdown_marks_all_errored_row_and_has_no_star():
    md = to_markdown(_report(pass_count=0, error_count=5))
    assert "⭐" not in md
    assert "errored, no output" in md


def test_version_is_four_with_a_winner():
    data = build_receipt(_report(pass_count=5, error_count=0))
    assert data["receipt_version"] == 4
    assert data["verdict"] != "No clear winner"
