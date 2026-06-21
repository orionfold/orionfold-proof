"""Tests for bundled datasets, keypoints, and defaults."""

from orionfold.data import load_dataset
from orionfold.scoring.rubric import default_rubric_for, normalize


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
