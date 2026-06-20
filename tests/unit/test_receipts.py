"""Receipts must carry provenance, state a clear recommendation, and leak no secrets."""

from orionfold.data import load_dataset
from orionfold.domain.models import Candidate, ProofBrief, Rubric
from orionfold.proof.engine import run_proof
from orionfold.receipts import export

_BRIEF = ProofBrief(
    task_name="Investment memo summarization",
    decision_question="Which model should I trust for client memos?",
    success_criteria="At least 80% similarity to the analyst summary.",
)


def _report():
    return run_proof(
        run_id="run_receipt",
        created_at="2026-06-19T12:00:00Z",
        brief=_BRIEF,
        dataset=load_dataset("investment-memo-summarization"),
        candidates=[
            Candidate(id="mock_good", label="Mock · good", provider_id="mock_good"),
            Candidate(id="mock_bad", label="Mock · bad", provider_id="mock_bad"),
        ],
        rubric=Rubric(),
    )


def test_all_formats_carry_version_hash_and_timestamp():
    report = _report()
    for text in (export.to_json(report), export.to_markdown(report), export.to_html(report)):
        assert report.run.config_hash in text
        assert "2026-06-19T12:00:00Z" in text
        assert report.run.id in text  # repro: run id present
    # JSON explicitly exposes the current schema version field.
    assert f'"receipt_version": {export.RECEIPT_VERSION}' in export.to_json(report)


def test_recommendation_names_the_winning_candidate_with_a_verdict():
    report = _report()
    for text in (export.to_markdown(report), export.to_html(report)):
        assert "Verdict" in text
        assert "Ship" in text  # mock_good passes 5/5 → Ship
        assert "mock_good" in text


def test_repro_section_supports_rerun():
    report = _report()
    for text in (export.to_markdown(report), export.to_html(report)):
        assert "Repro" in text
        assert "/api/runs" in text  # a concrete rerun command


def test_failure_case_appears_in_receipt():
    report = _report()
    md = export.to_markdown(report)
    assert "Failure cases" in md
    # The deterministic mock_bad error should surface as a failure case.
    assert "error:" in md


def test_receipt_never_contains_secret_markers():
    # Even though we never write secrets, assert the guard holds across every format.
    report = _report()
    needles = ["api_key", "apikey", "authorization", "bearer", "sk-", "secret", "password"]
    for text in (export.to_json(report), export.to_markdown(report), export.to_html(report)):
        lowered = text.lower()
        for needle in needles:
            assert needle not in lowered, f"receipt leaked marker: {needle}"
