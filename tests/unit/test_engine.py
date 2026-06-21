"""The matrix engine must be deterministic, error-safe, and produces a ranked leaderboard."""

import hashlib
import json

import pytest

from orionfold import __version__
from orionfold.data import load_dataset
from orionfold.domain.models import Candidate, Dataset, Example, ProofBrief, Rubric
from orionfold.proof.engine import config_hash, run_proof

_CANDS = [
    Candidate(id="mock_good", label="Mock · good", provider_id="mock_good"),
    Candidate(id="mock_bad", label="Mock · bad", provider_id="mock_bad"),
]
_BRIEF = ProofBrief(task_name="Memo summarization", decision_question="Which to trust?")


def _report():
    return run_proof(
        run_id="run_test",
        created_at="2026-06-19T12:00:00Z",
        brief=_BRIEF,
        dataset=load_dataset("investment-memo-summarization"),
        candidates=_CANDS,
        rubric=Rubric(),
    )


def test_run_is_deterministic_including_config_hash():
    a, b = _report(), _report()
    assert a.run.config_hash == b.run.config_hash
    assert [r.model_dump() for r in a.results] == [r.model_dump() for r in b.results]


def test_matrix_covers_every_candidate_times_example():
    report = _report()
    n_examples = len(load_dataset("investment-memo-summarization").examples)
    assert len(report.results) == len(_CANDS) * n_examples


def test_good_candidate_wins_and_is_recommended():
    report = _report()
    top = report.leaderboard[0]
    assert top.candidate_id == "mock_good"
    assert top.recommended is True
    assert top.pass_rate == 1.0
    # Exactly one entry is recommended.
    assert sum(1 for e in report.leaderboard if e.recommended) == 1


def test_provider_error_becomes_a_failing_row_not_an_exception():
    report = _report()
    errored = [r for r in report.results if r.error is not None]
    assert errored, "expected mock_bad to error on at least one example"
    assert all(r.passed is False and r.score == 0.0 for r in errored)


def test_config_hash_changes_with_rubric():
    ds = load_dataset("investment-memo-summarization")
    h1 = config_hash(ds, _CANDS, Rubric(threshold=0.8))
    h2 = config_hash(ds, _CANDS, Rubric(threshold=0.5))
    assert h1 != h2


# ─── Task 4: keypoint branch, judge branch, cost rollup ───────────────────────


def _ds():
    return Dataset(id="d", name="d", examples=[
        Example(input_text="Q3 rev $48.2M up 22%", expected_text="Revenue grew 22% to $48.2M.",
                keypoints=["22%", "$48.2M"]),
    ])


def _run(rubric):
    return run_proof(
        run_id="r1", created_at="2026-06-21T00:00:00Z",
        brief=ProofBrief(task_name="t", decision_question="q"),
        dataset=_ds(),
        candidates=[Candidate(id="mock_good", label="g", provider_id="mock_good")],
        rubric=rubric,
    )


def test_keypoint_run_passes_for_mock_good():
    report = _run(Rubric(kind="keypoint"))
    assert report.results[0].score == 1.0 and report.results[0].passed


def test_judge_run_via_mock_is_deterministic_and_costed():
    report = _run(Rubric(kind="judge", judge_provider_id="mock_judge"))
    row = report.results[0]
    assert row.judge_cost_usd == 0.0001 and row.judge_latency_ms == 5
    assert report.cost_summary.judge_cost_usd == pytest.approx(0.0001)


def test_judge_without_provider_id_raises():
    with pytest.raises(ValueError):
        _run(Rubric(kind="judge"))


def test_cost_summary_totals():
    report = _run(Rubric(kind="judge", judge_provider_id="mock_judge"))
    cs = report.cost_summary
    assert cs.total_cost_usd == pytest.approx(cs.candidate_cost_usd + cs.judge_cost_usd)


def test_non_judge_run_has_zero_judge_cost():
    report = _run(Rubric(kind="keypoint"))
    assert report.cost_summary.judge_cost_usd == 0.0
    assert report.cost_summary.total_cost_usd == report.cost_summary.candidate_cost_usd


# ─── Task 3: config_hash includes system_prompt only when set ─────────────────


def test_config_hash_unchanged_for_model_compare_runs():
    # A run whose candidates have system_prompt=None must hash identically to the pre-feature
    # payload — i.e. the system_prompt key must be ABSENT, not present-and-null. Lock the value.
    ds = Dataset(id="d1", name="d1", description="", examples=[Example(input_text="a", expected_text="b")])
    cands = [Candidate(id="mock_good", label="Mock", provider_id="mock_good")]
    payload = {
        "version": __version__,
        "dataset": {"id": ds.id, "examples": [e.model_dump() for e in ds.examples]},
        "candidates": [{"id": "mock_good", "provider_id": "mock_good", "privacy": "local", "model": None}],
        "rubric": Rubric(threshold=0.8).model_dump(),
    }
    expected = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    assert config_hash(ds, cands, Rubric(threshold=0.8)) == expected


def test_config_hash_distinguishes_prompt_variants():
    ds = Dataset(id="d1", name="d1", description="", examples=[Example(input_text="a", expected_text="b")])
    v1 = [Candidate(id="ollama#a", label="A", provider_id="ollama", model="llama3.2", system_prompt="terse")]
    v2 = [Candidate(id="ollama#b", label="B", provider_id="ollama", model="llama3.2", system_prompt="verbose")]
    assert config_hash(ds, v1, Rubric()) != config_hash(ds, v2, Rubric())
    # Same prompts reproduce the same hash (repeatability).
    v1_again = [Candidate(id="ollama#a", label="A", provider_id="ollama", model="llama3.2", system_prompt="terse")]
    assert config_hash(ds, v1, Rubric()) == config_hash(ds, v1_again, Rubric())
    # Same id, differ ONLY by system_prompt → must hash differently (locks the conditional).
    same_id_a = [Candidate(id="ollama#x", label="X", provider_id="ollama", model="llama3.2", system_prompt="terse")]
    same_id_b = [Candidate(id="ollama#x", label="X", provider_id="ollama", model="llama3.2", system_prompt="verbose")]
    assert config_hash(ds, same_id_a, Rubric()) != config_hash(ds, same_id_b, Rubric())
