"""Deterministic scoring primitives (ADR-0001 §7).

v0 scoring is keyless and reproducible: exact / contains / normalized-similarity, all from
the standard library. LLM-as-judge is deferred post-v0. Determinism is what lets the full
proof suite run without API keys and makes runs testable.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from orionfold.domain.models import Dataset, Rubric, RubricKind

_WHITESPACE = re.compile(r"\s+")

# Per-kind default passing threshold (0..1). The *fallback* a run starts from when the user
# hasn't tuned it: Similarity is lenient (0.55 is typical for good paraphrased summaries — 0.80
# wrongly reads them as "no winner"); Keypoint/Judge stay strict (0.80). Settings sliders may
# override these per kind; the resolved value still travels in config_hash, so a tuned threshold
# is part of the proof's identity. Kinds without a tunable default (exact/contains/none) fall back
# to the Rubric field default. This is the SINGLE SOURCE OF TRUTH: the frontend consumes a codegen'd
# copy (`web/.../thresholds.generated.ts`, written by `orionfold codegen`); a test
# (`tests/unit/test_codegen.py`) fails if that file drifts from this map.
DEFAULT_THRESHOLDS: dict[RubricKind, float] = {
    "similarity": 0.55,
    "keypoint": 0.8,
    "judge": 0.8,
}


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


def score_keypoints(keypoints: list[str], output: str, rubric: Rubric) -> float:
    """Fraction of ``keypoints`` whose normalized text appears in the normalized output.

    Empty keypoints returns 0.0; the engine treats an empty list as a signal to fall back to
    similarity scoring for that row, so this primitive never has to know about the fallback.
    """
    if not keypoints:
        return 0.0
    out = normalize(output, case_sensitive=rubric.case_sensitive)
    hits = sum(
        1 for kp in keypoints if normalize(kp, case_sensitive=rubric.case_sensitive) in out
    )
    return hits / len(keypoints)


def threshold_for(kind: RubricKind, overrides: dict[str, float] | None = None) -> float:
    """The default passing threshold for a scoring ``kind``.

    A user override (from Settings sliders) wins; otherwise the built-in ``DEFAULT_THRESHOLDS``
    map; otherwise the ``Rubric`` field default (0.8) for kinds with no tunable default.
    """
    if overrides and kind in overrides:
        return overrides[kind]
    if kind in DEFAULT_THRESHOLDS:
        return DEFAULT_THRESHOLDS[kind]
    return Rubric.model_fields["threshold"].default


# A dataset's display **check hint** (DB/API metadata) maps to a scoring kind, so an "Exact match"
# label set grades by equality instead of partial similarity (B / _IDEAS issue #3). The hint vocab
# (``web/.../tags.ts``) is {"" | substring | numeric | exact | eyeball}. ``numeric`` is normalized
# equality in v0 (a tolerance check is out of scope); ``eyeball`` stays on the keyless heuristic so
# Auto never requires a configured judge. A hint is a stronger signal than the keypoint heuristic, so
# it wins when present; absence (the mock matrix has none) preserves the keypoint default → 467ddd96c9a5.
_HINT_KIND: dict[str, RubricKind] = {
    "exact": "exact",
    "numeric": "exact",
    "substring": "contains",
}


def default_rubric_for(
    dataset: Dataset,
    overrides: dict[str, float] | None = None,
    *,
    check_hint: str | None = None,
) -> Rubric:
    """Pick the default rubric for a dataset.

    Resolution order: an explicit dataset ``check_hint`` wins (exact/numeric → ``exact``,
    substring → ``contains``); otherwise keypoint when any example carries keypoints, else
    similarity. The resolved kind's default threshold comes from ``threshold_for`` so the Auto
    path honors the per-kind defaults and any persisted Settings override.
    """
    hinted = _HINT_KIND.get((check_hint or "").strip())
    kind: RubricKind = hinted or (
        "keypoint" if any(ex.keypoints for ex in dataset.examples) else "similarity"
    )
    return Rubric(kind=kind, threshold=threshold_for(kind, overrides))
