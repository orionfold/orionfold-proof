"""Receipts must carry provenance, state a clear recommendation, and leak no secrets."""

import pytest

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


def test_html_receipt_carries_both_palettes():
    html_out = export.to_html(_report())
    assert "@media (prefers-color-scheme: light)" in html_out
    assert ':root[data-theme="light"]' in html_out
    assert ':root[data-theme="dark"]' in html_out
    # standalone (no explicit theme) must not pin a data-theme on <html>
    assert "data-theme=" not in html_out.split("<head>")[0]
    # The @media and :root[data-theme="light"] light branches must carry identical token values
    # (two selectors, one palette) — guards against a single-branch edit drifting AA-corrected colors.
    assert html_out.count("--rc-case-key: #5f6e80") == 2
    assert html_out.count("--rc-case-key: #6f8190") == 2  # the two dark branches, unchanged


def test_html_receipt_theme_param_pins_data_theme():
    report = _report()
    assert '<html lang="en" data-theme="light">' in export.to_html(report, theme="light")
    assert '<html lang="en" data-theme="dark">' in export.to_html(report, theme="dark")
    # an unknown theme is ignored (no attribute)
    assert '<html lang="en">' in export.to_html(report, theme="bogus")


# ---------------------------------------------------------------------------
# v5 tests — Scored-by descriptor + run-cost summary
# ---------------------------------------------------------------------------

_BRIEF_V5 = ProofBrief(
    task_name="Investment memo summarization",
    decision_question="Which model should I trust for client memos?",
    success_criteria="At least 80% similarity to the analyst summary.",
)


@pytest.fixture
def make_report():
    """Factory fixture: returns a ProofReport built with a parameterizable rubric kind."""

    def _make(kind: str = "similarity", judge_provider_id: str | None = None, judge_model: str | None = None):
        return run_proof(
            run_id="run_receipt_v5",
            created_at="2026-06-21T10:00:00Z",
            brief=_BRIEF_V5,
            dataset=load_dataset("investment-memo-summarization"),
            candidates=[
                Candidate(id="mock_good", label="Mock · good", provider_id="mock_good"),
                Candidate(id="mock_bad", label="Mock · bad", provider_id="mock_bad"),
            ],
            rubric=Rubric(kind=kind, judge_provider_id=judge_provider_id, judge_model=judge_model),
        )

    return _make


def test_receipt_version_is_8():
    assert export.RECEIPT_VERSION == 8


def test_receipt_has_cost_per_quality_column_and_field():
    report = _report()  # mock_good passes 5/5 at cost $0.00 -> "Free"
    md = export.to_markdown(report)
    html = export.to_html(report)
    assert "$ / quality" in md
    assert "$ / quality" in html
    assert "Free" in md
    assert '"cost_per_quality"' in export.to_json(report)


def test_scored_by_keypoint(make_report):
    data = export.build_receipt(make_report(kind="keypoint"))
    assert data["scored_by"] == "Keypoint coverage"


def test_scored_by_judge_shows_model(make_report):
    data = export.build_receipt(make_report(kind="judge", judge_provider_id="mock_judge", judge_model="claude-haiku-4-5"))
    assert "LLM judge" in data["scored_by"] and "claude-haiku-4-5" in data["scored_by"]


def test_cost_block_present(make_report):
    data = export.build_receipt(make_report(kind="keypoint"))
    assert set(data["cost"]) == {"candidate", "judge", "total"}


def test_markdown_has_scored_by_and_run_cost(make_report):
    md = export.to_markdown(make_report(kind="keypoint"))
    assert "Scored by" in md and "Run cost" in md


def test_html_has_scored_by_and_run_cost(make_report):
    h = export.to_html(make_report(kind="keypoint"))
    assert "Scored by" in h and "Run cost" in h


# ---------------------------------------------------------------------------
# v6 tests — prompt-variants section, JSON field, honest repro
# ---------------------------------------------------------------------------

