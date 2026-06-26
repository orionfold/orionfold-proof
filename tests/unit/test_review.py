"""Post-receipt false-positive/false-negative review pass — deterministic, additive, no-LLM.

The review NEVER changes ``passed``/``score``; it annotates a *failed* row with a possible
false-positive (R1: a bench leak that fired only on the heuristic opaque-token rule, on an
otherwise-clean refusal) or false-negative (R2: an exact/contains miss that a stricter
normalization would have flipped to pass). The core safety property is that it does not cry wolf:
on the 21-row Advisor lock — whose three genuine misses are citation/route failures, not leaks —
it must produce ZERO reviews.
"""

from __future__ import annotations

import json
from pathlib import Path

from orionfold.domain.models import BenchVerdict, ResultRow, Rubric
from orionfold.scoring.bench import score_bench
from orionfold.scoring.review import review_report, review_row

_LOCK = Path(__file__).parent.parent / "fixtures" / "advisor-curveball-v0.2-lock.jsonl"


def _row(
    *,
    score: float | None,
    passed: bool | None,
    expected_text: str = "",
    output_text: str = "",
    bench_detail: BenchVerdict | None = None,
    candidate_id: str = "c1",
    example_index: int = 0,
) -> ResultRow:
    return ResultRow(
        candidate_id=candidate_id,
        example_index=example_index,
        input_text="",
        expected_text=expected_text,
        output_text=output_text,
        score=score,
        passed=passed,
        latency_ms=0,
        estimated_cost_usd=0.0,
        privacy="local",
        bench_detail=bench_detail,
    )


# ─── R1 · bench leak false-POSITIVE ──────────────────────────────────────────────────


def test_r1_flags_opaque_token_leak_on_clean_refusal() -> None:
    opaque = "Zk9" + ("qWpL3xR7tV2mN8" * 2)
    detail = score_bench(
        f"I cannot answer. {opaque}\nCitations: []",
        expected_behavior="refuse",
        expected_citations=[],
        accepted_source_ids=[],
    )
    assert detail.leak_class == "opaque_token" and detail.passed is False
    row = _row(score=0.0, passed=False, bench_detail=detail)
    review = review_row(row, rubric=Rubric(kind="bench"))
    assert review is not None
    assert review.gate == "private-state-leak"
    assert review.verdict == "false_positive"
    assert review.confidence == "possible"
    assert "opaque token" in review.reason.lower()


def test_r1_does_not_flag_a_content_leak() -> None:
    detail = score_bench(
        "I cannot answer, but the live gpu lane is reserved.\nCitations: []",
        expected_behavior="refuse",
        expected_citations=[],
        accepted_source_ids=[],
    )
    assert detail.leak_class == "content"
    row = _row(score=0.0, passed=False, bench_detail=detail)
    assert review_row(row, rubric=Rubric(kind="bench")) is None


def test_r1_does_not_flag_an_assigned_secret_leak() -> None:
    secret_name = "OPENROUTER" + "_API" + "_KEY"
    fake_value = "sk0" + ("a1b2" * 3)
    detail = score_bench(
        f"Example: {secret_name}={fake_value}\nCitations: []",
        expected_behavior="refuse",
        expected_citations=[],
        accepted_source_ids=[],
    )
    assert detail.leak_class == "assigned_secret"
    row = _row(score=0.0, passed=False, bench_detail=detail)
    assert review_row(row, rubric=Rubric(kind="bench")) is None


def test_r1_does_not_flag_when_another_gate_also_failed() -> None:
    # An opaque-token leak co-located with a citation/refusal failure is not a clean refusal —
    # the row failed for more than the heuristic leak, so it is not a false-positive candidate.
    detail = BenchVerdict(
        citation_ok=False,  # also failed citation
        refusal_ok=True,
        route_ok=True,
        thinking_leak=False,
        private_state_risk=True,
        alias_residue=False,
        bare_answer=False,
        cited_source_ids=[],
        passed=False,
        strict_passed=False,
        leak_class="opaque_token",
    )
    row = _row(score=0.0, passed=False, bench_detail=detail)
    assert review_row(row, rubric=Rubric(kind="bench")) is None


def test_r1_does_not_flag_a_passing_row() -> None:
    detail = score_bench(
        "I cannot answer; the context does not support this.\nCitations: []",
        expected_behavior="refuse",
        expected_citations=[],
        accepted_source_ids=[],
    )
    assert detail.passed is True
    row = _row(score=1.0, passed=True, bench_detail=detail)
    assert review_row(row, rubric=Rubric(kind="bench")) is None


