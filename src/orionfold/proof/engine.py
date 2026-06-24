"""Matrix run engine — the heart of the proof loop (ADR-0001 §6, §8).

Runs every candidate against every example, scoring each output and capturing latency and
estimated cost into uniform :class:`ResultRow`s. Errors are recorded as failing rows (never
raised) so one bad candidate cannot abort a run. ``now`` and ``run_id`` are injected so a run
is fully deterministic and testable.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator

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
from orionfold.providers.base import safe_generate
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
            yield ResultRow(
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
                judge_cost_usd=judge_cost,
                judge_latency_ms=judge_latency,
                bench_detail=bench_detail,
                privacy=result.privacy,
                error=result.error if result.error is not None else judge_error,
            )


def run_matrix(
    dataset: Dataset, candidates: list[Candidate], rubric: Rubric
) -> list[ResultRow]:
    """Execute candidates × examples, returning one scored :class:`ResultRow` per cell."""
    return list(iter_matrix(dataset, candidates, rubric))


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
    """Run the full proof and assemble the report (run provenance + leaderboard + rows)."""
    results = run_matrix(dataset, candidates, rubric)
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
