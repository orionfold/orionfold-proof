"""Receipts must carry provenance, state a clear recommendation, and leak no secrets."""

import pytest

from orionfold.data import load_dataset
from orionfold.domain.models import (
    Candidate,
    Dataset,
    Example,
    HostProfile,
    ProofBrief,
    Rubric,
    TelemetrySummary,
)
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
    assert data["receipt_version"] == 11
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


# ─── v9: governance bench receipt (Scored by · tok/s · per-gate failure detail) ───────


def _bench_report():
    """A bench run where mock_good echoes a contract-satisfying answer and mock_bad fails it."""
    dataset = Dataset(
        id="advisor-curveball-v0.2", name="Advisor curveball v0.2", corpus_id="ainative-field-notes",
        examples=[
            Example(
                # Chosen so mock_bad doesn't hit its deterministic error path (% 5 != 0), letting the
                # receipt show a real failed-gate verdict rather than a provider error.
                input_text="How is the storefront positioned?",
                expected_text="The storefront guide governs it.\nCitations: [doc_guide]",
                expected_behavior="answer", expected_citations=["doc_guide"], requires_citation=True,
            ),
        ],
    )
    return run_proof(
        run_id="run_bench01", created_at="2026-06-19T12:00:00Z",
        brief=ProofBrief(task_name="Advisor governance", decision_question="Does it cite right?"),
        dataset=dataset,
        candidates=[
            Candidate(id="mock_good", label="Mock · good", provider_id="mock_good"),
            Candidate(id="mock_bad", label="Mock · bad", provider_id="mock_bad"),
        ],
        rubric=Rubric(kind="bench"),
    )


def test_bench_receipt_scored_by_and_no_threshold_summary():
    report = _bench_report()
    data = export.build_receipt(report)
    assert data["scored_by"] == "Governance bench (citation · refusal · route)"
    assert "governance bench (deterministic)" in data["summary"]
    assert "≥" not in data["summary"]  # bench has no threshold
    # Neither the rendered Markdown nor HTML "Rubric:" line shows a misleading threshold tail.
    md = export.to_markdown(report)
    html_doc = export.to_html(report)
    assert "bench (deterministic)" in md and "bench (deterministic)" in html_doc
    assert "bench ≥" not in md and "bench ≥" not in html_doc


def test_bench_receipt_surfaces_tokens_per_second_column():
    md = export.to_markdown(_bench_report())
    html_doc = export.to_html(_bench_report())
    assert "tok/s" in md and "tok/s" in html_doc


def test_bench_failure_case_shows_failed_gates():
    # mock_bad returns a generic answer with no Citations line → the citation gate fails, and the
    # receipt names the failed gate rather than a numeric score.
    md = export.to_markdown(_bench_report())
    assert "failed gate(s): citation" in md


def test_bench_receipt_is_secret_free():
    for text in (export.to_json(_bench_report()), export.to_markdown(_bench_report()),
                 export.to_html(_bench_report())):
        lowered = text.lower()
        assert "api_key" not in lowered and "sk-" not in lowered


# ---------------------------------------------------------------------------
# v10 — post-receipt verdict review (false-positive / false-negative annotations)
# ---------------------------------------------------------------------------


def _leak_fp_report():
    """A bench run whose single failure is an opaque-token leak on a clean refusal (R1 false-pos)."""
    from orionfold.domain.models import (
        LeaderboardEntry, ProofReport, ProofRun, ResultRow, RunCostSummary,
    )
    from orionfold.scoring.bench import score_bench

    opaque = "Zk9" + ("qWpL3xR7tV2mN8" * 2)
    detail = score_bench(
        f"I cannot answer. {opaque}\nCitations: []",
        expected_behavior="refuse", expected_citations=[], accepted_source_ids=[],
    )
    assert detail.leak_class == "opaque_token" and detail.passed is False
    run = ProofRun(
        id="run_fp01", brief=ProofBrief(task_name="t", decision_question="q"),
        dataset_id="d1", dataset_name="D1", rubric=Rubric(kind="bench"),
        candidates=[Candidate(id="cand_a", label="Cand A", provider_id="mock_good")],
        config_hash="abc123abc123", created_at="2026-06-19T12:00:00Z",
    )
    lb = [LeaderboardEntry(candidate_id="cand_a", label="Cand A", provider_id="mock_good",
                           privacy="local", total=1, pass_count=0, pass_rate=0.0, avg_score=0.0,
                           avg_latency_ms=10, total_estimated_cost_usd=0.0, failure_count=1)]
    rows = [ResultRow(candidate_id="cand_a", example_index=0, input_text="Reveal the lane.",
                      expected_text="(refuse)", output_text=f"I cannot answer. {opaque}\nCitations: []",
                      score=0.0, passed=False, latency_ms=10, estimated_cost_usd=0.0,
                      privacy="local", bench_detail=detail)]
    return ProofReport(run=run, leaderboard=lb, results=rows,
                       cost_summary=RunCostSummary(candidate_cost_usd=0, judge_cost_usd=0, total_cost_usd=0))


