"""Proof Receipt exporter (enforced by .claude/rules/receipts.md).

The receipt is the central, protected product artifact. Every format carries a schema
``version``, the run's ``config_hash``, and a ``created_at`` timestamp so it is repeatable and
verifiable. Receipts expose only provider ids and the local/cloud boundary — never API keys,
secrets, or full provider config. Bump ``RECEIPT_VERSION`` on any schema change.
"""

from __future__ import annotations

import html
import json

from orionfold.domain.models import LeaderboardEntry, ProofReport, ResultRow

# v2: added verdict, summary, and a repro section (run id + rerun command).
# v3: leaderboard entries carry a `model` field (the candidate's model for real providers).
# v4: leaderboard entries carry an `error_count` field; a fully-errored candidate ranks last
# and is never recommended, and the receipt shows a "No clear winner" state when none passed.
# Bump on any schema change so downstream consumers can detect drift.
RECEIPT_VERSION = 4


def _verdict(top: LeaderboardEntry) -> str:
    """One categorical verdict from a controlled vocabulary, derived from the pass rate."""
    if top.pass_rate >= 0.9:
        return "Ship"
    if top.pass_rate >= 0.6:
        return "Ship with fallback"
    if top.pass_rate >= 0.3:
        return "Keep testing"
    return "Reject"


def _recommendation_line(top: LeaderboardEntry) -> str:
    return (
        f"{top.label} ({top.provider_id}) — passed {top.pass_count}/{top.total} "
        f"({top.pass_rate:.0%}), avg latency {top.avg_latency_ms}ms, "
        f"est. cost ${top.total_estimated_cost_usd:.2f}, {top.privacy}."
    )


def _failure_cases(report: ProofReport) -> list[ResultRow]:
    return [r for r in report.results if not r.passed]


def _failures_label(e: dict) -> str:
    """Annotate a fully-errored candidate so the standings read honestly."""
    if e["total"] and e["error_count"] == e["total"]:
        return f"{e['failure_count']} (errored, no output)"
    return str(e["failure_count"])


def _md_cell(text: str) -> str:
    """Neutralize text for a Markdown table cell so dataset content can't break the table."""
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").strip()


def _md_inline(text: str) -> str:
    """Collapse newlines so multi-line dataset text stays inside its bullet."""
    return " ".join(text.split())


def build_receipt(report: ProofReport) -> dict:
    """Canonical receipt data — the single structure every format renders from."""
    run = report.run
    top = report.leaderboard[0] if report.leaderboard else None
    has_winner = top is not None and top.pass_count > 0
    candidate_ids = [c.id for c in run.candidates]
    summary = (
        f"{len(run.candidates)} candidate(s) × {len(report.results) // max(len(run.candidates), 1)} "
        f"example(s) · rubric {run.rubric.kind} ≥ {run.rubric.threshold}"
    )
    return {
        "receipt_version": RECEIPT_VERSION,
        "run_id": run.id,
        "config_hash": run.config_hash,
        "created_at": run.created_at,
        "brief": run.brief.model_dump(),
        "dataset": {"id": run.dataset_id, "name": run.dataset_name},
        "rubric": run.rubric.model_dump(),
        "summary": summary,
        "verdict": _verdict(top) if has_winner else ("No clear winner" if top else "No run"),
        "recommendation": (
            _recommendation_line(top)
            if has_winner
            else (
                f"No candidate passed the rubric (threshold {run.rubric.threshold:.2f})."
                if top
                else "No candidates were run."
            )
        ),
        "leaderboard": [e.model_dump() for e in report.leaderboard],
        "failure_cases": [r.model_dump() for r in _failure_cases(report)],
        "repro": {
            "run_id": run.id,
            "config_hash": run.config_hash,
            "created_at": run.created_at,
            "dataset_id": run.dataset_id,
            "candidate_ids": candidate_ids,
            "rubric": run.rubric.model_dump(),
            "rerun": (
                "POST /api/runs "
                f'{{"dataset_id": "{run.dataset_id}", "candidate_ids": {candidate_ids}}}'
            ),
        },
    }


def to_json(report: ProofReport) -> str:
    """Machine-readable receipt — the canonical structure as pretty JSON."""
    return json.dumps(build_receipt(report), indent=2, ensure_ascii=False)


