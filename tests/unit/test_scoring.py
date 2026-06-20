"""Scoring primitives must be deterministic and behave per rubric kind."""

from orionfold.domain.models import Rubric
from orionfold.scoring.rubric import normalize, passed, score


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
