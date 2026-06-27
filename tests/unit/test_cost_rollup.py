"""``cost_rollup`` — the cumulative cost rollup core function (Arena-shape redesign Slice 3).

A read-only rollup over persisted ``RunCostSummary`` fields (``candidate_cost_usd`` = eval,
``judge_cost_usd`` = judge): cumulative spend in a window (today / all) split eval vs judge,
plus a cost / pass-rate trend series. Mirrors the ``track_record`` pattern — reads existing
fields, re-runs no scoring, so it can never touch ``config_hash``.
"""

from __future__ import annotations

from orionfold.domain.models import (
    Candidate,
    LeaderboardEntry,
    ProofBrief,
    ProofReport,
    ProofRun,
    Rubric,
    RunCostSummary,
)
from orionfold.proof import cost_rollup


def _entry(candidate_id: str, *, pass_count: int, total: int = 5) -> LeaderboardEntry:
    return LeaderboardEntry(
        candidate_id=candidate_id,
        label=candidate_id,
        provider_id="mock",
        privacy="local",
        model=None,
        total=total,
        pass_count=pass_count,
        pass_rate=pass_count / total if total else 0.0,
        avg_score=pass_count / total if total else 0.0,
        avg_latency_ms=10,
        total_estimated_cost_usd=0.0,
        failure_count=total - pass_count,
        error_count=0,
        recommended=False,
    )


def _report(
    *,
    run_id: str,
    created_at: str,
    eval_cost: float,
    judge_cost: float,
    leaderboard: list[LeaderboardEntry] | None = None,
    mode: str = "full",
    chosen_winner: str | None = None,
    rubric_kind: str = "exact",
) -> ProofReport:
    lb = leaderboard if leaderboard is not None else [_entry("gpt", pass_count=4)]
    run = ProofRun(
        id=run_id,
        brief=ProofBrief(task_name="t", decision_question="?"),
        dataset_id="ds",
        dataset_name="DS",
        rubric=Rubric(kind=rubric_kind),  # type: ignore[arg-type]
        candidates=[
            Candidate(id=e.candidate_id, label=e.label, provider_id=e.provider_id) for e in lb
        ],
        config_hash="deadbeef",
        created_at=created_at,
        mode=mode,  # type: ignore[arg-type]
        chosen_winner=chosen_winner,
    )
    return ProofReport(
        run=run,
        leaderboard=lb,
        results=[],
        cost_summary=RunCostSummary(
            candidate_cost_usd=eval_cost,
            judge_cost_usd=judge_cost,
            total_cost_usd=eval_cost + judge_cost,
        ),
    )


def test_empty_reports_yields_zero_rollup() -> None:
    roll = cost_rollup([], window="all")
    assert roll.window == "all"
    assert roll.run_count == 0
    assert (roll.eval_cost_usd, roll.judge_cost_usd, roll.total_cost_usd) == (0.0, 0.0, 0.0)
    assert roll.trend == []


def test_all_window_sums_eval_and_judge_split() -> None:
    reports = [
        _report(run_id="r1", created_at="2026-06-25T10:00:00Z", eval_cost=0.10, judge_cost=0.02),
        _report(run_id="r2", created_at="2026-06-26T10:00:00Z", eval_cost=0.30, judge_cost=0.05),
    ]
    roll = cost_rollup(reports, window="all")
    assert roll.run_count == 2
    assert round(roll.eval_cost_usd, 4) == 0.40
    assert round(roll.judge_cost_usd, 4) == 0.07
    assert round(roll.total_cost_usd, 4) == 0.47