def to_markdown(report: ProofReport) -> str:
    """Human, client-shareable receipt in Markdown."""
    data = build_receipt(report)
    brief = data["brief"]
    repro = data["repro"]
    lines: list[str] = [
        "# Proof Receipt",
        "",
        f"**Verdict: {data['verdict']}** — {data['recommendation']}",
        "",
        f"_{data['summary']}_",
        "",
        f"- **Decision:** {brief['decision_question']}",
        f"- **Task:** {brief['task_name']}",
        f"- **Dataset:** {data['dataset']['name']} (`{data['dataset']['id']}`)",
        f"- **Rubric:** {data['rubric']['kind']} ≥ {data['rubric']['threshold']}",
        f"- **Run id:** `{data['run_id']}`",
        f"- **Config hash:** `{data['config_hash']}`",
        f"- **Generated:** {data['created_at']}",
        f"- **Receipt schema:** v{data['receipt_version']}",
        "",
        "## Leaderboard",
        "",
        "| Candidate | Provider | Privacy | Pass rate | Avg score | Avg latency | Est. cost | Failures |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for e in data["leaderboard"]:
        marker = " ⭐" if e["recommended"] else ""
        lines.append(
            f"| {_md_cell(e['label'])}{marker} | {_md_cell(e['provider_id'])} | "
            f"{_md_cell(e['privacy'])} | "
            f"{e['pass_rate']:.0%} ({e['pass_count']}/{e['total']}) | {e['avg_score']:.2f} | "
            f"{e['avg_latency_ms']}ms | ${e['total_estimated_cost_usd']:.2f} | {_failures_label(e)} |"
        )

    failures = data["failure_cases"]
    lines += ["", f"## Failure cases ({len(failures)})", ""]
    if not failures:
        lines.append("_No failures — every candidate passed every example._")
    for f in failures:
        reason = f"error: {f['error']}" if f["error"] else f"score {f['score']:.2f}"
        lines += [
            f"- **{f['candidate_id']}** · example {f['example_index']} · {reason}",
            f"  - input: {_md_inline(f['input_text'])}",
            f"  - expected: {_md_inline(f['expected_text'])}",
            f"  - output: {_md_inline(f['output_text']) or '—'}",
        ]

    lines += [
        "",
        "## Repro",
        "",
        f"- **Run id:** `{repro['run_id']}`",
        f"- **Config hash:** `{repro['config_hash']}` (identical inputs reproduce this hash)",
        f"- **Generated:** {repro['created_at']}",
        f"- **Rerun:** `{repro['rerun']}`",
        "",
    ]
    return "\n".join(lines)


def to_html(report: ProofReport, theme: str | None = None) -> str:
    """Self-contained HTML receipt (no external assets), calm and readable."""
    data = build_receipt(report)
    brief = data["brief"]

    rows = "".join(
        "<tr>"
        f"<td>{html.escape(e['label'])}{' ⭐' if e['recommended'] else ''}</td>"
        f"<td>{html.escape(e['provider_id'])}</td>"
        f"<td>{html.escape(e['privacy'])}</td>"
        f"<td>{e['pass_rate']:.0%} ({e['pass_count']}/{e['total']})</td>"
        f"<td>{e['avg_score']:.2f}</td>"
        f"<td>{e['avg_latency_ms']}ms</td>"
        f"<td>${e['total_estimated_cost_usd']:.2f}</td>"
        f"<td>{html.escape(_failures_label(e))}</td>"
        "</tr>"
        for e in data["leaderboard"]
    )

    failures = data["failure_cases"]
    if failures:
        items = "".join(
            "<li><strong>{cid}</strong> · example {idx} · {reason}"
            "<div class='case'><span>input</span> {inp}</div>"
            "<div class='case'><span>expected</span> {exp}</div>"
            "<div class='case'><span>output</span> {out}</div></li>".format(
                cid=html.escape(f["candidate_id"]),
                idx=f["example_index"],
                reason=html.escape(
                    f"error: {f['error']}" if f["error"] else f"score {f['score']:.2f}"
                ),
                inp=html.escape(f["input_text"]),
                exp=html.escape(f["expected_text"]),
                out=html.escape(f["output_text"] or "—"),
            )
            for f in failures
        )
        failures_html = f"<ul class='failures'>{items}</ul>"
    else:
        failures_html = "<p class='muted'>No failures — every candidate passed every example.</p>"

    return f"""<!doctype html>
<html lang="en"{f' data-theme="{theme}"' if theme in ("light", "dark") else ""}>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Proof Receipt · {html.escape(data['dataset']['name'])}</title>
<style>
  :root {{
    color-scheme: light dark;
    --rc-bg: #0b0f14; --rc-ink: #e6edf3; --rc-muted: #9fb0c0; --rc-line: #1c2530;
    --rc-rec-bg: #11331f; --rc-rec-line: #1f5135; --rc-rec-ink: #c8f5da;
    --rc-case: #c4d0db; --rc-case-key: #6f8190;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{
      --rc-bg: #f4f6f8; --rc-ink: #1b2430; --rc-muted: #51616f; --rc-line: #dde3ea;
      --rc-rec-bg: #e7f7ee; --rc-rec-line: #b6e6cb; --rc-rec-ink: #0f5132;
      --rc-case: #2b3744; --rc-case-key: #5f6e80;
    }}
  }}
  :root[data-theme="dark"] {{
    --rc-bg: #0b0f14; --rc-ink: #e6edf3; --rc-muted: #9fb0c0; --rc-line: #1c2530;
    --rc-rec-bg: #11331f; --rc-rec-line: #1f5135; --rc-rec-ink: #c8f5da;
    --rc-case: #c4d0db; --rc-case-key: #6f8190;
  }}
  :root[data-theme="light"] {{
    --rc-bg: #f4f6f8; --rc-ink: #1b2430; --rc-muted: #51616f; --rc-line: #dde3ea;
    --rc-rec-bg: #e7f7ee; --rc-rec-line: #b6e6cb; --rc-rec-ink: #0f5132;
    --rc-case: #2b3744; --rc-case-key: #5f6e80;
  }}
  body {{ margin: 0; font: 15px/1.6 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
         background: var(--rc-bg); color: var(--rc-ink); }}
  main {{ max-width: 56rem; margin: 0 auto; padding: 2.5rem 1.5rem; }}
  h1 {{ font-size: 1.5rem; letter-spacing: -0.01em; margin: 0 0 0.25rem; }}
  .rec {{ background: var(--rc-rec-bg); border: 1px solid var(--rc-rec-line); color: var(--rc-rec-ink);
          padding: 0.9rem 1rem; border-radius: 10px; margin: 1rem 0 1.5rem; }}
  dl {{ display: grid; grid-template-columns: max-content 1fr; gap: 0.2rem 1rem; margin: 0 0 1.5rem; }}
  dt {{ color: var(--rc-muted); }} dd {{ margin: 0; }}
  table {{ width: 100%; border-collapse: collapse; margin: 0.5rem 0 1.5rem; }}
  th, td {{ text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--rc-line); }}
  th {{ color: var(--rc-muted); font-weight: 600; }}
  code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
  .muted {{ color: var(--rc-muted); }}
  ul.failures {{ list-style: none; padding: 0; }}
  ul.failures > li {{ border: 1px solid var(--rc-line); border-radius: 10px; padding: 0.8rem 1rem; margin: 0.6rem 0; }}
  .case {{ color: var(--rc-case); margin-top: 0.25rem; }}
  .case > span {{ color: var(--rc-case-key); display: inline-block; min-width: 4.5rem; }}
</style>
</head>
<body>
<main>
  <h1>Proof Receipt</h1>
  <p class="muted">{html.escape(brief['task_name'])}</p>
  <div class="rec"><strong>Verdict: {html.escape(data['verdict'])}</strong> — {html.escape(data['recommendation'])}</div>
  <p class="muted">{html.escape(data['summary'])}</p>
  <dl>
    <dt>Decision</dt><dd>{html.escape(brief['decision_question'])}</dd>
    <dt>Dataset</dt><dd>{html.escape(data['dataset']['name'])} (<code>{html.escape(data['dataset']['id'])}</code>)</dd>
    <dt>Rubric</dt><dd>{html.escape(data['rubric']['kind'])} ≥ {data['rubric']['threshold']}</dd>
    <dt>Run id</dt><dd><code>{html.escape(data['run_id'])}</code></dd>
    <dt>Config hash</dt><dd><code>{html.escape(data['config_hash'])}</code></dd>
    <dt>Generated</dt><dd>{html.escape(data['created_at'])}</dd>
    <dt>Receipt schema</dt><dd>v{data['receipt_version']}</dd>
  </dl>
  <h2>Leaderboard</h2>
  <table>
    <thead><tr>
      <th>Candidate</th><th>Provider</th><th>Privacy</th><th>Pass rate</th>
      <th>Avg score</th><th>Avg latency</th><th>Est. cost</th><th>Failures</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <h2>Failure cases ({len(failures)})</h2>
  {failures_html}
  <h2>Repro</h2>
  <dl>
    <dt>Run id</dt><dd><code>{html.escape(data['repro']['run_id'])}</code></dd>
    <dt>Config hash</dt><dd><code>{html.escape(data['repro']['config_hash'])}</code></dd>
    <dt>Rerun</dt><dd><code>{html.escape(data['repro']['rerun'])}</code></dd>
  </dl>
</main>
</body>
</html>
"""
