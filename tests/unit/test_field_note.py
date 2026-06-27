"""Field note = a receipt-derived, publish-ready trust narrative scaffold.

The package emits structured, secret-free evidence + figures + a narrative *stub*; it never
authors the prose. These tests freeze: a valid frontmatter spine derived from the report, the
ADR-0005 §4 ``fmt_check`` flag, the reused receipt evidence body, two well-formed SVG figures
honouring the DS accent/status split, deterministic output, graceful degrade on quick/
no-winner runs, and secret-freedom.
"""

import xml.etree.ElementTree as ET

import yaml

from orionfold.data import load_dataset
from orionfold.domain.models import Candidate, Dataset, Example, ProofBrief, Rubric
from orionfold.proof.engine import run_proof
from orionfold.receipts import build_field_note
from orionfold.receipts.field_note import _frontmatter
from orionfold.receipts.figures import pareto_svg, pass_rate_svg

_BRIEF = ProofBrief(
    task_name="Support ticket triage",
    decision_question="Which model do I trust to triage tickets?",
    success_criteria="Exact label match.",
)


def _report(rubric=None):
    return run_proof(
        run_id="run_field_note",
        created_at="2026-06-19T12:00:00Z",
        brief=_BRIEF,
        dataset=load_dataset("support-ticket-triage"),
        candidates=[
            Candidate(id="mock_good", label="Mock · good", provider_id="mock_good"),
            Candidate(id="mock_bad", label="Mock · bad", provider_id="mock_bad"),
        ],
        rubric=rubric or Rubric(kind="exact", threshold=1.0),
    )


def _quick_report(chosen="mock_good"):
    report = run_proof(
        run_id="run_q",
        created_at="2026-06-22T00:00:00Z",
        brief=ProofBrief(task_name="Quick check", decision_question="Which reads better?"),
        dataset=Dataset(
            id="quick-compare",
            name="Quick Compare",
            examples=[Example(input_text="Summarize: revenue grew 22%.", expected_text="")],
        ),
        candidates=[
            Candidate(id="mock_good", label="Mock · good", provider_id="mock_good"),
            Candidate(id="mock_bad", label="Mock · bad", provider_id="mock_bad"),
        ],
        rubric=Rubric(kind="none"),
    )
    report.run.mode = "quick"
    report.run.chosen_winner = chosen
    return report


def _parse_frontmatter(note: str) -> dict:
    """Pull the leading ``---``-delimited YAML block out of the note and parse it."""
    assert note.startswith("---\n")
    end = note.index("\n---", 4)
    return yaml.safe_load(note[4:end])


# --- frontmatter spine -----------------------------------------------------------------------


def test_frontmatter_is_valid_yaml_with_required_spine_keys():
    fm = _parse_frontmatter(build_field_note(_report()))
    assert fm["artifact"] == "proof-field-note"
    for key in (
        "title", "date", "summary", "run_id", "config_hash", "decision_question",
        "dataset", "rubric", "recommended", "fmt_check", "candidates", "cost_usd", "tags",
    ):
        assert key in fm, f"missing frontmatter key: {key}"


def test_frontmatter_values_are_derived_from_the_report():
    report = _report()
    fm = _parse_frontmatter(build_field_note(report))
    assert fm["run_id"] == report.run.id
    assert fm["config_hash"] == report.run.config_hash
    assert fm["decision_question"] == report.run.brief.decision_question
    assert fm["dataset"]["id"] == report.run.dataset_id
    assert fm["dataset"]["name"] == report.run.dataset_name
    assert fm["rubric"]["kind"] == "exact"
    assert fm["rubric"]["threshold"] == 1.0
    assert fm["recommended"] == "Mock · good"  # mock_good passes 5/5
    assert [c["label"] for c in fm["candidates"]] == ["Mock · good", "Mock · bad"]


