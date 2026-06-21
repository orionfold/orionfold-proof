"""LLM-as-judge seam — meaning-aware scoring for the ``judge`` rubric (deferred from v0).

The judge reuses the provider boundary: a real judge builds a grading prompt, calls the model
through ``safe_generate`` (inheriting cost estimation AND secret redaction), and parses a single
number. ``MockJudge`` is the keyless, deterministic judge that keeps the suite reproducible.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Protocol

from orionfold.domain.models import Candidate, Example, Rubric
from orionfold.providers.base import Provider, safe_generate
from orionfold.providers.registry import get_provider

_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


@dataclass
class JudgeOutcome:
    score: float
    cost_usd: float
    latency_ms: int
    error: str | None = None


def parse_score(text: str) -> float | None:
    """First number in ``text`` as a 0..1 score. Accepts 0..1, 0..10, or 0..100; clamps."""
    m = _NUMBER.search(text or "")
    if m is None:
        return None
    value = float(m.group())
    if value > 10:        # looks like 0..100
        value /= 100.0
    elif value > 2:       # looks like 0..10 (2+ is clearly not 0..1)
        value /= 10.0
    return max(0.0, min(1.0, value))


def grading_prompt(expected: str, output: str) -> str:
    return (
        "You are grading how well a candidate answer captures the MEANING of a reference "
        "answer, ignoring wording and format. Reply with ONLY a number from 0 to 1.\n\n"
        f"Reference answer:\n{expected}\n\n"
        f"Candidate answer:\n{output}\n\n"
        "Score (0 to 1):"
    )


class Judge(Protocol):
    def score(self, expected: str, output: str) -> JudgeOutcome: ...


class MockJudge:
    """Deterministic keyless judge: difflib ratio with a fixed nominal cost."""

    def score(self, expected: str, output: str) -> JudgeOutcome:
        ratio = SequenceMatcher(None, expected, output).ratio()
        return JudgeOutcome(score=ratio, cost_usd=0.0001, latency_ms=5, error=None)


class LLMJudge:
    def __init__(self, provider: Provider, model: str | None) -> None:
        self._provider = provider
        self._model = model

    def score(self, expected: str, output: str) -> JudgeOutcome:
        example = Example(input_text=grading_prompt(expected, output), expected_text="")
        candidate = Candidate(
            id="judge", label="judge", provider_id=self._provider.id, model=self._model
        )
        result = safe_generate(self._provider, example, candidate)
        if result.error is not None:
            return JudgeOutcome(0.0, result.estimated_cost_usd, result.latency_ms, result.error)
        value = parse_score(result.output_text)
        if value is None:
            return JudgeOutcome(
                0.0, result.estimated_cost_usd, result.latency_ms,
                "judge returned an unparseable score",
            )
        return JudgeOutcome(value, result.estimated_cost_usd, result.latency_ms, None)


def build_judge(rubric: Rubric) -> Judge:
    """Resolve the judge for a rubric. ``mock_judge`` is keyless; others resolve via the registry."""
    if not rubric.judge_provider_id:
        raise ValueError("judge rubric requires judge_provider_id")
    if rubric.judge_provider_id == "mock_judge":
        return MockJudge()
    return LLMJudge(get_provider(rubric.judge_provider_id), rubric.judge_model)
