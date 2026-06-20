"""Leaderboard aggregation — turn the result matrix into a ranked standing per candidate.

The ordering encodes the product's recommendation: trust the candidate that passes most
often, breaking ties toward lower latency then lower cost. The top entry is marked
``recommended`` so the receipt can state a clear, defensible choice.
"""

from __future__ import annotations

from orionfold.domain.models import Candidate, LeaderboardEntry, ResultRow


def build_leaderboard(
    candidates: list[Candidate], results: list[ResultRow]
) -> list[LeaderboardEntry]:
    """Aggregate ``results`` per candidate and rank them; mark the top as recommended."""
    by_candidate: dict[str, list[ResultRow]] = {c.id: [] for c in candidates}
    for row in results:
        by_candidate.setdefault(row.candidate_id, []).append(row)

    entries: list[LeaderboardEntry] = []
    for cand in candidates:
        rows = by_candidate.get(cand.id, [])
        total = len(rows)
        pass_count = sum(1 for r in rows if r.passed)
        failure_count = total - pass_count
        avg_score = sum(r.score for r in rows) / total if total else 0.0
        avg_latency = round(sum(r.latency_ms for r in rows) / total) if total else 0
        total_cost = sum(r.estimated_cost_usd for r in rows)
        entries.append(
            LeaderboardEntry(
                candidate_id=cand.id,
                label=cand.label,
                provider_id=cand.provider_id,
                privacy=cand.privacy,
                total=total,
                pass_count=pass_count,
                pass_rate=pass_count / total if total else 0.0,
                avg_score=avg_score,
                avg_latency_ms=avg_latency,
                total_estimated_cost_usd=total_cost,
                failure_count=failure_count,
            )
        )

    # Best first: highest pass rate, then lowest latency, then lowest cost.
    entries.sort(key=lambda e: (-e.pass_rate, e.avg_latency_ms, e.total_estimated_cost_usd))
    if entries:
        entries[0].recommended = True
    return entries
