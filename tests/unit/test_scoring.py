"""Scoring primitives must be deterministic and behave per rubric kind."""

from orionfold.domain.models import Dataset, Example, Rubric
from orionfold.scoring.rubric import (
    default_rubric_for,
    normalize,
    passed,
    score,
    score_keypoints,
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