def test_fmt_check_true_for_format_kinds_false_otherwise():
    assert _parse_frontmatter(build_field_note(_report(Rubric(kind="exact", threshold=1.0))))["fmt_check"] is True
    assert _parse_frontmatter(build_field_note(_report(Rubric(kind="contains"))))["fmt_check"] is True
    assert _parse_frontmatter(build_field_note(_report(Rubric(kind="similarity"))))["fmt_check"] is False
    assert _parse_frontmatter(build_field_note(_report(Rubric(kind="keypoint"))))["fmt_check"] is False


def test_no_winner_run_records_no_clear_winner():
    # mock_bad alone never passes the exact check → no recommended candidate.
    report = run_proof(
        run_id="run_lose",
        created_at="2026-06-19T12:00:00Z",
        brief=_BRIEF,
        dataset=load_dataset("support-ticket-triage"),
        candidates=[Candidate(id="mock_bad", label="Mock · bad", provider_id="mock_bad")],
        rubric=Rubric(kind="exact", threshold=1.0),
    )
    fm = _parse_frontmatter(build_field_note(report))
    assert fm["recommended"] == "no clear winner"


# --- evidence body + narrative stub ----------------------------------------------------------


def test_reuses_the_receipt_evidence_body_not_a_copy():
    from orionfold.receipts import export

    report = _report()
    note = build_field_note(report)
    # The field note demotes the receipt's H1 to "## Evidence" but otherwise embeds it verbatim.
    receipt_md = export.to_markdown(report).replace("# Proof Receipt\n", "## Evidence\n", 1)
    assert receipt_md in note
    assert "## Leaderboard" in note  # the receipt's own section survived


def test_narrative_stub_is_a_placeholder_the_package_does_not_fill():
    note = build_field_note(_report())
    assert "## Why this can be trusted" in note
    assert "<!-- author: replace this section -->" in note


def test_field_note_has_a_single_h1_titled_by_the_decision():
    note = build_field_note(_report())
    # Scope to the body after the frontmatter — "# …" lines inside the --- fence are YAML
    # comments, not Markdown headings.
    body = note[note.index("\n---", 4) + 4 :]
    h1s = [ln for ln in body.splitlines() if ln.startswith("# ")]
    assert h1s == ["# Which model do I trust to triage tickets?"]


# --- figures ---------------------------------------------------------------------------------


def test_both_figures_present_and_parse_as_xml():
    report = _report()
    for svg in (pareto_svg(report), pass_rate_svg(report)):
        assert "<figure" in svg and "<svg" in svg
        # Our SVG is generated from the report (trusted) and must never carry a DOCTYPE or
        # entity declaration — assert that, then parse to confirm the markup is well-formed.
        # (No untrusted XML reaches this parser, so the stdlib XXE surface is not in play.)
        assert "<!DOCTYPE" not in svg and "<!ENTITY" not in svg
        inner = svg[svg.index("<svg") : svg.index("</svg>") + len("</svg>")]
        ET.fromstring(inner)  # raises on malformed XML


def test_scatter_accent_only_on_recommended():
    # mock_good is recommended (the only --color-accent); mock_bad is status-toned (danger).
    svg = pareto_svg(_report())
    assert svg.count("var(--color-accent)") == 1
    assert "var(--color-danger)" in svg  # the 0% loser


def test_pass_rate_bars_use_color_ok_for_non_recommended():
    # The recommended bar is the only accent; every other bar is --color-ok (PASS green).
    svg = pass_rate_svg(_report())
    assert svg.count("var(--color-accent)") == 1  # exactly the recommended bar
    assert "var(--color-ok)" in svg  # the non-recommended candidate's bar


def test_pass_rate_bars_omitted_on_unscored_quick_run():
    assert pass_rate_svg(_quick_report()) == ""


def test_scatter_degrades_without_a_frontier_line_when_nothing_dominates():
    # Two same-cost ($0) mock candidates → no cost spread → no dashed frontier polyline.
    svg = pareto_svg(_report())
    assert "<polyline" not in svg


def test_figures_have_accessibility_attributes():
    svg = pareto_svg(_report())
    assert 'role="img"' in svg
    assert "aria-label=" in svg
    assert "<title>" in svg
    assert "<figcaption>" in svg


# --- chart polish (v12 receipt redesign) -----------------------------------------------------

