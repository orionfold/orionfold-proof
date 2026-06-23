"""Deterministic, keyless mock providers — the default proof path (ADR-0001 §6, §8).

These let the whole loop run with no network and no API keys, which is what makes the test
suite reproducible and the first-run experience instant. ``mock_good`` returns the expected
answer; ``mock_bad`` returns a generic answer and deterministically errors on a subset of
inputs so the run always exercises the error path and produces a real failure case.
"""

from __future__ import annotations

import hashlib
from math import ceil

from orionfold.domain.models import Candidate, Example, Privacy, ProviderResult

# A plausible-but-wrong generic answer, so mock_bad scores poorly on real summaries.
_GENERIC_ANSWER = "This document discusses various financial topics and market conditions."


def _stable_int(text: str) -> int:
    """Process-independent hash (Python's ``hash`` is salted; sha256 is reproducible)."""
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:4], "big")


def _tokens(text: str) -> int:
    return len(text.split())


# Concise-instruction cues → a verbosity budget (fraction of words kept). The mocks are
# deterministic simulations: a prompt that asks for brevity drops trailing content (and so
# trailing keypoints), giving the keyless prompt-compare demo a real, explainable signal.
# Strong cues truncate harder than mild ones; the strongest (smallest budget) present wins.
_STRONG_CUES = ("as few words as possible", "fewest", "terse", "one sentence", "tl;dr")
_MILD_CUES = ("concise", "brief", "short", "minimal")


def _shape_for_prompt(base: str, system_prompt: str | None) -> str:
    """Shape a mock's base output by concise cues in ``system_prompt``.

    Returns ``base`` UNCHANGED (same object) when there is no system prompt or no recognized
    cue — the model-compare path stays byte-identical. A concise cue truncates to a prefix.
    """
    if system_prompt is None:
        return base
    prompt = system_prompt.lower()
    budget = 1.0
    if any(cue in prompt for cue in _STRONG_CUES):
        budget = 0.4
    elif any(cue in prompt for cue in _MILD_CUES):
        budget = 0.6
    if budget >= 1.0:
        return base
    words = base.split()
    keep = max(1, ceil(budget * len(words)))
    return " ".join(words[:keep])


# Quick-compare has no expected answer, so `mock_good` synthesizes a plausible "good" output
# FROM the pasted prompt instead. This keeps the keyless head-to-head a clear good-vs-bad.
_CONDENSE_WORD_BUDGET = 28


def _condense(text: str) -> str:
    """A deterministic, on-topic 'summary' of an ad-hoc prompt (no expected answer exists).

    Strips a leading instruction clause ("Summarize this …: <body>") so the takeaway is the
    substantive content, then keeps the leading sentence — capped to a tidy word budget and
    trimmed at a word boundary — so it reads like a concise summary, not the prompt echoed back.
    """
    core = text.strip()
    # Drop an instruction lead only on a colon-space with a multi-word head, so ratios/times
    # ("3:1", "9:30") and one-word labels ("Note:") are left intact.
    prefix, sep, rest = core.partition(": ")
    if sep and len(prefix) <= 60 and len(prefix.split()) >= 2 and rest.strip():
        core = rest.strip()
    words = core.split()
    if not words:
        return core
    budget = min(len(words), _CONDENSE_WORD_BUDGET)
    kept = words[:budget]
    truncated = budget < len(words)
    # Prefer ending on the first complete sentence within the budget.
    for i, word in enumerate(kept):
        if word.endswith((".", "!", "?")):
            kept = kept[: i + 1]
            truncated = False
            break
    out = " ".join(kept)
    return out + "…" if truncated else out


class MockGoodProvider:
    """A strong candidate: returns the expected text with deterministic local latency."""

    id: str = "mock_good"
    label: str = "Mock · good"
    privacy: Privacy = "local"

    def generate(self, example: Example, candidate: Candidate) -> ProviderResult:
        # Scored runs echo the expected answer; the keyless quick path (no expected) gets a
        # condensed, on-topic summary of the prompt so the candidate never renders blank.
        base = example.expected_text or _condense(example.input_text)
        output = _shape_for_prompt(base, candidate.system_prompt)
        latency = 40 + _stable_int(example.input_text) % 40
        return ProviderResult(
            output_text=output,
            latency_ms=latency,
            input_tokens=_tokens(example.input_text),
            output_tokens=_tokens(output),
            estimated_cost_usd=0.0,
            privacy="local",
            raw_metadata={"provider": self.id},
        )


class MockBadProvider:
    """A weak candidate: a generic answer, slower, and erroring on ~1 in 5 inputs."""

    id: str = "mock_bad"
    label: str = "Mock · bad"
    privacy: Privacy = "local"

    def generate(self, example: Example, candidate: Candidate) -> ProviderResult:
        # Deterministically fail on a subset to exercise the error path + a failure case — but
        # only on scored (dataset) runs. The keyless quick path (no expected answer) always
        # returns a weak answer so the head-to-head stays a clean good-vs-bad.
        if example.expected_text and _stable_int(example.input_text) % 5 == 0:
            raise RuntimeError("mock_bad: simulated provider failure")

        output = _shape_for_prompt(_GENERIC_ANSWER, candidate.system_prompt)
        latency = 120 + _stable_int(example.input_text) % 80
        return ProviderResult(
            output_text=output,
            latency_ms=latency,
            input_tokens=_tokens(example.input_text),
            output_tokens=_tokens(output),
            estimated_cost_usd=0.0,
            privacy="local",
            raw_metadata={"provider": self.id},
        )