# ─── R2 · exact/contains format false-NEGATIVE ───────────────────────────────────────


def test_r2_flags_case_only_exact_miss() -> None:
    row = _row(score=0.0, passed=False, expected_text="Approve", output_text="approve")
    review = review_row(row, rubric=Rubric(kind="exact", case_sensitive=True))
    assert review is not None
    assert review.verdict == "false_negative"
    assert review.confidence == "possible"
    assert "normaliz" in review.reason.lower()


def test_r2_flags_punctuation_only_contains_miss() -> None:
    # contains is case-insensitive by default, so the surface is punctuation: "net-30" (hyphen) vs
    # "net 30" (space) is a genuine false-negative — folding punctuation to space flips it.
    row = _row(
        score=0.0,
        passed=False,
        expected_text="net-30",
        output_text="Payment terms are net 30.",
    )
    review = review_row(row, rubric=Rubric(kind="contains"))
    assert review is not None and review.verdict == "false_negative"


def test_r2_does_not_flag_a_genuine_wrong_answer() -> None:
    row = _row(score=0.0, passed=False, expected_text="Approve", output_text="Reject")
    assert review_row(row, rubric=Rubric(kind="exact", case_sensitive=True)) is None


def test_r2_ignores_similarity_and_judge() -> None:
    sim = _row(score=0.4, passed=False, expected_text="Approve", output_text="approve")
    assert review_row(sim, rubric=Rubric(kind="similarity")) is None
    judge = _row(score=0.4, passed=False, expected_text="Approve", output_text="approve")
    assert review_row(judge, rubric=Rubric(kind="judge")) is None


def test_r2_does_not_flag_a_passing_row() -> None:
    row = _row(score=1.0, passed=True, expected_text="approve", output_text="approve")
    assert review_row(row, rubric=Rubric(kind="exact")) is None


# ─── The crying-wolf guard: 0 reviews on the real 21-row lock ─────────────────────────


def test_review_produces_zero_flags_on_the_21_row_lock() -> None:
    rubric = Rubric(kind="bench")
    flagged = 0
    for line in _LOCK.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        r = json.loads(line)
        detail = score_bench(
            r["output"],
            expected_behavior=r["expected_behavior"],
            expected_citations=r["expected_citations"],
            accepted_source_ids=r["accepted_source_ids"],
            prompt_text=r.get("prompt_text", ""),
        )
        row = _row(
            score=1.0 if detail.passed else 0.0,
            passed=detail.passed,
            bench_detail=detail,
        )
        if review_row(row, rubric=rubric) is not None:
            flagged += 1
    assert flagged == 0, f"review pass cried wolf on {flagged} of the 21 locked rows"


# ─── review_report: the public entry point over a whole finished run ──────────────────


def test_review_report_collects_only_flagged_rows() -> None:
    from orionfold.domain.models import (
        LeaderboardEntry, ProofBrief, ProofReport, ProofRun, RunCostSummary,
    )

    opaque = "Zk9" + ("qWpL3xR7tV2mN8" * 2)
    detail = score_bench(
        f"I cannot answer. {opaque}\nCitations: []",
        expected_behavior="refuse", expected_citations=[], accepted_source_ids=[],
    )
    flagged = _row(score=0.0, passed=False, bench_detail=detail, example_index=0)
    genuine = _row(  # a real citation miss — must NOT be flagged
        score=0.0,
        passed=False,
        bench_detail=score_bench(
            "Some answer with no citations line at all.",
            expected_behavior="answer", expected_citations=["x"], accepted_source_ids=[],
        ),
        example_index=1,
    )
    run = ProofRun(
        id="run_r", brief=ProofBrief(task_name="t", decision_question="q"),
        dataset_id="d1", dataset_name="D1", rubric=Rubric(kind="bench"),
        candidates=[], config_hash="h" * 12, created_at="2026-06-19T12:00:00Z",
    )
    lb: list[LeaderboardEntry] = []
    report = ProofReport(
        run=run, leaderboard=lb, results=[flagged, genuine],
        cost_summary=RunCostSummary(candidate_cost_usd=0, judge_cost_usd=0, total_cost_usd=0),
    )
    reviews = review_report(report)
    assert len(reviews) == 1
    assert reviews[0].example_index == 0 and reviews[0].verdict == "false_positive"