def test_scatter_has_a_subtle_grid_behind_the_dots():
    svg = pareto_svg(_report())
    # Faint gridlines are drawn with a low opacity so they read as background structure.
    assert 'opacity="0.22"' in svg


def test_scatter_shows_a_visible_label_next_to_each_dot():
    # Beyond the <title> hover, each candidate gets a visible short label by its dot.
    svg = pareto_svg(_report())
    # The mock candidates' short labels (tail after the last "/" or "·") appear as <text>.
    assert "<text" in svg
    # Two candidates → at least the two dot labels plus the two axis labels.
    assert svg.count("<text") >= 4


def test_pass_rate_bars_have_subtle_gridlines():
    svg = pass_rate_svg(_report())
    assert 'opacity="0.28"' in svg


def test_pass_rate_bar_height_is_capped_for_few_candidates():
    # A single-candidate bar must not fill the whole plot — the cap keeps it calm/readable.
    from orionfold.domain.models import (
        Candidate, LeaderboardEntry, ProofBrief, ProofReport, ProofRun, Rubric, RunCostSummary,
    )
    run = ProofRun(
        id="run_one", brief=ProofBrief(task_name="t", decision_question="q"),
        dataset_id="d", dataset_name="D", rubric=Rubric(threshold=0.8),
        candidates=[Candidate(id="solo", label="hf.co/Orionfold/Advisor-GGUF", provider_id="ollama")],
        config_hash="abc123abc123", created_at="2026-06-27T00:00:00Z",
    )
    lb = [LeaderboardEntry(candidate_id="solo", label="hf.co/Orionfold/Advisor-GGUF",
                           provider_id="ollama", privacy="local", total=21, pass_count=18,
                           pass_rate=18 / 21, avg_score=0.86, avg_latency_ms=3000,
                           total_estimated_cost_usd=0.0, error_count=0, failure_count=3,
                           recommended=True)]
    report = ProofReport(run=run, leaderboard=lb, results=[],
                         cost_summary=RunCostSummary(candidate_cost_usd=0, judge_cost_usd=0, total_cost_usd=0))
    svg = pass_rate_svg(report)
    import re
    heights = [float(h) for h in re.findall(r'<rect[^>]*height="([\d.]+)"', svg)]
    assert heights and max(heights) <= 26.0  # capped, not the full ~160px inner height


# --- determinism -----------------------------------------------------------------------------


def test_field_note_is_byte_deterministic():
    a = build_field_note(_report())
    b = build_field_note(_report())
    assert a == b


def test_figures_are_byte_deterministic():
    report = _report()
    assert pareto_svg(report) == pareto_svg(report)
    assert pass_rate_svg(report) == pass_rate_svg(report)


# --- graceful degrade on quick / no-winner ---------------------------------------------------


def test_quick_run_builds_a_field_note_with_no_bars_but_a_scatter():
    note = build_field_note(_quick_report())
    assert "artifact: proof-field-note" in note
    assert "## Why this can be trusted" in note  # stub still present
    assert "<svg" in note  # the scatter still renders (dots, no frontier)


# --- secret-free -----------------------------------------------------------------------------


def test_field_note_is_secret_free():
    note = build_field_note(_report())
    lowered = note.lower()
    # Key/auth *shapes* only — not English nouns. Dataset content legitimately contains words
    # like "password" (a ticket about a password reset), so matching the bare noun would be a
    # false positive; we match the markers an actual leaked credential carries.
    for needle in ("sk-ant-", "sk-", "api_key=", "api-key:", "bearer ", "authorization:"):
        assert needle not in lowered, f"field note leaked a secret-shaped token: {needle}"


def test_frontmatter_does_not_emit_judge_provider_internals():
    # A judge rubric carries a provider id + model; the spine records the rubric kind/threshold
    # but the field note must never surface a key or auth header. (Smoke over a judge-shaped run.)
    report = _report(Rubric(kind="similarity", threshold=0.55))
    fm = _frontmatter(report)
    assert "authorization" not in fm.lower()
    assert "api_key" not in fm.lower()