def test_receipt_records_prompt_variants_and_text():
    from orionfold.domain.models import (
        Candidate, LeaderboardEntry, ProofBrief, ProofReport, ProofRun,
        Rubric, RunCostSummary,
    )

    cands = [
        Candidate(id="mock_good#baseline", label="Baseline", provider_id="mock_good",
                  system_prompt="Be neutral."),
        Candidate(id="mock_good#concise", label="Concise", provider_id="mock_good",
                  system_prompt="Be terse."),
    ]
    run = ProofRun(
        id="run_x", brief=ProofBrief(task_name="t", decision_question="q"),
        dataset_id="d1", dataset_name="D1", rubric=Rubric(threshold=0.8),
        candidates=cands, config_hash="abc123abc123", created_at="2026-06-21T00:00:00Z",
    )
    lb = [
        LeaderboardEntry(candidate_id="mock_good#baseline", label="Baseline",
                         provider_id="mock_good", privacy="local", system_prompt="Be neutral.",
                         total=1, pass_count=1, pass_rate=1.0, avg_score=1.0, avg_latency_ms=10,
                         total_estimated_cost_usd=0.0, failure_count=0, error_count=0,
                         recommended=True),
        LeaderboardEntry(candidate_id="mock_good#concise", label="Concise",
                         provider_id="mock_good", privacy="local", system_prompt="Be terse.",
                         total=1, pass_count=1, pass_rate=1.0, avg_score=1.0, avg_latency_ms=10,
                         total_estimated_cost_usd=0.0, failure_count=0, error_count=0),
    ]
    report = ProofReport(run=run, leaderboard=lb, results=[],
                         cost_summary=RunCostSummary(candidate_cost_usd=0, judge_cost_usd=0, total_cost_usd=0))

    data = export.build_receipt(report)
    assert data["receipt_version"] == 8
    assert data["prompt_variants"] == [
        {"name": "Baseline", "system_prompt": "Be neutral."},
        {"name": "Concise", "system_prompt": "Be terse."},
    ]
    md = export.to_markdown(report)
    assert "## Prompt variants" in md
    assert "Be neutral." in md and "Be terse." in md
    html = export.to_html(report)
    assert "Prompt variants" in html and "Be terse." in html
    # Provenance, not secrets: nothing key-shaped leaks (sanity).
    assert "API_KEY" not in md and "API_KEY" not in html


# ---------------------------------------------------------------------------
# v8 tests — quick-compare receipt (unscored, human pick)
# ---------------------------------------------------------------------------

from orionfold.domain.models import Dataset, Example


def _quick_report(chosen="mock_good"):
    dataset = Dataset(
        id="quick-compare", name="Quick Compare",
        examples=[Example(input_text="Summarize: revenue grew 22%.", expected_text="")],
    )
    report = run_proof(
        run_id="run_q", created_at="2026-06-22T00:00:00Z",
        brief=ProofBrief(task_name="Quick check", decision_question="Which reads better?"),
        dataset=dataset,
        candidates=[
            Candidate(id="mock_good", label="Mock · good", provider_id="mock_good"),
            Candidate(id="mock_bad", label="Mock · bad", provider_id="mock_bad"),
        ],
        rubric=Rubric(kind="none"),
    )
    report.run.mode = "quick"
    report.run.chosen_winner = chosen
    return report


def test_quick_receipt_is_pick_based_and_unscored():
    data = export.build_receipt(_quick_report(chosen="mock_good"))
    assert data["mode"] == "quick"
    assert data["chosen_winner"] == "mock_good"
    assert data["failure_cases"] == []           # no scoring → no failures section
    assert "Picked" in data["verdict"]
    assert "mock_good" in data["recommendation"]
    assert "quick" in data["quick_note"].lower()


def test_quick_receipt_tie():
    data = export.build_receipt(_quick_report(chosen="tie"))
    assert "Tie" in data["verdict"]


def test_quick_markdown_has_objective_columns_and_no_score():
    md = export.to_markdown(_quick_report(chosen="mock_good"))
    assert "QUICK CHECK" in md
    assert "Tokens" in md and "Latency" in md
    assert "Pass rate" not in md and "$ / quality" not in md
    assert "Failure cases" not in md
    assert "Promote to a full scored run" in md
    assert "⭐" in md  # the picked candidate is starred


def test_quick_html_is_objective_and_secret_free():
    html_out = export.to_html(_quick_report(chosen="mock_good"))
    assert "QUICK CHECK" in html_out
    assert "Tokens" in html_out and "Latency" in html_out
    assert "Pass rate" not in html_out
    assert "Promote to a full scored run" in html_out
    low = html_out.lower()
    assert "api_key" not in low and "sk-" not in low
