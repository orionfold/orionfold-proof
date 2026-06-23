"""Scoring primitives must be deterministic and behave per rubric kind."""

from orionfold.domain.models import Dataset, Example, Rubric
from orionfold.scoring.rubric import (
    DEFAULT_THRESHOLDS,
    default_rubric_for,
    normalize,
    passed,
    score,
    score_keypoints,
    threshold_for,
)


def test_normalize_collapses_whitespace_and_case():
    assert normalize("  Hello   World \n") == "hello world"
    assert normalize("Hello World", case_sensitive=True) == "Hello World"


def test_exact_rubric_matches_only_on_equality():
    rubric = Rubric(kind="exact", threshold=1.0)
    assert score("Net margin improved.", "net   margin improved.", rubric) == 1.0
    assert score("Net margin improved.", "Net margin declined.", rubric) == 0.0


def test_contains_rubric_checks_substring():
    rubric = Rubric(kind="contains", threshold=1.0)
    assert score("net margin", "The net margin improved this quarter.", rubric) == 1.0
    assert score("gross margin", "The net margin improved.", rubric) == 0.0


def test_similarity_rubric_is_graded_and_deterministic():
    rubric = Rubric(kind="similarity")
    perfect = score("Revenue grew 20%.", "Revenue grew 20%.", rubric)
    partial = score("Revenue grew 20%.", "Revenue grew twenty percent.", rubric)
    none = score("Revenue grew 20%.", "Completely unrelated text here.", rubric)
    assert perfect == 1.0
    assert 0.0 < partial < 1.0
    assert none < partial
    # Deterministic across calls.
    assert partial == score("Revenue grew 20%.", "Revenue grew twenty percent.", rubric)


def test_passed_uses_threshold():
    rubric = Rubric(kind="similarity", threshold=0.8)
    assert passed(0.81, rubric) is True
    assert passed(0.79, rubric) is False


_R = Rubric(kind="keypoint")


def test_keypoints_all_present_scores_one():
    out = "Revenue grew 22% to $48.2M with 118% retention and 79% margin."
    assert score_keypoints(["22%", "$48.2M", "118%", "79%"], out, _R) == 1.0


def test_keypoints_partial_coverage():
    out = "Revenue grew 22% to $48.2M."
    assert score_keypoints(["22%", "$48.2M", "118%", "79%"], out, _R) == 0.5


def test_keypoints_none_present_scores_zero():
    assert score_keypoints(["22%", "118%"], "An unrelated generic answer.", _R) == 0.0


def test_keypoints_case_insensitive_by_default():
    assert score_keypoints(["Series B"], "raising a series b round", _R) == 1.0


def test_keypoints_empty_list_returns_zero_sentinel():
    # Empty keypoints is the engine's fallback signal; the primitive returns 0.0 for "nothing matched".
    assert score_keypoints([], "anything", _R) == 0.0


def test_default_rubric_keypoint_when_present():
    ds = Dataset(id="d", name="d", examples=[Example(input_text="i", expected_text="e", keypoints=["x"])])
    assert default_rubric_for(ds).kind == "keypoint"


def test_default_rubric_similarity_when_absent():
    ds = Dataset(id="d", name="d", examples=[Example(input_text="i", expected_text="e")])
    assert default_rubric_for(ds).kind == "similarity"


# ─── A2: per-kind default thresholds + Settings overrides ─────────────────────


def test_default_threshold_map_values():
    # Similarity is lenient (0.55 — paraphrased summaries score low on lexical overlap);
    # Keypoint/Judge stay strict (0.8). Frozen because the frontend mirror must agree.
    assert DEFAULT_THRESHOLDS == {"similarity": 0.55, "keypoint": 0.8, "judge": 0.8}


def test_threshold_for_uses_map_then_override():
    assert threshold_for("similarity") == 0.55
    assert threshold_for("keypoint") == 0.8
    # A persisted override wins over the built-in map.
    assert threshold_for("similarity", {"similarity": 0.7}) == 0.7
    # Kinds with no tunable default fall back to the Rubric field default (0.8).
    assert threshold_for("exact") == Rubric.model_fields["threshold"].default


def test_default_rubric_similarity_carries_lenient_threshold():
    # The Auto path resolves a similarity rubric at the lenient default, not the old 0.80.
    ds = Dataset(id="d", name="d", examples=[Example(input_text="i", expected_text="e")])
    assert default_rubric_for(ds).threshold == 0.55


def test_default_rubric_keypoint_threshold_unchanged_protects_mock_hash():
    # The keypoint default MUST stay 0.8: the canonical mock matrix dataset carries keypoints, so
    # its Auto rubric resolves to keypoint@0.8 → config_hash 467ddd96c9a5 is unaffected by A2.
    ds = Dataset(
        id="d", name="d",
        examples=[Example(input_text="i", expected_text="e", keypoints=["x"])],
    )
    r = default_rubric_for(ds)
    assert r.kind == "keypoint" and r.threshold == 0.8


def test_default_rubric_override_applies_to_resolved_kind():
    ds = Dataset(id="d", name="d", examples=[Example(input_text="i", expected_text="e")])
    assert default_rubric_for(ds, {"similarity": 0.4}).threshold == 0.4


# ─── B: check-hint → scoring-method mapping ───────────────────────────────────


def test_check_hint_exact_resolves_exact():
    # An "exact" hint grades labels by normalized equality, not partial similarity.
    ds = Dataset(id="d", name="d", examples=[Example(input_text="i", expected_text="e")])
    assert default_rubric_for(ds, check_hint="exact").kind == "exact"


def test_check_hint_numeric_resolves_exact():
    # Numeric match is normalized equality in v0 (no tolerance check — out of scope).
    ds = Dataset(id="d", name="d", examples=[Example(input_text="i", expected_text="42")])
    assert default_rubric_for(ds, check_hint="numeric").kind == "exact"


def test_check_hint_substring_resolves_contains():
    ds = Dataset(id="d", name="d", examples=[Example(input_text="i", expected_text="e")])
    assert default_rubric_for(ds, check_hint="substring").kind == "contains"


def test_check_hint_eyeball_falls_back_to_heuristic():
    # Eyeball stays on the keyless heuristic — Auto must not require a configured judge.
    ds = Dataset(id="d", name="d", examples=[Example(input_text="i", expected_text="e")])
    assert default_rubric_for(ds, check_hint="eyeball").kind == "similarity"


def test_check_hint_empty_uses_heuristic():
    ds = Dataset(id="d", name="d", examples=[Example(input_text="i", expected_text="e")])
    assert default_rubric_for(ds, check_hint="").kind == "similarity"
    assert default_rubric_for(ds, check_hint=None).kind == "similarity"


def test_check_hint_wins_over_keypoint_heuristic():
    # An explicit hint is a stronger signal than the keypoint heuristic.
    ds = Dataset(
        id="d", name="d",
        examples=[Example(input_text="i", expected_text="e", keypoints=["x"])],
    )
    assert default_rubric_for(ds, check_hint="exact").kind == "exact"


def test_check_hint_absent_preserves_mock_keypoint_hash():
    # The mock matrix dataset carries no hint, so Auto still resolves keypoint@0.8 → 467ddd96c9a5.
    ds = Dataset(
        id="d", name="d",
        examples=[Example(input_text="i", expected_text="e", keypoints=["x"])],
    )
    r = default_rubric_for(ds)
    assert r.kind == "keypoint" and r.threshold == 0.8
