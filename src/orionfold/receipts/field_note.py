"""Proof **field note** — a receipt-derived, shareable trust narrative scaffold.

A field note wraps a real Proof Receipt in a publish-ready Markdown document: YAML
frontmatter (the loop's state-machine spine), the receipt's own evidence body (verdict,
leaderboard, cost, failure cases, repro — reused from :mod:`orionfold.receipts.export`, never
re-implemented), two inline SVG figures (:mod:`orionfold.receipts.figures`), and a narrative
*stub* the operator fills in by hand.

The package **never authors the narrative** — it emits structured, secret-free evidence and
leaves a clearly-marked placeholder. That boundary is load-bearing: the public export is an
end-user capability (a consultant can share *"why I chose this model for this task"*); the
private authoring/publish skill (Layer B) is what turns the stub into prose.

Frontmatter is **hand-rendered** (not ``yaml.dump``) so the output is byte-deterministic and
``import orionfold`` carries no YAML dependency. Every value is derived from the
``ProofReport`` — nothing is invented.
"""

from __future__ import annotations

from orionfold.domain.models import ProofReport
from orionfold.receipts import export
from orionfold.receipts.figures import pareto_svg, pass_rate_svg

# Rubric kinds that grade *format*, not correctness — the ADR-0005 §4 honesty flag. An exact/
# contains match proves the output is shaped right, not that it's the right answer.
_FMT_CHECK_KINDS = frozenset({"exact", "contains"})

_NARRATIVE_STUB = """\
## Why this can be trusted

<!-- author: replace this section -->

_The evidence above is generated and repeatable. Write the trust narrative here — why this
result is worth acting on, what the decision was, and any caveats a reader should weigh._

<!-- /author -->"""


def _yaml_str(value: str) -> str:
    """Quote a scalar for YAML only when needed; always double-quote to stay deterministic."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _frontmatter(report: ProofReport) -> str:
    """Hand-render the §4 frontmatter spine — deterministic, derived-only, valid YAML."""
    run = report.run
    rubric = run.rubric
    top = report.leaderboard[0] if report.leaderboard else None
    # Read the leaderboard's own verdict (single source of truth) rather than re-derive it —
    # the recommended entry is what the receipt names, so the field note can never disagree.
    winner = next((e for e in report.leaderboard if e.recommended), None)
    recommended = winner.label if winner is not None else "no clear winner"
    fmt_check = rubric.kind in _FMT_CHECK_KINDS
    title = run.brief.decision_question or run.brief.task_name

    lines: list[str] = [
        "---",
        "artifact: proof-field-note",
        f"title: {_yaml_str(title)}",
        f"date: {_yaml_str(run.created_at[:10])}",
        f"summary: {_yaml_str(export._recommendation_line(top) if top else 'No candidates ran.')}",
        "# --- proof provenance (the spine) ---",
        f"run_id: {_yaml_str(run.id)}",
        f"config_hash: {_yaml_str(run.config_hash)}",
        f"decision_question: {_yaml_str(run.brief.decision_question)}",
        f"dataset: {{ id: {_yaml_str(run.dataset_id)}, name: {_yaml_str(run.dataset_name)} }}",
        f"rubric: {{ kind: {_yaml_str(rubric.kind)}, threshold: {export.json.dumps(rubric.threshold)} }}",
        f"recommended: {_yaml_str(recommended)}",
        f"fmt_check: {str(fmt_check).lower()}   # format check, not correctness (ADR-0005 §4)",
        "# --- cross-platform feasibility record (ADR-0005 §3) ---",
        "candidates:",
    ]
    for c in run.candidates:
        model = _yaml_str(c.model) if c.model else "null"
        lines.append(
            f"  - {{ label: {_yaml_str(c.label)}, provider_id: {_yaml_str(c.provider_id)}, "
            f"privacy: {_yaml_str(c.privacy)}, model: {model} }}"
        )
    lines += [
        f"cost_usd: {export.json.dumps(round(report.cost_summary.total_cost_usd, 6))}",
        f"tags: [proof, {rubric.kind}]",
        "---",
    ]
    return "\n".join(lines)


def _evidence_body(report: ProofReport) -> str:
    """The receipt's own Markdown, with its H1 demoted so the field note owns the title."""
    md = export.to_markdown(report)
    # to_markdown opens with "# Proof Receipt"; the field note already has an H1, so demote it
    # to an H2 "## Evidence" section rather than carry two H1s.
    return md.replace("# Proof Receipt\n", "## Evidence\n", 1)


def build_field_note(report: ProofReport) -> str:
    """Compose a publish-ready field note from a stored ``ProofReport``.

    Frontmatter spine + receipt evidence body + two inline SVG figures + a narrative stub.
    Pure: no DB, no HTTP, no browser. Secret-free by construction (reads only the stored
    report, which already excludes keys/config). Figures degrade gracefully on quick/no-winner
    runs (pass-rate bars omitted when unscored; the scatter draws dots with no frontier when
    nothing dominates).
    """
    run = report.run
    title = run.brief.decision_question or run.brief.task_name

    sections: list[str] = [_frontmatter(report), "", f"# {title}", ""]

    # Figures first — the visual proof — then the receipt evidence, then the narrative stub.
    figures = [pareto_svg(report)]
    bars = pass_rate_svg(report)
    if bars:
        figures.append(bars)
    if figures:
        sections += ["## Figures", "", *_interleave(figures), ""]

    sections += [_evidence_body(report), "", _NARRATIVE_STUB, ""]
    return "\n".join(sections)


def _interleave(blocks: list[str]) -> list[str]:
    """Join figure blocks with a blank line between them (one list entry per line group)."""
    out: list[str] = []
    for i, block in enumerate(blocks):
        if i:
            out.append("")
        out.append(block)
    return out
