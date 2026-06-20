"""Deterministic, keyless mock providers — the default proof path (ADR-0001 §6, §8).

These let the whole loop run with no network and no API keys, which is what makes the test
suite reproducible and the first-run experience instant. ``mock_good`` returns the expected
answer; ``mock_bad`` returns a generic answer and deterministically errors on a subset of
inputs so the run always exercises the error path and produces a real failure case.
"""

from __future__ import annotations

import hashlib

from orionfold.domain.models import Candidate, Example, Privacy, ProviderResult

# A plausible-but-wrong generic answer, so mock_bad scores poorly on real summaries.
_GENERIC_ANSWER = "This document discusses various financial topics and market conditions."


def _stable_int(text: str) -> int:
    """Process-independent hash (Python's ``hash`` is salted; sha256 is reproducible)."""
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:4], "big")


def _tokens(text: str) -> int:
    return len(text.split())


class MockGoodProvider:
    """A strong candidate: returns the expected text with deterministic local latency."""

    id: str = "mock_good"
    label: str = "Mock · good"
    privacy: Privacy = "local"

    def generate(self, example: Example, candidate: Candidate) -> ProviderResult:
        output = example.expected_text
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
        # Deterministically fail on a subset to exercise the error path + a failure case.
        if _stable_int(example.input_text) % 5 == 0:
            raise RuntimeError("mock_bad: simulated provider failure")

        output = _GENERIC_ANSWER
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
