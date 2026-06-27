"""Cumulative cost rollup — a read-only aggregate over stored runs (Arena-shape redesign Slice 3).

The telemetry rail's "Cost today (eval + judge split)" and "Cost to date" cells, plus the
Receipts trend tiles, all read from one rollup over persisted :class:`RunCostSummary` fields.

Pure and hash-inert, exactly like :func:`orionfold.proof.leaderboard.track_record`: reads
existing ``cost_summary`` / ``leaderboard`` / ``created_at`` fields, re-runs no scoring, opens
no connection, and so can never touch ``config_hash`` or a receipt byte. The same draft-filter
as ``list_runs`` applies — an un-picked quick-compare run is an abandoned draft, not a receipt,
and its (unconfirmed) spend does not count.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from orionfold.domain.models import CostRollup, CostTrendPoint, ProofReport

Window = Literal["today", "all"]


def _utc_today() -> str:
    """Current UTC calendar date as ``YYYY-MM-DD`` — the prefix of an ISO-8601 ``created_at``."""
    return datetime.now(timezone.utc).date().isoformat()


def _pooled_pass_rate(report: ProofReport) -> float:
    """Σpasses / Σexamples across the run's leaderboard — pooled, not a mean of per-row rates.

    0.0 when nothing was scored (an unscored quick-compare run), mirroring ``track_record``.
    """
    total = sum(e.total for e in report.leaderboard)
    if total == 0:
        return 0.0
    passes = sum(e.pass_count for e in report.leaderboard)
    return passes / total


def _is_receipt(report: ProofReport) -> bool:
    """A run that counts as a finished receipt — same rule as ``list_runs``.

    A quick-compare run with no recorded pick is an abandoned draft; its spend is unconfirmed
    and excluded so the rail's cost never inflates from drafts the operator never committed to.
    """
    run = report.run
    return not (run.mode == "quick" and run.chosen_winner is None)


def cost_rollup(
    reports: list[ProofReport], *, window: Window, today: str | None = None
) -> CostRollup:
    """Roll persisted per-run costs up into a windowed eval/judge split + a trend series.

    ``window="today"`` keeps runs whose ``created_at`` falls on the current UTC date (override
    via ``today`` for deterministic tests); ``window="all"`` keeps every stored run. Drafts
    (un-picked quick-compare runs) are excluded. The ``trend`` is sorted oldest-first so a
    Recharts line reads left→right, independent of the newest-first order ``list_runs`` returns.
    """
    cutoff = (today or _utc_today()) if window == "today" else None

    kept: list[ProofReport] = []
    for report in reports:
        if not _is_receipt(report):
            continue
        if cutoff is not None and not report.run.created_at.startswith(cutoff):
            continue
        kept.append(report)

    eval_cost = sum(r.cost_summary.candidate_cost_usd for r in kept)
    judge_cost = sum(r.cost_summary.judge_cost_usd for r in kept)

    # Oldest-first for a left→right trend line; stable tiebreak on run id for determinism.
    trend = [
        CostTrendPoint(
            run_id=r.run.id,
            created_at=r.run.created_at,
            total_cost_usd=r.cost_summary.total_cost_usd,
            pass_rate=_pooled_pass_rate(r),
        )
        for r in sorted(kept, key=lambda r: (r.run.created_at, r.run.id))
    ]

    return CostRollup(
        window=window,
        run_count=len(kept),
        eval_cost_usd=eval_cost,
        judge_cost_usd=judge_cost,
        total_cost_usd=eval_cost + judge_cost,
        trend=trend,
    )
