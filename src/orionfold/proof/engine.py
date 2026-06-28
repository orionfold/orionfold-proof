"""Matrix run engine — the heart of the proof loop (ADR-0001 §6, §8).

Runs every candidate against every example, scoring each output and capturing latency and
estimated cost into uniform :class:`ResultRow`s. Errors are recorded as failing rows (never
raised) so one bad candidate cannot abort a run. ``now`` and ``run_id`` are injected so a run
is fully deterministic and testable.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor

from orionfold import __version__
from orionfold.domain.models import (
    BenchVerdict,
    Candidate,
    Dataset,
    Example,
    ProofBrief,
    ProofReport,
    ProofRun,
    ResultRow,
    Rubric,
    RunCostSummary,
)
from orionfold.proof.leaderboard import build_leaderboard
from orionfold.providers.base import Provider, safe_generate
from orionfold.providers.registry import get_provider
from orionfold.scoring.bench import score_bench
from orionfold.scoring.judge import Judge, build_judge
from orionfold.scoring.rubric import passed, score, score_keypoints

_SIMILARITY = Rubric(kind="similarity")


def _candidate_hash_fields(c: Candidate) -> dict:
    fields = {"id": c.id, "provider_id": c.provider_id, "privacy": c.privacy, "model": c.model}
    # Add system_prompt ONLY when set, so model-compare runs (None) keep byte-identical hashes.
    if c.system_prompt is not None:
        fields["system_prompt"] = c.system_prompt
    return fields


# The bench/advisory contract fields on Example (spec §3) with their defaults. Each is folded into
# the hash ONLY when it differs from its default, so every example authored before the bench kind
# existed hashes byte-identically (the mock matrix `467ddd96c9a5` invariant). The opposite — dumping
# the whole Example — would change every existing dataset's hash the moment the fields were added.
_BENCH_HASH_DEFAULTS: dict[str, object] = {
    "expected_behavior": None,
    "expected_citations": [],
    "accepted_source_ids": [],
    "requires_citation": False,
    "requires_refusal": False,
    "requires_route": False,
}


def _example_hash_fields(e: Example) -> dict:
    """Hash payload for one Example: the original tri-field shape, plus any *set* bench field.

    Preserves byte-identical hashes for all pre-bench examples (which set none of the bench
    fields) while making a bench row's per-row contract part of the run's identity.
    """
    fields: dict[str, object] = {
        "input_text": e.input_text,
        "expected_text": e.expected_text,
        "keypoints": e.keypoints,
    }
    for name, default in _BENCH_HASH_DEFAULTS.items():
        value = getattr(e, name)
        if value != default:
            fields[name] = value
    return fields


def config_hash(dataset: Dataset, candidates: list[Candidate], rubric: Rubric) -> str:
    """Stable 12-char hash of everything that defines a run's identity.

    Two runs with the same dataset, candidates, rubric, and app version produce the same
    hash — that is what makes the receipt *repeatable* and lets users prove provenance.
    """
    payload = {
        "version": __version__,
        "dataset": {
            # corpus_id is intentionally excluded — corpus identity is receipt provenance, not a
            # hash input (else every dataset's hash would move). Examples use the conditional
            # bench-field projection so pre-bench examples hash byte-identically.
            "id": dataset.id,
            "examples": [_example_hash_fields(e) for e in dataset.examples],
        },
        "candidates": [
            _candidate_hash_fields(c)
            for c in candidates
        ],
        "rubric": rubric.model_dump(),
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def score_cell(
    candidate: Candidate,
    provider: Provider,
    example: Example,
    index: int,
    rubric: Rubric,
    judge: Judge | None,
) -> ResultRow:
    """Generate + score ONE (candidate, example) cell into a :class:`ResultRow`.

    Pure function of its inputs (no shared mutable state) — this is what makes candidates safe to
    run concurrently: two cells never touch each other's data, and scoring is deterministic, so the
    cell's outcome is independent of the order cells complete in. ``judge`` is pre-built once per run
    (judge rubrics) and read-only here. The ``provider`` is resolved once per candidate by the caller.
    """
    result = safe_generate(provider, example, candidate)
    judge_cost, judge_latency, judge_error = 0.0, 0, None
    bench_detail: BenchVerdict | None = None
    score_value: float | None
    did_pass: bool | None
    if rubric.kind == "none":
        # Unscored quick-compare: capture output + metrics, never a score.
        score_value, did_pass = None, None
    elif result.error is not None:
        score_value, did_pass = 0.0, False
    elif rubric.kind == "bench":
        # Deterministic governance scoring — reads the EXAMPLE's per-row contract, never
        # expected_text, and has no threshold. score is the binary verdict (1.0/0.0).
        bench_detail = score_bench(
            result.output_text,
            expected_behavior=example.expected_behavior,
            expected_citations=example.expected_citations,
            accepted_source_ids=example.accepted_source_ids,
            prompt_text=example.input_text,
        )
        score_value = 1.0 if bench_detail.passed else 0.0
        did_pass = bench_detail.passed
    elif rubric.kind == "keypoint":
        score_value = (
            score_keypoints(example.keypoints, result.output_text, rubric)
            if example.keypoints
            else score(example.expected_text, result.output_text, _SIMILARITY)
        )
        did_pass = passed(score_value, rubric)
    elif rubric.kind == "judge":
        assert judge is not None
        outcome = judge.score(example.expected_text, result.output_text)
        score_value = outcome.score
        judge_cost, judge_latency, judge_error = (
            outcome.cost_usd, outcome.latency_ms, outcome.error
        )
        did_pass = judge_error is None and passed(score_value, rubric)
    else:
        score_value = score(example.expected_text, result.output_text, rubric)
        did_pass = passed(score_value, rubric)
    return ResultRow(
        candidate_id=candidate.id,
        example_index=index,
        input_text=example.input_text,
        expected_text=example.expected_text,
        output_text=result.output_text,
        score=score_value,
        passed=did_pass,
        latency_ms=result.latency_ms,
        estimated_cost_usd=result.estimated_cost_usd,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        warm_decode_ms=result.warm_decode_ms,
        judge_cost_usd=judge_cost,
        judge_latency_ms=judge_latency,
        bench_detail=bench_detail,
        privacy=result.privacy,
        error=result.error if result.error is not None else judge_error,
    )


def iter_matrix(
    dataset: Dataset, candidates: list[Candidate], rubric: Rubric
) -> Iterator[ResultRow]:
    """Yield one scored :class:`ResultRow` per cell as it completes.

    Iterating candidate-major (each candidate's examples in order) makes a consumer's running
    count a faithful position in the matrix — the basis for streamed progress (ADR-0003). The
    cell logic is identical to a batch run; only the shape (generator vs. list) differs.
    """
    judge: Judge | None = build_judge(rubric) if rubric.kind == "judge" else None
    for candidate in candidates:
        provider = get_provider(candidate.provider_id)
        for index, example in enumerate(dataset.examples):
            yield score_cell(candidate, provider, example, index, rubric, judge)


def run_matrix(
    dataset: Dataset, candidates: list[Candidate], rubric: Rubric
) -> list[ResultRow]:
    """Execute candidates × examples, returning one scored :class:`ResultRow` per cell."""
    return list(iter_matrix(dataset, candidates, rubric))


# Bound on concurrent cloud candidates — a courteous cap, not a per-provider rate limiter (see
# the `timeout-and-retry-policy` backlog item for that). Local candidates serialize regardless.
_MAX_CLOUD_WORKERS = 8


def run_matrix_concurrent(
    dataset: Dataset,
    candidates: list[Candidate],
    rubric: Rubric,
    *,
    on_cell: Callable[[ResultRow], None] | None = None,
    cancel: threading.Event | None = None,
) -> list[ResultRow]:
    """Run candidates CONCURRENTLY, returning rows in input-candidate order.

    Candidates are independent — each scores the same frozen examples in isolation with deterministic
    scoring — so the only thing concurrency changes is *when* cells finish, never *what* they score.
    The returned list is reassembled candidate-major (input order), so it is byte-identical to
    :func:`run_matrix`; the leaderboard groups by candidate id and ``config_hash`` ignores row order,
    so nothing downstream can observe the difference.

    Policy (operator decision): **cloud candidates run in parallel** (bounded by
    ``_MAX_CLOUD_WORKERS``); **local candidates serialize** through one shared lock so two local
    models never fight over the same GPU / unified memory (one resident at a time). A run mixing both
    overlaps its cloud work with its (serialized) local work.

    ``on_cell`` is invoked once per completed cell, from a worker thread, as soon as that cell scores
    — the hook the live progress stream drains. It must be thread-safe; cells complete out of order.

    When ``cancel`` is set, each candidate stops after the current example — an in-flight
    ``score_cell`` always finishes (no torn provider call), then no further examples start. ``cancel``
    is runtime-only and never part of run identity, so it cannot affect ``config_hash``.
    """
    judge: Judge | None = build_judge(rubric) if rubric.kind == "judge" else None
    local_lock = threading.Lock()
    # Each candidate gets its own result slot so the final concat is deterministic input order,
    # regardless of which candidate finishes first.
    per_candidate: list[list[ResultRow]] = [[] for _ in candidates]

    def run_candidate(slot: int, candidate: Candidate) -> None:
        provider = get_provider(candidate.provider_id)
        rows = per_candidate[slot]
        # Serialize local candidates against each other; cloud candidates never take the lock.
        lock = local_lock if candidate.privacy == "local" else _NULL_LOCK
        with lock:
            for index, example in enumerate(dataset.examples):
                row = score_cell(candidate, provider, example, index, rubric, judge)
                rows.append(row)
                if on_cell is not None:
                    on_cell(row)
                if cancel is not None and cancel.is_set():
                    return

    # A single candidate (the common headless/CLI case) needs no pool — run inline.
    if len(candidates) <= 1:
        for slot, candidate in enumerate(candidates):
            run_candidate(slot, candidate)
    else:
        workers = min(_MAX_CLOUD_WORKERS, len(candidates))
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="proof-cand") as pool:
            futures = [pool.submit(run_candidate, slot, c) for slot, c in enumerate(candidates)]
            for future in futures:
                future.result()  # re-raise any unexpected error (safe_generate already traps provider errors)

    return [row for rows in per_candidate for row in rows]


class _NullLock:
    """A no-op context manager — cloud candidates take this instead of the local lock."""

    def __enter__(self) -> None:
        return None

    def __exit__(self, *exc: object) -> None:
        return None


_NULL_LOCK = _NullLock()


def build_cost_summary(rows: list[ResultRow]) -> RunCostSummary:
    """Roll per-row costs up into the full run cost picture (candidate + judge + total)."""
    candidate = sum(r.estimated_cost_usd for r in rows)
    judge = sum(r.judge_cost_usd for r in rows)
    return RunCostSummary(
        candidate_cost_usd=candidate, judge_cost_usd=judge, total_cost_usd=candidate + judge
    )


def run_proof(
    *,
    run_id: str,
    created_at: str,
    brief: ProofBrief,
    dataset: Dataset,
    candidates: list[Candidate],
    rubric: Rubric,
) -> ProofReport:
    """Run the full proof and assemble the report (run provenance + leaderboard + rows).

    Candidates run concurrently (cloud parallel, local serialized) — see
    :func:`run_matrix_concurrent`. Rows come back in input-candidate order, so the assembled report
    is byte-identical to a sequential run; only the wall-clock differs.
    """
    results = run_matrix_concurrent(dataset, candidates, rubric)
    leaderboard = build_leaderboard(candidates, results)
    run = ProofRun(
        id=run_id,
        brief=brief,
        dataset_id=dataset.id,
        dataset_name=dataset.name,
        rubric=rubric,
        candidates=candidates,
        config_hash=config_hash(dataset, candidates, rubric),
        created_at=created_at,
    )
    cost_summary = build_cost_summary(results)
    return ProofReport(run=run, leaderboard=leaderboard, results=results, cost_summary=cost_summary)
