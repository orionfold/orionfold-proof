"""Standalone (extract-to-`<img>`) SVG mode for the receipt-article publish path.

The receipt-article EXTRACTS the two figures to `.svg` files the website references as
`<img src>` — an isolated render context that (a) hard-errors in Astro's `image()` unless the
file ROOT is `<svg>` (no `<figure>` wrapper), and (b) cannot read page CSS variables, so
`var(--color-*)` paints invisible. `standalone=True` emits a bare `<svg>` root with literal,
theme-neutral hex baked in. The default (inline) output stays byte-identical — the field note
and the receipt HTML still theme with the page.
"""

import xml.etree.ElementTree as ET

from orionfold.data import load_dataset
from orionfold.domain.models import Candidate, ProofBrief, Rubric
from orionfold.proof.engine import run_proof
from orionfold.receipts.figures import pareto_svg, pass_rate_svg

_BRIEF = ProofBrief(
    task_name="Support ticket triage",
    decision_question="Which model do I trust to triage tickets?",
    success_criteria="Exact label match.",
)

# The literal hex the website proved renders on BOTH light + dark (an <img>-SVG can't be
# theme-reactive). Kept here as the frozen contract for the standalone palette.
_HEX = {
    "ink-faint": "#9aa1ab",
    "ink-muted": "#6b7280",
    "accent": "#14c8c0",
    "ok": "#3fd55a",
}


def _report():
    return run_proof(
        run_id="run_standalone",
        created_at="2026-06-19T12:00:00Z",
        brief=_BRIEF,
        dataset=load_dataset("support-ticket-triage"),
        candidates=[
            Candidate(id="mock_good", label="Mock · good", provider_id="mock_good"),
            Candidate(id="mock_bad", label="Mock · bad", provider_id="mock_bad"),
        ],
        rubric=Rubric(kind="exact", threshold=1.0),
    )


# --- bare <svg> root (no figure wrapper) -----------------------------------------------------


def test_standalone_emits_a_bare_svg_root():
    for svg in (pareto_svg(_report(), standalone=True), pass_rate_svg(_report(), standalone=True)):
        assert svg.startswith("<svg")
        assert svg.rstrip().endswith("</svg>")
        assert "<figure" not in svg
        assert "<figcaption" not in svg


def test_standalone_still_parses_as_xml_and_keeps_a11y():
    svg = pareto_svg(_report(), standalone=True)
    root = ET.fromstring(svg)  # the bare root must be a valid <svg> element
    assert root.tag.endswith("svg")
    assert 'role="img"' in svg and "aria-label=" in svg and "<title>" in svg


# --- literal hex, no CSS vars ----------------------------------------------------------------


def test_standalone_inlines_literal_hex_and_drops_css_vars():
    for svg in (pareto_svg(_report(), standalone=True), pass_rate_svg(_report(), standalone=True)):
        assert "var(--" not in svg
    # The recommended pick fills with the brand cyan; bars/dots use the proven hex.
    scatter = pareto_svg(_report(), standalone=True)
    bars = pass_rate_svg(_report(), standalone=True)
    assert _HEX["accent"] in scatter  # recommended dot
    assert _HEX["ink-muted"] in scatter  # label text (WCAG-legible on light)
    assert _HEX["ink-faint"] in scatter  # gridlines/axes
    assert _HEX["accent"] in bars  # recommended bar
    assert _HEX["ok"] in bars  # non-recommended PASS-green bar


def test_standalone_frontier_polyline_uses_hex_not_var():
    # The two mock candidates are both $0, so the default report draws no frontier line. A real
    # cost spread (a priced cloud candidate) DOES draw the dashed polyline — it must use hex, not
    # var(), in standalone mode (regression: it was the one stroke that leaked a var()).
    from orionfold.domain.models import (
        LeaderboardEntry, ProofBrief, ProofReport, ProofRun, Rubric, RunCostSummary,
    )

    run = ProofRun(
        id="run_spread", brief=ProofBrief(task_name="t", decision_question="q"),
        dataset_id="d", dataset_name="D", rubric=Rubric(threshold=0.8),
        candidates=[], config_hash="abc123abc123", created_at="2026-06-27T00:00:00Z",
    )
    # A genuine cost-vs-quality tradeoff so ≥2 points sit ON the frontier (the cheap-but-lower and
    # the pricier-but-higher both non-dominated) — that's what draws the connecting polyline.
    lb = [
        LeaderboardEntry(
            candidate_id="cheap", label="cheap", provider_id="ollama", privacy="local",
            total=21, pass_count=15, pass_rate=15 / 21, avg_score=0.71, avg_latency_ms=3000,
            total_estimated_cost_usd=0.0, error_count=0, failure_count=6, recommended=False,
        ),
        LeaderboardEntry(
            candidate_id="best", label="best", provider_id="anthropic", privacy="cloud",
            total=21, pass_count=20, pass_rate=20 / 21, avg_score=0.95, avg_latency_ms=2000,
            total_estimated_cost_usd=0.34, error_count=0, failure_count=1, recommended=True,
        ),
    ]
    report = ProofReport(
        run=run, leaderboard=lb, results=[],
        cost_summary=RunCostSummary(candidate_cost_usd=0.34, judge_cost_usd=0, total_cost_usd=0.34),
    )
    svg = pareto_svg(report, standalone=True)
    assert "<polyline" in svg  # a real cost spread draws the frontier
    assert "var(--" not in svg  # and every stroke is baked hex, including the polyline


def test_standalone_is_byte_deterministic():
    report = _report()
    assert pareto_svg(report, standalone=True) == pareto_svg(report, standalone=True)
    assert pass_rate_svg(report, standalone=True) == pass_rate_svg(report, standalone=True)


# --- the default (inline) path is untouched --------------------------------------------------


def test_default_inline_output_is_unchanged():
    for svg in (pareto_svg(_report()), pass_rate_svg(_report())):
        assert "<figure" in svg and "<figcaption" in svg
        assert "var(--color-" in svg
        # No standalone hex leaks into the themed inline output.
        for hex_value in _HEX.values():
            assert hex_value not in svg
