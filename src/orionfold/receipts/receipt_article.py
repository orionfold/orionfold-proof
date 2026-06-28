"""Proof **receipt-article** — a receipt-derived scaffold for the website /receipts gallery.

The /story twin (:mod:`orionfold.receipts.field_note`) inlines its SVG figures; the
receipt-article instead leaves figure REFERENCES (the emit helper extracts the SVGs to
files, matching the website's src/assets/receipts/<slug>/ convention). Like the field note,
the package emits derived-only, secret-free evidence + a DETERMINISTIC sample table and a
narrative *stub*; the human authors the prose. Frontmatter matches the website `receipts`
collection schema (title/metric/claim/dek/date/tags/relatedTo/source/verify).
"""

from __future__ import annotations

from orionfold.domain.models import ProofReport, ResultRow
from orionfold.receipts import export

_NARRATIVE_STUB = """\
## Why this can be trusted

<!-- author: replace this section -->

_The evidence above is generated and repeatable. Write the trust narrative here — why this
result is worth acting on, what the decision was, and any caveats a reader should weigh._

<!-- /author -->"""

_MAX_SAMPLE_ROWS = 5


def _yaml_str(value: str) -> str:
    """Quote a scalar for YAML; always double-quote to stay deterministic."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _winner(report: ProofReport):
    return next((e for e in report.leaderboard if e.recommended), None)


def _metric_seed(report: ProofReport) -> str:
    """A candidate 'number that pops' for the operator to refine; never invented beyond the run."""
    w = _winner(report)
    if w is None:
        return "no clear winner"
    return f"{w.pass_count}/{w.total} · {w.pass_rate:.0%}"


def _sample_rows(report: ProofReport) -> list[ResultRow]:
    """Deterministic representative sample: failures first (up to 3), then passes, <=5 rows.

    Stable order by (example_index, candidate_id). 'Failure' = passed is False (an honest
    absence, None, is treated as non-failure)."""
    ordered = sorted(report.results, key=lambda r: (r.example_index, r.candidate_id))
    failures = [r for r in ordered if r.passed is False]
    passes = [r for r in ordered if r.passed is not False]
    return (failures[:3] + passes)[:_MAX_SAMPLE_ROWS]


def _cell(text: str, *, limit: int = 80) -> str:
    """One-line, pipe-safe Markdown table cell."""
    flat = " ".join(text.split())
    if len(flat) > limit:
        flat = flat[: limit - 1].rstrip() + "…"
    return flat.replace("|", "\\|")


def _sample_table(report: ProofReport) -> str:
    rows = _sample_rows(report)
    if not rows:
        return ""
    out = [
        "## Examples (sampled)",
        "",
        "| # | Input | Expected | Output | Result |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        verdict = "pass" if r.passed else ("fail" if r.passed is False else "—")
        out.append(
            f"| {r.example_index} | {_cell(r.input_text)} | {_cell(r.expected_text)} "
            f"| {_cell(r.output_text)} | {verdict} |"
        )
    return "\n".join(out)


def _receipts_frontmatter(report: ProofReport) -> str:
    run = report.run
    top = report.leaderboard[0] if report.leaderboard else None
    w = _winner(report)
    recommended = w.label if w is not None else "no clear winner"
    title = run.brief.decision_question or run.brief.task_name
    claim = export._recommendation_line(top) if top else "No candidates ran."
    verify = (
        f"Rerun: orionfold proof against dataset {run.dataset_name} "
        f"(config hash {run.config_hash})."
    )
    lines = [
        "---",
        "artifact: proof-receipt-article",
        f"title: {_yaml_str(title)}",
        f"metric: {_yaml_str(_metric_seed(report))}",
        f"claim: {_yaml_str(claim)}",
        f"dek: {_yaml_str(claim)}",
        f"date: {_yaml_str(run.created_at[:10])}",
        f"tags: [proof, {run.rubric.kind}]",
        "relatedTo: []",
        "source: []",
        f"verify: {_yaml_str(verify)}",
        "# --- proof provenance (not rendered by the receipts schema, tolerated) ---",
        f"run_id: {_yaml_str(run.id)}",
        f"config_hash: {_yaml_str(run.config_hash)}",
        f"recommended: {_yaml_str(recommended)}",
        "---",
    ]
    return "\n".join(lines)


def _evidence_body(report: ProofReport) -> str:
    md = export.to_markdown(report)
    return md.replace("# Proof Receipt\n", "## Evidence\n", 1)


def build_receipt_article(report: ProofReport) -> str:
    """Compose a /receipts-ready scaffold: frontmatter + figure refs + evidence + sample table + stub.

    Pure: no DB, no HTTP, no browser. Secret-free by construction. Figure REFERENCES point at
    assets the emit helper extracts; the body never inlines SVG.
    """
    run = report.run
    title = run.brief.decision_question or run.brief.task_name
    sections = [
        _receipts_frontmatter(report),
        "",
        f"# {title}",
        "",
        "## Figures",
        "",
        "![Cost vs quality](./assets/cost-quality.svg)",
        "",
        "![Pass rate](./assets/pass-rate.svg)",
        "",
        _evidence_body(report),
        "",
    ]
    table = _sample_table(report)
    if table:
        sections += [table, ""]
    sections += [_NARRATIVE_STUB, ""]
    return "\n".join(sections)
