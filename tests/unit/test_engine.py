"""The matrix engine must be deterministic, error-safe, and produce a ranked leaderboard."""

from orionfold.data import load_dataset
from orionfold.domain.models import Candidate, ProofBrief, Rubric
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
