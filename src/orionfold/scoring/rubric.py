"""Deterministic scoring primitives (ADR-0001 §7).

v0 scoring is keyless and reproducible: exact / contains / normalized-similarity, all from
the standard library. LLM-as-judge is deferred post-v0. Determinism is what lets the full
proof suite run without API keys and makes runs testable.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from orionfold.domain.models import Rubric

_WHITESPACE = re.compile(r"\s+")


def normalize(text: str, *, case_sensitive: bool = False) -> str:
    """Collapse whitespace and (optionally) case so trivial differences don't fail a match."""
    collapsed = _WHITESPACE.sub(" ", text).strip()
    return collapsed if case_sensitive else collapsed.lower()


def score(expected: str, output: str, rubric: Rubric) -> float:
    """Score ``output`` against ``expected`` in [0, 1] per the rubric kind.

    - ``exact``: 1.0 iff normalized texts are equal.
    - ``contains``: 1.0 iff the normalized expected text appears in the normalized output.
    - ``similarity``: difflib ratio of the normalized texts (a stable 0..1 overlap measure).
    """
    exp = normalize(expected, case_sensitive=rubric.case_sensitive)
    out = normalize(output, case_sensitive=rubric.case_sensitive)

    if rubric.kind == "exact":
        return 1.0 if exp == out else 0.0
    if rubric.kind == "contains":
        return 1.0 if exp and exp in out else 0.0
    # similarity
    if not exp and not out:
        return 1.0
    return SequenceMatcher(None, exp, out).ratio()


def passed(score_value: float, rubric: Rubric) -> bool:
    """True when a score clears the rubric threshold."""
    return score_value >= rubric.threshold
