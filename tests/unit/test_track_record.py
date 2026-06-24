"""``track_record`` — the cross-run rollup core function (ADR-0004 §5).

Comparability rule: runs group by (dataset_id, rubric.kind). The rollup reads existing
LeaderboardEntry/ProofRun fields only — it re-runs no scoring, so it can never touch
``config_hash``.
"""

from __future__ import annotations

from orionfold.domain.models import (
    Candidate,
    LeaderboardEntry,
    ProofBrief,
    ProofReport,
    ProofRun,
    Rubric,
)
from orionfold.proof import track_record


def _entry(
    candidate_id: str,
    *,
    pass_count: int,
    total: int = 5,
    cost: float = 0.01,
    recommended: bool = False,
    label: str | None = None,
) -> LeaderboardEntry:
    return LeaderboardEntry(
        candidate_id=candidate_id,
        label=label or candidate_id,
        provider_id="mock",
        privacy="local",
        model=None,
        total=total,
        pass_count=pass_count,
        pass_rate=pass_count / total if total else 0.0,
        avg_score=pass_count / total if total else 0.0,
        avg_latency_ms=10,
        total_estimated_cost_usd=cost,
        failure_count=total - pass_count,
        error_count=0,
        recommended=recommended,
    )


def _report(
    *,
    run_id: str,
    dataset_id: str,
    dataset_name: str,
    rubric_kind: str,
    leaderboard: list[LeaderboardEntry],
    mode: str = "full",
    created_at: str = "2026-06-23T12:00:00Z",
) -> ProofReport:
    rubric = Rubric(kind=rubric_kind)  # type: ignore[arg-type]
    run = ProofRun(
        id=run_id,
        brief=ProofBrief(task_name=dataset_name, decision_question="?"),
        dataset_id=dataset_id,
        dataset_name=dataset_name,
        rubric=rubric,
        candidates=[
            Candidate(id=e.candidate_id, label=e.label, provider_id=e.provider_id)
            for e in leaderboard
        ],
        config_hash="deadbeef",
        created_at=created_at,
        mode=mode,  # type: ignore[arg-type]
    )
    return ProofReport(run=run, leaderboard=leaderboard, results=[])


def test_empty_reports_yields_no_groups() -> None:
    assert track_record([]) == []


def test_single_run_one_group() -> None:
    report = _report(
        run_id="run_1",
        dataset_id="triage",
        dataset_name="Triage",
        rubric_kind="exact",
        leaderboard=[
            _entry("gpt", pass_count=5, recommended=True),
            _entry("haiku", pass_count=4),
        ],
    )
    groups = track_record([report])
    assert len(groups) == 1
    g = groups[0]
    assert (g.dataset_id, g.rubric_kind, g.runs) == ("triage", "exact", 1)
    # Best aggregate pass-rate first.
    assert [e.candidate_id for e in g.entries] == ["gpt", "haiku"]
    gpt = g.entries[0]
    assert gpt.runs == 1
    assert (gpt.total_examples, gpt.total_passes) == (5, 5)
    assert gpt.pass_rate == 1.0
    assert gpt.times_recommended == 1
    assert g.entries[1].times_recommended == 0


def test_two_runs_same_dataset_and_kind_aggregate() -> None:
    r1 = _report(
        run_id="run_1",
        dataset_id="triage",
        dataset_name="Triage",
        rubric_kind="exact",
        leaderboard=[_entry("gpt", pass_count=4, cost=0.02, recommended=True)],
    )
    r2 = _report(
        run_id="run_2",
        dataset_id="triage",
        dataset_name="Triage",
        rubric_kind="exact",
        leaderboard=[_entry("gpt", pass_count=5, cost=0.04, recommended=True)],
    )
    groups = track_record([r1, r2])
    assert len(groups) == 1
    g = groups[0]
    assert g.runs == 2
    gpt = g.entries[0]
    assert gpt.runs == 2
    # Pass-rate is pooled over examples, not a mean of per-run rates: (4+5)/(5+5).
    assert gpt.total_examples == 10
    assert gpt.total_passes == 9
    assert gpt.pass_rate == 0.9
    # avg_cost is the mean per-run cost: (0.02 + 0.04) / 2.
    assert abs(gpt.avg_cost_usd - 0.03) < 1e-9
    assert gpt.times_recommended == 2