def test_today_window_filters_by_utc_date() -> None:
    reports = [
        _report(run_id="old", created_at="2026-06-25T23:59:59Z", eval_cost=1.00, judge_cost=1.00),
        _report(run_id="today1", created_at="2026-06-27T00:00:01Z", eval_cost=0.10, judge_cost=0.01),
        _report(run_id="today2", created_at="2026-06-27T23:59:59Z", eval_cost=0.20, judge_cost=0.02),
    ]
    roll = cost_rollup(reports, window="today", today="2026-06-27")
    assert roll.run_count == 2
    assert round(roll.eval_cost_usd, 4) == 0.30
    assert round(roll.judge_cost_usd, 4) == 0.03
    assert [p.run_id for p in roll.trend] == ["today1", "today2"]


def test_trend_is_oldest_first_with_pooled_pass_rate() -> None:
    # list_runs returns newest-first; the trend must be re-sorted oldest-first for a left→right line.
    reports = [
        _report(
            run_id="newer",
            created_at="2026-06-27T12:00:00Z",
            eval_cost=0.20,
            judge_cost=0.0,
            leaderboard=[_entry("a", pass_count=5), _entry("b", pass_count=3)],  # pooled 8/10
        ),
        _report(
            run_id="older",
            created_at="2026-06-26T12:00:00Z",
            eval_cost=0.10,
            judge_cost=0.0,
            leaderboard=[_entry("a", pass_count=2)],  # pooled 2/5
        ),
    ]
    roll = cost_rollup(reports, window="all")
    assert [p.run_id for p in roll.trend] == ["older", "newer"]
    assert round(roll.trend[0].pass_rate, 4) == 0.40  # 2/5
    assert round(roll.trend[1].pass_rate, 4) == 0.80  # 8/10
    assert roll.trend[1].total_cost_usd == 0.20


def test_unscored_quick_run_without_pick_is_excluded() -> None:
    # Mirrors list_runs: a quick-compare run with no winner is an abandoned draft, not a receipt.
    reports = [
        _report(
            run_id="draft",
            created_at="2026-06-27T10:00:00Z",
            eval_cost=0.50,
            judge_cost=0.0,
            mode="quick",
            chosen_winner=None,
            rubric_kind="none",
        ),
        _report(run_id="real", created_at="2026-06-27T11:00:00Z", eval_cost=0.10, judge_cost=0.0),
    ]
    roll = cost_rollup(reports, window="all")
    assert roll.run_count == 1
    assert round(roll.total_cost_usd, 4) == 0.10
    assert [p.run_id for p in roll.trend] == ["real"]


def test_quick_run_with_a_pick_is_included() -> None:
    # A picked quick-compare run IS a receipt (the pick is the proof) — its cost counts.
    reports = [
        _report(
            run_id="picked",
            created_at="2026-06-27T10:00:00Z",
            eval_cost=0.40,
            judge_cost=0.0,
            mode="quick",
            chosen_winner="gpt",
            rubric_kind="none",
        ),
    ]
    roll = cost_rollup(reports, window="all")
    assert roll.run_count == 1
    assert round(roll.total_cost_usd, 4) == 0.40


def test_unscored_run_pass_rate_is_zero_not_a_crash() -> None:
    # A picked quick run has rubric kind "none" and an empty/unscored leaderboard pass-rate.
    reports = [
        _report(
            run_id="picked",
            created_at="2026-06-27T10:00:00Z",
            eval_cost=0.40,
            judge_cost=0.0,
            leaderboard=[_entry("gpt", pass_count=0, total=0)],
            mode="quick",
            chosen_winner="gpt",
            rubric_kind="none",
        ),
    ]
    roll = cost_rollup(reports, window="all")
    assert roll.trend[0].pass_rate == 0.0


def test_rollup_never_touches_config_hash() -> None:
    # Hash-inert proof: the rollup reads but never mutates the run's config_hash.
    reports = [
        _report(run_id="r1", created_at="2026-06-27T10:00:00Z", eval_cost=0.10, judge_cost=0.0),
    ]
    before = reports[0].run.config_hash
    cost_rollup(reports, window="all")
    cost_rollup(reports, window="today", today="2026-06-27")
    assert reports[0].run.config_hash == before == "deadbeef"
