"""Tests for bundled datasets, keypoints, and defaults."""

import pytest

from orionfold.data import bundled_datasets, load_dataset
from orionfold.scoring.rubric import default_rubric_for, normalize

# Categories the triage dataset is allowed to label with (mirrors the JSON instruction).
_TRIAGE_CATEGORIES = {"billing", "bug", "feature_request", "account", "integration"}


def test_demo_dataset_has_keypoints():
    """Every example in the demo dataset has keypoints."""
    ds = load_dataset("investment-memo-summarization")
    assert all(ex.keypoints for ex in ds.examples)


def test_demo_keypoints_are_substrings_of_expected():
    """Every keypoint is a normalized substring of its example's expected_text."""
    ds = load_dataset("investment-memo-summarization")
    for ex in ds.examples:
        exp = normalize(ex.expected_text)
        for kp in ex.keypoints:
            assert normalize(kp) in exp, f"{kp!r} not in expected {ex.expected_text!r}"


def test_demo_default_rubric_is_keypoint():
    """The demo dataset's default rubric is 'keypoint' because it carries keypoints."""
    assert default_rubric_for(load_dataset("investment-memo-summarization")).kind == "keypoint"


@pytest.mark.parametrize(
    "dataset_id",
    [
        "investment-memo-summarization",
        "support-ticket-triage",
        "contract-field-extraction",
        "buyer-need-solution-match",
    ],
)
def test_bundled_dataset_loads_with_five_examples(dataset_id):
    """Each bundled dataset loads, validates, and carries exactly five examples."""
    ds = load_dataset(dataset_id)
    assert ds.id == dataset_id
    assert len(ds.examples) == 5
    assert all(ex.input_text and ex.expected_text for ex in ds.examples)


def test_all_bundled_datasets_are_listed():
    """``bundled_datasets()`` surfaces every registered dataset (catalog/import picks them up)."""
    ids = {ds.id for ds in bundled_datasets()}
    assert {
        "investment-memo-summarization",
        "support-ticket-triage",
        "contract-field-extraction",
        "buyer-need-solution-match",
    } <= ids


# --- support-ticket-triage → exact ---------------------------------------------------------


def test_triage_resolves_to_exact_with_hint():
    """No keypoints + an 'exact' hint → the exact rubric (classification by equality)."""
    ds = load_dataset("support-ticket-triage")
    assert all(not ex.keypoints for ex in ds.examples)
    assert default_rubric_for(ds, check_hint="exact").kind == "exact"


def test_triage_expected_is_a_known_bare_label():
    """Every expected_text is exactly one label from the fixed category set."""
    ds = load_dataset("support-ticket-triage")
    for ex in ds.examples:
        assert ex.expected_text in _TRIAGE_CATEGORIES, f"unexpected label {ex.expected_text!r}"


# --- contract-field-extraction → contains --------------------------------------------------


def test_extraction_resolves_to_contains_with_substring_hint():
    """No keypoints + a 'substring' hint → the contains rubric (forgiving extraction)."""
    ds = load_dataset("contract-field-extraction")
    assert all(not ex.keypoints for ex in ds.examples)
    assert default_rubric_for(ds, check_hint="substring").kind == "contains"


def test_extraction_expected_is_a_concise_field_value():
    """Each expected_text is a short field value (not a sentence), suited to contains scoring."""
    ds = load_dataset("contract-field-extraction")
    for ex in ds.examples:
        assert ex.expected_text.strip() == ex.expected_text
        assert len(ex.expected_text.split()) <= 4, f"field too long: {ex.expected_text!r}"


# --- buyer-need-solution-match → similarity (UI auto-judge for samples) ---------------------


def test_buyer_match_resolves_to_similarity_without_hint():
    """No keypoints + no hint → similarity (the keyless/backend default; UI auto-picks judge)."""
    ds = load_dataset("buyer-need-solution-match")
    assert all(not ex.keypoints for ex in ds.examples)
    assert default_rubric_for(ds).kind == "similarity"


def test_buyer_match_expected_is_a_substantive_pitch():
    """Each expected_text is a full pitch sentence — a paraphrase task lexical scoring can't crack."""
    ds = load_dataset("buyer-need-solution-match")
    for ex in ds.examples:
        assert len(ex.expected_text.split()) >= 12
