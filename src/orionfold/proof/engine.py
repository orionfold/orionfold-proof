"""Matrix run engine — the heart of the proof loop (ADR-0001 §6, §8).

Runs every candidate against every example, scoring each output and capturing latency and
estimated cost into uniform :class:`ResultRow`s. Errors are recorded as failing rows (never
raised) so one bad candidate cannot abort a run. ``now`` and ``run_id`` are injected so a run
is fully deterministic and testable.
"""

from __future__ import annotations

import hashlib
import json

from orionfold import __version__
from orionfold.domain.models import (
    Candidate,
    Dataset,
    ProofBrief,
    ProofReport,
    ProofRun,
    ResultRow,
    Rubric,
)
from orionfold.proof.leaderboard import build_leaderboard
from orionfold.providers.base import safe_generate
from orionfold.providers.registry import get_provider
from orionfold.scoring.rubric import passed, score


def config_hash(dataset: Dataset, candidates: list[Candidate], rubric: Rubric) -> str:
    """Stable 12-char hash of everything that defines a run's identity.

    Two runs with the same dataset, candidates, rubric, and app version produce the same
    hash — that is what makes the receipt *repeatable* and lets users prove provenance.
    """
    payload = {
        "version": __version__,
        "dataset": {
            "id": dataset.id,
            "examples": [e.model_dump() for e in dataset.examples],
        },
        "candidates": [
            {"id": c.id, "provider_id": c.provider_id, "privacy": c.privacy}
            for c in candidates
        ],
        "rubric": rubric.model_dump(),
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def run_matrix(
    dataset: Dataset, candidates: list[Candidate], rubric: Rubric
) -> list[ResultRow]:
    """Execute candidates × examples, returning one scored :class:`ResultRow` per cell."""
    rows: list[ResultRow] = []
    for candidate in candidates:
        provider = get_provider(candidate.provider_id)
        for index, example in enumerate(dataset.examples):
            result = safe_generate(provider, example, candidate)
            if result.error is not None:
                score_value, did_pass = 0.0, False
            else:
                score_value = score(example.expected_text, result.output_text, rubric)
                did_pass = passed(score_value, rubric)
            rows.append(
                ResultRow(
                    candidate_id=candidate.id,
                    example_index=index,
                    input_text=example.input_text,
                    expected_text=example.expected_text,
                    output_text=result.output_text,
                    score=score_value,
                    passed=did_pass,
                    latency_ms=result.latency_ms,
                    estimated_cost_usd=result.estimated_cost_usd,
                    privacy=result.privacy,
                    error=result.error,
                )
            )
    return rows


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
    return ProofReport(run=run, leaderboard=leaderboard, results=results)
