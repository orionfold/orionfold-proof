"""Leaderboard aggregation — turn the result matrix into a ranked standing per candidate.

The ordering encodes the product's recommendation: trust the candidate that passes most
often, breaking ties toward lower latency then lower cost. The top entry is marked
``recommended`` only when it passed at least one example, so the receipt never crowns a
candidate that produced nothing.

The standing also carries ``cost_per_quality`` (cost per quality point) for presentation;
it does not affect ranking.
"""

from __future__ import annotations

from orionfold.domain.models import (
    Candidate,
    LeaderboardEntry,
    Privacy,
    ProofReport,
    ResultRow,
    TrackRecordEntry,
    TrackRecordGroup,
)


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
        error_count = sum(1 for r in rows if r.error is not None)
        avg_score = sum((r.score or 0.0) for r in rows) / total if total else 0.0
        avg_latency = round(sum(r.latency_ms for r in rows) / total) if total else 0
        total_cost = sum(r.estimated_cost_usd for r in rows)
        cost_per_quality = total_cost / avg_score if avg_score > 0 else None
        entries.append(
            LeaderboardEntry(
                candidate_id=cand.id,
                label=cand.label,
                provider_id=cand.provider_id,
                privacy=cand.privacy,
                model=cand.model,
                system_prompt=cand.system_prompt,
                total=total,
                pass_count=pass_count,
                pass_rate=pass_count / total if total else 0.0,
                avg_score=avg_score,
                avg_latency_ms=avg_latency,
                total_estimated_cost_usd=total_cost,
                failure_count=failure_count,
                error_count=error_count,
                cost_per_quality=cost_per_quality,
            )
        )

    # Best first: a candidate that produced any real output always outranks a fully-errored
    # one (which reports 0ms/$0.00 and would otherwise win the latency/cost tiebreak); then
    # highest pass rate, then highest avg score, then lowest latency, then lowest cost.
    def _all_errored(e: LeaderboardEntry) -> bool:
        return e.total > 0 and e.error_count == e.total

    entries.sort(
        key=lambda e: (
            _all_errored(e),
            -e.pass_rate,
            -e.avg_score,
            e.avg_latency_ms,
            e.total_estimated_cost_usd,
        )
    )
    # Only crown a winner that actually passed at least one example — never recommend a
    # candidate that produced nothing.
    if entries and entries[0].pass_count > 0:
        entries[0].recommended = True
    return entries


def track_record(
    reports: list[ProofReport], *, dataset_id: str | None = None
) -> list[TrackRecordGroup]:
    """Roll up many runs into per-candidate standings, one group per comparable slice.

    Comparability rule (ADR-0004 §5): runs group by ``(dataset_id, rubric.kind)`` — only runs
    over the same dataset scored the same way roll up together. Quick-compare runs are
    excluded (rubric kind ``"none"`` is unscored — nothing to aggregate), mirroring how the
    leaderboard and ``list_runs`` treat them.

    Pure: reads existing ``LeaderboardEntry``/``ProofRun`` fields, re-runs no scoring, opens
    no connection. Pass-rate is pooled over examples (Σpasses / Σexamples), not a mean of
    per-run rates, so a 100-example run outweighs a 5-example one. ``avg_cost_usd`` is the
    mean per-run cost. Optional ``dataset_id`` narrows to a single dataset.
    """
    # Accumulate per (dataset_id, rubric_kind) → per candidate_id, preserving the candidate's
    # display fields from its most recent leaderboard entry.
    groups: dict[tuple[str, str], _GroupAcc] = {}
    for report in reports:
        run = report.run
        if run.mode == "quick" or run.rubric.kind == "none":
            continue  # unscored — no pass-rate to roll up
        if dataset_id is not None and run.dataset_id != dataset_id:
            continue
        key = (run.dataset_id, run.rubric.kind)
        acc = groups.get(key)
        if acc is None:
            acc = _GroupAcc(dataset_id=run.dataset_id, dataset_name=run.dataset_name)
            groups[key] = acc
        acc.run_ids.add(run.id)
        for entry in report.leaderboard:
            acc.add(entry)

    out: list[TrackRecordGroup] = []
    for (ds_id, kind), acc in groups.items():
        entries = [c.finalize() for c in acc.candidates.values()]
        # Best aggregate pass-rate first; stable tiebreak on candidate_id for determinism.
        entries.sort(key=lambda e: (-e.pass_rate, e.candidate_id))
        out.append(
            TrackRecordGroup(
                dataset_id=ds_id,
                dataset_name=acc.dataset_name,
                rubric_kind=kind,  # type: ignore[arg-type]
                runs=len(acc.run_ids),
                entries=entries,
            )
        )
    # Stable, readable order: by dataset name, then rubric kind.
    out.sort(key=lambda g: (g.dataset_name, g.rubric_kind))
    return out


class _CandidateAcc:
    """Mutable accumulator for one candidate across a group's runs."""

    def __init__(self, entry: LeaderboardEntry) -> None:
        self.candidate_id = entry.candidate_id
        self.label = entry.label
        self.provider_id = entry.provider_id
        self.privacy: Privacy = entry.privacy
        self.model = entry.model
        self.runs = 0
        self.total_examples = 0
        self.total_passes = 0
        self.cost_sum = 0.0
        self.times_recommended = 0

    def add(self, entry: LeaderboardEntry) -> None:
        # Keep the latest display fields (a candidate's label/model could differ run to run).
        self.label = entry.label
        self.model = entry.model
        self.runs += 1
        self.total_examples += entry.total
        self.total_passes += entry.pass_count
        self.cost_sum += entry.total_estimated_cost_usd
        if entry.recommended:
            self.times_recommended += 1

    def finalize(self) -> TrackRecordEntry:
        return TrackRecordEntry(
            candidate_id=self.candidate_id,
            label=self.label,
            provider_id=self.provider_id,
            privacy=self.privacy,
            model=self.model,
            runs=self.runs,
            total_examples=self.total_examples,
            total_passes=self.total_passes,
            pass_rate=(self.total_passes / self.total_examples) if self.total_examples else 0.0,
            avg_cost_usd=(self.cost_sum / self.runs) if self.runs else 0.0,
            times_recommended=self.times_recommended,
        )


class _GroupAcc:
    """Mutable accumulator for one (dataset, rubric kind) group."""

    def __init__(self, dataset_id: str, dataset_name: str) -> None:
        self.dataset_id = dataset_id
        self.dataset_name = dataset_name
        self.run_ids: set[str] = set()
        self.candidates: dict[str, _CandidateAcc] = {}

    def add(self, entry: LeaderboardEntry) -> None:
        acc = self.candidates.get(entry.candidate_id)
        if acc is None:
            acc = _CandidateAcc(entry)
            self.candidates[entry.candidate_id] = acc
        acc.add(entry)
