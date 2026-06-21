"""Receipt presents a calm 'No clear winner' state when nothing passed."""

from __future__ import annotations

from orionfold.domain.models import (
    Candidate,
    ProofBrief,
    ProofReport,
    ProofRun,
    ResultRow,
    Rubric,
)
from orionfold.proof.leaderboard import build_leaderboard
from orionfold.receipts.export import build_receipt, to_markdown


def _cand(cid: str) -> Candidate:
    return Candidate(id=cid, label=cid.capitalize(), provider_id=cid)


def _row(cid: str, idx: int, *, score: float, passed: bool, latency: int,
         cost: float = 0.0, error: str | None = None) -> ResultRow:
    return ResultRow(
        candidate_id=cid,
        example_index=idx,
        input_text="in",
        expected_text="exp",
        output_text="" if error else "out",
        score=score,
        passed=passed,
        latency_ms=latency,
        estimated_cost_usd=cost,
        privacy="local",
        error=error,
    )


def _run(candidates: list[Candidate], results: list[ResultRow]) -> ProofReport:
    run = ProofRun(
        id="run_test01",
        brief=ProofBrief(task_name="t", decision_question="q?"),
        dataset_id="d",
        dataset_name="D",
        rubric=Rubric(threshold=0.8),
        candidates=candidates,
        config_hash="hash",
        created_at="2026-06-20T00:00:00Z",
    )
    leaderboard = build_leaderboard(candidates, results)
    return ProofReport(run=run, leaderboard=leaderboard, results=results)


def test_no_winner_verdict_and_reason():
    cand = _cand("erro")
    results = [
        _row("erro", i, score=0.0, passed=False, latency=0, error="boom")
        for i in range(5)
    ]
    data = build_receipt(_run([cand], results))
    assert data["receipt_version"] == 4
    assert data["verdict"] == "No clear winner"
    assert "No candidate passed the rubric" in data["recommendation"]
    assert "0.80" in data["recommendation"]


def test_markdown_marks_all_errored_row_and_has_no_star():
    """No ⭐ is produced by build_leaderboard when every result is an error.

    The 'recommended' flag is set by production logic — this test is NOT vacuous:
    it exercises build_leaderboard to confirm it leaves recommended=False when
    pass_count==0, then asserts the receipt renderer correctly omits the star.
    """
    cand = _cand("erro")
    results = [
        _row("erro", i, score=0.0, passed=False, latency=0, error="boom")
        for i in range(5)
    ]
    report = _run([cand], results)
    # build_leaderboard must have left recommended=False (no passes)
    assert all(not e.recommended for e in report.leaderboard)
    md = to_markdown(report)
    assert "⭐" not in md
    assert "errored, no output" in md


def test_star_appears_when_candidate_passes():
    """Positive control: ⭐ IS rendered when a candidate passes at least one example.

    This confirms the marker is wired end-to-end and that the suppression in
    test_markdown_marks_all_errored_row_and_has_no_star is meaningful, not silent.
    """
    good = _cand("good")
    results = [
        _row("good", 0, score=1.0, passed=True, latency=40),
        _row("good", 1, score=1.0, passed=True, latency=40),
    ]
    report = _run([good], results)
    assert report.leaderboard[0].recommended is True
    md = to_markdown(report)
    assert "⭐" in md


def test_version_is_four_with_a_winner():
    cand = _cand("good")
    results = [
        _row("good", i, score=1.0, passed=True, latency=50)
        for i in range(5)
    ]
    data = build_receipt(_run([cand], results))
    assert data["receipt_version"] == 4
    assert data["verdict"] != "No clear winner"