def test_same_dataset_different_kind_are_separate_groups() -> None:
    exact = _report(
        run_id="run_1",
        dataset_id="triage",
        dataset_name="Triage",
        rubric_kind="exact",
        leaderboard=[_entry("gpt", pass_count=5)],
    )
    similarity = _report(
        run_id="run_2",
        dataset_id="triage",
        dataset_name="Triage",
        rubric_kind="similarity",
        leaderboard=[_entry("gpt", pass_count=3)],
    )
    groups = track_record([exact, similarity])
    # Same dataset, two rubric kinds → two groups; never pooled.
    assert len(groups) == 2
    kinds = {g.rubric_kind for g in groups}
    assert kinds == {"exact", "similarity"}


def test_quick_runs_are_excluded() -> None:
    quick = _report(
        run_id="run_q",
        dataset_id="adhoc",
        dataset_name="Quick",
        rubric_kind="none",
        leaderboard=[_entry("gpt", pass_count=0, total=0)],
        mode="quick",
    )
    full = _report(
        run_id="run_f",
        dataset_id="triage",
        dataset_name="Triage",
        rubric_kind="exact",
        leaderboard=[_entry("gpt", pass_count=5)],
    )
    groups = track_record([quick, full])
    # Only the full run contributes — quick runs are unscored, nothing to roll up.
    assert len(groups) == 1
    assert groups[0].dataset_id == "triage"


def test_candidate_in_only_some_runs_counts_its_runs() -> None:
    r1 = _report(
        run_id="run_1",
        dataset_id="triage",
        dataset_name="Triage",
        rubric_kind="exact",
        leaderboard=[_entry("gpt", pass_count=5), _entry("haiku", pass_count=4)],
    )
    r2 = _report(
        run_id="run_2",
        dataset_id="triage",
        dataset_name="Triage",
        rubric_kind="exact",
        leaderboard=[_entry("gpt", pass_count=3)],  # haiku absent here
    )
    g = track_record([r1, r2])[0]
    by_id = {e.candidate_id: e for e in g.entries}
    assert by_id["gpt"].runs == 2
    assert by_id["haiku"].runs == 1
    assert by_id["haiku"].total_examples == 5


def test_dataset_filter_narrows_groups() -> None:
    a = _report(
        run_id="run_a",
        dataset_id="triage",
        dataset_name="Triage",
        rubric_kind="exact",
        leaderboard=[_entry("gpt", pass_count=5)],
    )
    b = _report(
        run_id="run_b",
        dataset_id="extraction",
        dataset_name="Extraction",
        rubric_kind="contains",
        leaderboard=[_entry("gpt", pass_count=4)],
    )
    groups = track_record([a, b], dataset_id="triage")
    assert len(groups) == 1
    assert groups[0].dataset_id == "triage"


def test_groups_ordered_by_dataset_then_kind() -> None:
    # Build out of order; expect a stable (dataset_name, rubric_kind) sort.
    reports = [
        _report(
            run_id="r3",
            dataset_id="b",
            dataset_name="Beta",
            rubric_kind="similarity",
            leaderboard=[_entry("gpt", pass_count=1)],
        ),
        _report(
            run_id="r1",
            dataset_id="a",
            dataset_name="Alpha",
            rubric_kind="exact",
            leaderboard=[_entry("gpt", pass_count=1)],
        ),
        _report(
            run_id="r2",
            dataset_id="a",
            dataset_name="Alpha",
            rubric_kind="contains",
            leaderboard=[_entry("gpt", pass_count=1)],
        ),
    ]
    groups = track_record(reports)
    assert [(g.dataset_name, g.rubric_kind) for g in groups] == [
        ("Alpha", "contains"),
        ("Alpha", "exact"),
        ("Beta", "similarity"),
    ]