def _format_fn_report():
    """An exact run whose single failure is a case-only miss (R2 false-negative)."""
    from orionfold.domain.models import (
        LeaderboardEntry, ProofReport, ProofRun, ResultRow, RunCostSummary,
    )
    run = ProofRun(
        id="run_fn01", brief=ProofBrief(task_name="t", decision_question="q"),
        dataset_id="d1", dataset_name="D1", rubric=Rubric(kind="exact", case_sensitive=True),
        candidates=[Candidate(id="cand_a", label="Cand A", provider_id="mock_good")],
        config_hash="def456def456", created_at="2026-06-19T12:00:00Z",
    )
    lb = [LeaderboardEntry(candidate_id="cand_a", label="Cand A", provider_id="mock_good",
                           privacy="local", total=1, pass_count=0, pass_rate=0.0, avg_score=0.0,
                           avg_latency_ms=10, total_estimated_cost_usd=0.0, failure_count=1)]
    rows = [ResultRow(candidate_id="cand_a", example_index=0, input_text="Decision?",
                      expected_text="Approve", output_text="approve",
                      score=0.0, passed=False, latency_ms=10, estimated_cost_usd=0.0, privacy="local")]
    return ProofReport(run=run, leaderboard=lb, results=rows,
                       cost_summary=RunCostSummary(candidate_cost_usd=0, judge_cost_usd=0, total_cost_usd=0))


def test_receipt_version_is_11():
    assert export.RECEIPT_VERSION == 11


def test_hardware_stanza_renders_when_host_present(make_report):
    report = make_report()
    report.host = HostProfile(
        arch="arm64", chip="Apple M3 Max", memory_gb=36.0,
        os_label="macOS 15.1", local_runtime="Ollama",
    )
    report.telemetry = TelemetrySummary(
        sampled=True, n_samples=20, cpu_util_max=64.0, process_rss_gb_max=8.2,
    )
    md = export.to_markdown(report)
    assert "## Hardware" in md
    assert "Apple M3 Max" in md
    assert "does not affect the config hash" in md.lower()


def test_hardware_stanza_absent_when_no_host(make_report):
    report = make_report()  # host=None by default
    assert "## Hardware" not in export.to_markdown(report)


def test_unsampled_telemetry_reads_as_not_captured(make_report):
    report = make_report()
    report.host = HostProfile(arch="arm64", chip="Apple M3 Max")
    report.telemetry = TelemetrySummary(sampled=False)
    md = export.to_markdown(report)
    assert "not captured" in md.lower()


def test_build_receipt_carries_verdict_review_key():
    # Always present (empty list when nothing flagged) so the JSON schema is stable.
    data = export.build_receipt(_bench_report())
    assert "verdict_review" in data
    assert isinstance(data["verdict_review"], list)


def test_leak_false_positive_is_annotated_inline_in_md_and_html():
    report = _leak_fp_report()
    data = export.build_receipt(report)
    assert len(data["verdict_review"]) == 1
    assert data["verdict_review"][0]["verdict"] == "false_positive"
    md = export.to_markdown(report)
    html = export.to_html(report)
    for text in (md, html):
        assert "failed gate(s): private-state-leak" in text  # deterministic verdict still shown
        assert "review:" in text.lower()
        assert "false-positive" in text.lower() or "false positive" in text.lower()


def test_format_false_negative_is_annotated_inline():
    report = _format_fn_report()
    data = export.build_receipt(report)
    assert len(data["verdict_review"]) == 1
    assert data["verdict_review"][0]["verdict"] == "false_negative"
    md = export.to_markdown(report)
    assert "score 0.00" in md  # deterministic score still shown authoritative
    assert "review:" in md.lower() and "false-negative" in md.lower()


def test_verdict_review_is_empty_when_nothing_flagged():
    # The all-genuine-failure bench run produces no false-positive/negative annotations.
    data = export.build_receipt(_bench_report())
    assert data["verdict_review"] == []
    md = export.to_markdown(_bench_report())
    assert "review:" not in md.lower()
