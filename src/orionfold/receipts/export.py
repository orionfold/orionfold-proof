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
from orionfold.receipts.figures import pareto_svg, pass_rate_svg
from orionfold.receipts.retrieved_context import parse_retrieved_context
from orionfold.scoring.review import review_report

# v2: added verdict, summary, and a repro section (run id + rerun command).
# v3: leaderboard entries carry a `model` field (the candidate's model for real providers).
# v4: leaderboard entries carry an `error_count` field; a fully-errored candidate ranks last
# and is never recommended, and the receipt shows a "No clear winner" state when none passed.
# v5: meaning-aware scoring — a "Scored by" descriptor (keypoint coverage / similarity / LLM
# judge · <model>) and a run-level cost summary (candidate + judge + total).
# v6: prompt-variant runs — each leaderboard entry carries its system_prompt; the receipt adds a
# "Prompt variants" section (name + full prompt text) for provenance. Empty for model-compare runs.
# v7: leaderboard entries carry a `cost_per_quality` field ($ per quality point); the receipt adds
# a "$ / quality" efficiency column. Presentation only — ranking is unchanged.
# v8: quick-compare runs — the receipt carries `mode` ("full"|"quick") and `chosen_winner`. A quick
# receipt is a single-example, un-scored, human-picked check: objective columns only (latency / cost
# / tokens), no failure cases, a "quick check — not scored proof" note, and a promote-to-full CTA.
# v9: governance bench — a new `bench` rubric kind scored deterministically (citation / refusal /
# route / no-leak), with NO threshold. The receipt's "Scored by" reads "Governance bench (…)", the
# summary drops the "≥ threshold" tail for bench, each leaderboard row carries a `tok/s` throughput
# column (the 32GB-Mac-vs-128GB-GB10 generalization metric; presentation only), and a bench failure
# case shows the per-gate verdict (citation/refusal/route/leak/residue) instead of a numeric score.
# v10: post-receipt verdict review — a deterministic, no-LLM self-audit that annotates a failed row
# whose verdict is *possibly* wrong: a false-positive (a bench leak that fired only on the heuristic
# opaque-token rule, on a clean refusal) or a false-negative (an exact/contains miss a stricter
# case/punctuation normalization would have flipped). Carried as a `verdict_review` list (empty when
# nothing flagged) and rendered inline under the affected failure case. Advisory only — the
# deterministic verdict stays authoritative; the review never changes pass/fail.
# v12: receipt VISUAL redesign — presentation only, the canonical `build_receipt()` dict is
# byte-identical to v11 (so `config_hash` and the JSON export are unchanged in shape/values). The
# HTML receipt gains a verdict hero (evidence eyebrow + metric headline + recommendation), the two
# inline SVG figures (pass-rate bars + cost-vs-quality scatter, reused from `figures` — full runs
# only, self-omitting on quick/unscored), a cost-ledger split block, and mono-uppercase section
# labels + a "Rerun it" provenance footer that mirror the orionfold.com receipts vocabulary (shared
# familiarity hooks across the cockpit and the website, each kept to its own genre). Markdown/JSON
# bodies are unchanged except the version number. Bump = the rendered HTML drifted, nothing else.
# Bump on any schema change so downstream consumers can detect drift.
RECEIPT_VERSION = 12


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
    # A quick check is unscored (passed is None), so there is no notion of a failure case.
    if report.run.mode == "quick":
        return []
    return [r for r in report.results if not r.passed]


def _quick_pick_lines(report: ProofReport) -> tuple[str, str]:
    """(verdict, recommendation) for a quick-compare run, driven by the human pick."""
    pick = report.run.chosen_winner
    if pick == "tie" or pick is None:
        return "Tie", "No clear winner — the two outputs were judged a tie."
    by_id = {c.id: c for c in report.run.candidates}
    cand = by_id.get(pick)
    label = cand.label if cand else pick
    provider = cand.provider_id if cand else "?"
    return f"Picked {label}", f"{label} ({provider}) — your pick on a single-example quick check."


def _failures_label(e: dict) -> str:
    """Annotate a fully-errored candidate so the standings read honestly."""
    if e["total"] and e["error_count"] == e["total"]:
        return f"{e['failure_count']} (errored, no output)"
    return str(e["failure_count"])


def _cost_per_quality_label(v: float | None) -> str:
    """Display rule for the $/quality efficiency cell, shared by MD and HTML."""
    if v is None:
        return "—"
    if v == 0:
        return "Free"
    return f"${v:.4f}"


def _tok_per_sec_label(v: float | None) -> str:
    """Display rule for the throughput cell (tok/s), shared by MD and HTML."""
    return "—" if v is None else f"{v:.1f}"


def _rubric_label(rubric: dict) -> str:
    """The 'Rubric:' metadata value, shared by MD and HTML. Bench is threshold-free, so it shows the
    kind alone — never a misleading '≥ 0.8' tail it doesn't use."""
    if rubric["kind"] == "bench":
        return "bench (deterministic)"
    return f"{rubric['kind']} ≥ {rubric['threshold']}"


def _bench_gate_summary(detail: dict) -> str:
    """One-line list of the FAILED governance gates for a bench failure case."""
    flags = [
        ("citation", not detail.get("citation_ok", True)),
        ("refusal", not detail.get("refusal_ok", True)),
        ("route", not detail.get("route_ok", True)),
        ("thinking-leak", detail.get("thinking_leak", False)),
        ("private-state-leak", detail.get("private_state_risk", False)),
    ]
    failed = [name for name, is_failed in flags if is_failed]
    return ", ".join(failed) if failed else "residue"


def _reviews_by_key(data: dict) -> dict[tuple[str, int], dict]:
    """Index the receipt's verdict_review list by (candidate_id, example_index) for inline lookup."""
    return {(r["candidate_id"], r["example_index"]): r for r in data.get("verdict_review", [])}


def _failure_reason(f: dict) -> str:
    """The base reason for one failure case (error / failed bench gates / numeric score)."""
    if f["error"]:
        return f"error: {f['error']}"
    if f.get("bench_detail"):
        return f"failed gate(s): {_bench_gate_summary(f['bench_detail'])}"
    return f"score {f['score']:.2f}"


def _review_suffix(review: dict | None) -> str:
    """The inline ' · review: …' tail appended to a failure case's reason, or '' when none.

    The deterministic verdict is rendered first and stays authoritative; this is a clearly-sourced,
    advisory second clause that never overrides it. Shared by Markdown and HTML (HTML escapes it).
    """
    if review is None:
        return ""
    label = "possible false-positive" if review["verdict"] == "false_positive" else "possible false-negative"
    return f" · review: {label} — {review['reason']}"


def _scored_by(rubric) -> str:
    """Human-readable descriptor for the rubric kind, safe to display in receipts."""
    if rubric.kind == "keypoint":
        return "Keypoint coverage"
    if rubric.kind == "judge":
        return f"LLM judge · {rubric.judge_model or rubric.judge_provider_id}"
    if rubric.kind == "bench":
        return "Governance bench (citation · refusal · route)"
    labels = {"similarity": "Similarity", "exact": "Exact match", "contains": "Contains"}
    return labels.get(rubric.kind) or rubric.kind


def _md_cell(text: str) -> str:
    """Neutralize text for a Markdown table cell so dataset content can't break the table."""
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").strip()


def _md_inline(text: str) -> str:
    """Collapse newlines so multi-line dataset text stays inside its bullet."""
    return " ".join(text.split())


def _rerun_command(run) -> str:
    """The POST body that reproduces this run — prompt-variant shape when variants are present."""
    variants = [
        {"name": c.label, "system_prompt": c.system_prompt}
        for c in run.candidates
        if c.system_prompt is not None
    ]
    if variants:
        model_id = run.candidates[0].id.split("#", 1)[0]
        body = {"dataset_id": run.dataset_id, "candidate_ids": [model_id], "prompt_variants": variants}
    else:
        body = {"dataset_id": run.dataset_id, "candidate_ids": [c.id for c in run.candidates]}
    return "POST /api/runs " + json.dumps(body, ensure_ascii=False)


def build_receipt(report: ProofReport) -> dict:
    """Canonical receipt data — the single structure every format renders from."""
    run = report.run
    top = report.leaderboard[0] if report.leaderboard else None
    has_winner = top is not None and top.pass_count > 0
    is_quick = run.mode == "quick"
    candidate_ids = [c.id for c in run.candidates]
    n_examples = len(report.results) // max(len(run.candidates), 1)
    if is_quick:
        summary = f"{len(run.candidates)} candidate(s) × {n_examples} example(s) · quick check (unscored)"
        verdict, recommendation = _quick_pick_lines(report)
    else:
        is_bench = run.rubric.kind == "bench"
        rubric_clause = (
            "governance bench (deterministic)"
            if is_bench
            else f"rubric {run.rubric.kind} ≥ {run.rubric.threshold}"
        )
        summary = (
            f"{len(run.candidates)} candidate(s) × {n_examples} example(s) · {rubric_clause}"
        )
        if top is not None and has_winner:
            verdict = _verdict(top)
            recommendation = _recommendation_line(top)
        elif top is not None:
            verdict = "No clear winner"
            recommendation = (
                "No candidate passed the governance bench."
                if is_bench
                else f"No candidate passed the rubric (threshold {run.rubric.threshold:.2f})."
            )
        else:
            verdict = "No run"
            recommendation = "No candidates were run."
    return {
        "receipt_version": RECEIPT_VERSION,
        "run_id": run.id,
        "config_hash": run.config_hash,
        "created_at": run.created_at,
        "brief": run.brief.model_dump(),
        "dataset": {"id": run.dataset_id, "name": run.dataset_name},
        "rubric": run.rubric.model_dump(),
        "summary": summary,
        "scored_by": _scored_by(run.rubric),
        "cost": {
            "candidate": report.cost_summary.candidate_cost_usd,
            "judge": report.cost_summary.judge_cost_usd,
            "total": report.cost_summary.total_cost_usd,
        },
        "mode": run.mode,
        "chosen_winner": run.chosen_winner,
        "quick_note": (
            "Single-example quick check — not scored proof. Promote to a full scored run for "
            "repeatable proof."
            if is_quick else ""
        ),
        "verdict": verdict,
        "recommendation": recommendation,
        "leaderboard": [e.model_dump() for e in report.leaderboard],
        "prompt_variants": [
            {"name": e["label"], "system_prompt": e["system_prompt"]}
            for e in (entry.model_dump() for entry in report.leaderboard)
            if e.get("system_prompt")
        ],
        "failure_cases": [r.model_dump() for r in _failure_cases(report)],
        "verdict_review": [r.model_dump() for r in review_report(report)],
        # Hardware context — presentation-only, never in config_hash. None when not captured.
        "host": report.host.model_dump() if report.host else None,
        "telemetry": report.telemetry.model_dump() if report.telemetry else None,
        "repro": {
            "run_id": run.id,
            "config_hash": run.config_hash,
            "created_at": run.created_at,
            "dataset_id": run.dataset_id,
            "candidate_ids": candidate_ids,
            "rubric": run.rubric.model_dump(),
            "rerun": _rerun_command(run),
        },
    }


def to_json(report: ProofReport) -> str:
    """Machine-readable receipt — the canonical structure as pretty JSON."""
    return json.dumps(build_receipt(report), indent=2, ensure_ascii=False)


def _hardware_lines(report: ProofReport) -> list[str]:
    """The ## Hardware stanza — context ("reproduced on hardware like X"), never proof.

    Excluded from config_hash: it describes the machine, not the run identity. Returns ``[]``
    when no host profile was captured (older runs), so the stanza only appears when real.
    """
    host = report.host
    if host is None:
        return []
    bits = [
        b
        for b in (
            host.chip or host.arch,
            f"{host.memory_gb} GB unified" if host.memory_gb else None,
            host.os_label,
            host.local_runtime,
        )
        if b
    ]
    lines = [
        "",
        "## Hardware",
        "",
        f"_Reproduced on hardware like: {' · '.join(bits)}._",
        "_This describes the machine; it does not affect the config hash._",
        "",
    ]
    tel = report.telemetry
    if tel is None or not tel.sampled:
        lines.append("- Live telemetry: not captured for this run.")
        return lines
    if tel.cpu_util_max is not None:
        lines.append(f"- CPU peak: {tel.cpu_util_max:.0f}%")
    if tel.process_rss_gb_max is not None:
        lines.append(f"- Runtime memory (RSS) peak: {tel.process_rss_gb_max:.1f} GB")
    if tel.gpu_util_max is not None:
        lines.append(f"- GPU peak: {tel.gpu_util_max:.0f}%")
    else:
        lines.append("- GPU: unavailable (enable GPU metrics in Settings)")
    if tel.warmup_ms is not None:
        lines.append(f"- First-call (incl. load): {tel.warmup_ms} ms")
    return lines


def _hardware_html(report: ProofReport) -> str:
    """The ## Hardware stanza as an HTML block, mirroring ``_hardware_lines``. Empty if no host."""
    lines = _hardware_lines(report)
    if not lines:
        return ""
    # lines[1] == "## Hardware"; lines[3] = "_Reproduced…_"; lines[4] = "_…config hash._";
    # remaining "- " bullets are the telemetry rows. Render simply and escaped.
    repro = html.escape(lines[3].strip("_"))
    note = html.escape(lines[4].strip("_"))
    bullets = "".join(
        f"<li>{html.escape(line[2:])}</li>" for line in lines if line.startswith("- ")
    )
    return (
        "<h2>Hardware</h2>"
        f"<p class='muted'>{repro}<br/>{note}</p>"
        f"<ul class='hardware'>{bullets}</ul>"
    )


def _tokens_by_candidate(report: ProofReport) -> dict[str, int]:
    """Total tokens (input+output) per candidate across the quick run's single example."""
    totals: dict[str, int] = {}
    for r in report.results:
        totals[r.candidate_id] = totals.get(r.candidate_id, 0) + r.input_tokens + r.output_tokens
    return totals


def _quick_markdown(report: ProofReport, data: dict) -> str:
    """Markdown for an unscored quick-compare check: objective table + outputs + the pick."""
    brief = data["brief"]
    repro = data["repro"]
    tokens = _tokens_by_candidate(report)
    pick = data["chosen_winner"]
    lines: list[str] = [
        "# Proof Receipt",
        "",
        "> **QUICK CHECK** · 1 example · not scored proof",
        "",
        f"**Verdict: {data['verdict']}** — {data['recommendation']}",
        "",
        f"_{data['summary']}_",
        "",
        f"- **Decision:** {brief['decision_question']}",
        f"- **Task:** {brief['task_name']}",
        f"- **Run id:** `{data['run_id']}`",
        f"- **Config hash:** `{data['config_hash']}`",
        f"- **Generated:** {data['created_at']}",
        f"- **Receipt schema:** v{data['receipt_version']}",
        "",
        "## Head-to-head",
        "",
        "| Candidate | Provider | Privacy | Latency | Cost | Tokens |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for e in data["leaderboard"]:
        marker = " ⭐" if e["candidate_id"] == pick else ""
        lines.append(
            f"| {_md_cell(e['label'])}{marker} | {_md_cell(e['provider_id'])} | "
            f"{_md_cell(e['privacy'])} | {e['avg_latency_ms']}ms | "
            f"${e['total_estimated_cost_usd']:.4f} | {tokens.get(e['candidate_id'], 0)} |"
        )
    lines += ["", "## Outputs", ""]
    by_id = {c.id: c for c in report.run.candidates}
    for r in report.results:
        cand = by_id.get(r.candidate_id)
        label = cand.label if cand else r.candidate_id
        star = " ⭐" if r.candidate_id == pick else ""
        body = f"error: {r.error}" if r.error else (_md_inline(r.output_text) or "—")
        lines += [f"- **{_md_cell(label)}{star}** — {body}"]
    lines += [
        "",
        f"_{data['quick_note']}_",
        "",
        "## Repro",
        "",
        f"- **Run id:** `{repro['run_id']}`",
        f"- **Config hash:** `{repro['config_hash']}` (identical inputs reproduce this hash)",
        f"- **Generated:** {repro['created_at']}",
        "",
    ]
    return "\n".join(lines)


def to_markdown(report: ProofReport) -> str:
    """Human, client-shareable receipt in Markdown."""
    data = build_receipt(report)
    if data["mode"] == "quick":
        return _quick_markdown(report, data)
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
        f"- **Rubric:** {_rubric_label(data['rubric'])}",
        f"- **Scored by:** {data['scored_by']}",
        f"- **Run id:** `{data['run_id']}`",
        f"- **Config hash:** `{data['config_hash']}`",
        f"- **Generated:** {data['created_at']}",
        f"- **Receipt schema:** v{data['receipt_version']}",
        "",
        "## Leaderboard",
        "",
        "| Candidate | Provider | Privacy | Pass rate | $ / quality | Avg score | Avg latency | tok/s | Est. cost | Failures |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for e in data["leaderboard"]:
        marker = " ⭐" if e["recommended"] else ""
        lines.append(
            f"| {_md_cell(e['label'])}{marker} | {_md_cell(e['provider_id'])} | "
            f"{_md_cell(e['privacy'])} | "
            f"{e['pass_rate']:.0%} ({e['pass_count']}/{e['total']}) | "
            f"{_cost_per_quality_label(e['cost_per_quality'])} | {e['avg_score']:.2f} | "
            f"{e['avg_latency_ms']}ms | {_tok_per_sec_label(e['tokens_per_second'])} | "
            f"${e['total_estimated_cost_usd']:.2f} | {_failures_label(e)} |"
        )

    c = data["cost"]
    lines += [
        "",
        f"_Run cost: candidate ${c['candidate']:.4f} · judge ${c['judge']:.4f} · "
        f"total ${c['total']:.4f}_",
    ]

    failures = data["failure_cases"]
    reviews = _reviews_by_key(data)
    lines += ["", f"## Failure cases ({len(failures)})", ""]
    if not failures:
        lines.append("_No failures — every candidate passed every example._")
    for f in failures:
        reason = _failure_reason(f)
        reason += _review_suffix(reviews.get((f["candidate_id"], f["example_index"])))
        lines += [
            f"- **{f['candidate_id']}** · example {f['example_index']} · {reason}",
            f"  - input: {_md_inline(f['input_text'])}",
            f"  - expected: {_md_inline(f['expected_text'])}",
            f"  - output: {_md_inline(f['output_text']) or '—'}",
        ]

    variants = data["prompt_variants"]
    if variants:
        lines += ["", "## Prompt variants", "",
                  f"_Same model, {len(variants)} system prompts compared._", ""]
        for v in variants:
            lines += [f"- **{_md_inline(v['name'])}:** {_md_inline(v['system_prompt'])}"]

    lines += _hardware_lines(report)

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


_RECEIPT_STYLE = """<style>
  :root {
    color-scheme: light dark;
    /* Receipt palette (--rc-*) + a status/accent set the inline SVG figures read (--color-*),
       defined HERE so a self-contained receipt themes its figures without the cockpit's stylesheet.
       Accent is Proof cyan (the one action colour); ok/warn/danger are status only. */
    --rc-bg: #0b0f14; --rc-ink: #e6edf3; --rc-muted: #9fb0c0; --rc-faint: #6f8190; --rc-line: #1c2530;
    --rc-card: #0f141b; --rc-rec-bg: #11331f; --rc-rec-line: #1f5135; --rc-rec-ink: #c8f5da;
    --rc-case: #c4d0db; --rc-case-key: #6f8190;
    --color-accent: #22d3ee; --color-ok: #34d399; --color-warn: #fbbf24; --color-danger: #f87171;
    --color-ink-muted: var(--rc-muted); --color-ink-faint: var(--rc-faint);
  }
  @media (prefers-color-scheme: light) {
    :root {
      --rc-bg: #f4f6f8; --rc-ink: #1b2430; --rc-muted: #51616f; --rc-faint: #6b7785; --rc-line: #dde3ea;
      --rc-card: #ffffff; --rc-rec-bg: #e7f7ee; --rc-rec-line: #b6e6cb; --rc-rec-ink: #0f5132;
      --rc-case: #2b3744; --rc-case-key: #5f6e80;
      --color-accent: #0e9e98; --color-ok: #0f9d63; --color-warn: #b97e00; --color-danger: #c0392b;
    }
  }
  :root[data-theme="dark"] {
    --rc-bg: #0b0f14; --rc-ink: #e6edf3; --rc-muted: #9fb0c0; --rc-faint: #6f8190; --rc-line: #1c2530;
    --rc-card: #0f141b; --rc-rec-bg: #11331f; --rc-rec-line: #1f5135; --rc-rec-ink: #c8f5da;
    --rc-case: #c4d0db; --rc-case-key: #6f8190;
    --color-accent: #22d3ee; --color-ok: #34d399; --color-warn: #fbbf24; --color-danger: #f87171;
  }
  :root[data-theme="light"] {
    --rc-bg: #f4f6f8; --rc-ink: #1b2430; --rc-muted: #51616f; --rc-faint: #6b7785; --rc-line: #dde3ea;
    --rc-card: #ffffff; --rc-rec-bg: #e7f7ee; --rc-rec-line: #b6e6cb; --rc-rec-ink: #0f5132;
    --rc-case: #2b3744; --rc-case-key: #5f6e80;
    --color-accent: #0e9e98; --color-ok: #0f9d63; --color-warn: #b97e00; --color-danger: #c0392b;
  }
  body { margin: 0; font: 15px/1.6 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
         background: var(--rc-bg); color: var(--rc-ink); }
  main { max-width: 56rem; margin: 0 auto; padding: 2.5rem 1.5rem; }
  /* Shared vocabulary with orionfold.com receipts: a mono-uppercase eyebrow over a tight display
     headline. Here the eyebrow is the evidence tag (PROOF RECEIPT · dataset), the headline is the
     verdict + metric spine — the cockpit's evidence genre wearing the website's familiarity hooks. */
  .eyebrow { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11px;
             letter-spacing: 0.18em; text-transform: uppercase; color: var(--color-accent); margin: 0; }
  h1 { font-size: 1.65rem; letter-spacing: -0.01em; line-height: 1.2; margin: 0.5rem 0 0; }
  .metric { margin: 0.6rem 0 0; display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.25rem 0.9rem;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  .metric .stat { font-size: 1.05rem; color: var(--rc-ink); }
  .metric .stat b { color: var(--color-accent); font-weight: 600; }
  .rec { background: var(--rc-rec-bg); border: 1px solid var(--rc-rec-line); color: var(--rc-rec-ink);
          padding: 0.9rem 1rem; border-radius: 12px; margin: 1.25rem 0 1.5rem; }
  /* Section labels echo the website's "The receipt" / "Rerun it" mono-uppercase chrome. */
  h2 { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px;
       letter-spacing: 0.12em; text-transform: uppercase; color: var(--rc-faint); font-weight: 600;
       margin: 2rem 0 0.6rem; }
  dl { display: grid; grid-template-columns: max-content 1fr; gap: 0.2rem 1rem; margin: 0 0 1.5rem; }
  dt { color: var(--rc-muted); } dd { margin: 0; }
  table { width: 100%; border-collapse: collapse; margin: 0.5rem 0 1rem; }
  th, td { text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--rc-line); }
  th { color: var(--rc-muted); font-weight: 600; font-size: 0.85rem; }
  tbody tr.rec-row { background: color-mix(in srgb, var(--rc-rec-bg) 55%, transparent); }
  code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  .muted { color: var(--rc-muted); }
  /* Inline figures (pass-rate bars + cost×quality scatter), reused from `figures`. Two-up on wide,
     stacked on narrow; the card frame matches the website's rounded receipt blocks. */
  .figures { display: grid; gap: 1rem; grid-template-columns: 1fr; margin: 0.5rem 0 0.5rem; }
  @media (min-width: 40rem) { .figures { grid-template-columns: 1fr 1fr; } }
  figure.fn-diagram { margin: 0; border: 1px solid var(--rc-line); border-radius: 12px;
                      background: var(--rc-card); padding: 0.9rem 1rem; }
  figure.fn-diagram svg { width: 100%; height: auto; display: block; }
  figure.fn-diagram figcaption { color: var(--rc-faint); font-size: 0.8rem; margin-top: 0.5rem; }
  /* Cost ledger — the eval/judge/total split as a small framed block, not a buried one-liner. */
  .ledger { display: flex; flex-wrap: wrap; gap: 0.4rem 1.5rem; border: 1px solid var(--rc-line);
            border-radius: 12px; background: var(--rc-card); padding: 0.8rem 1rem; margin: 0.5rem 0 0.5rem;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  .ledger .cell { display: flex; flex-direction: column; gap: 0.1rem; }
  .ledger .cell span { font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--rc-faint); }
  .ledger .cell strong { font-weight: 600; color: var(--rc-ink); }
  ul.failures, ul.variants { list-style: none; padding: 0; }
  ul.failures > li { border: 1px solid var(--rc-line); border-radius: 12px; padding: 0.8rem 1rem; margin: 0.6rem 0;
                     background: var(--rc-card); }
  ul.failures > li > strong { display: block; margin-bottom: 0.5rem; }
  ul.variants > li { margin: 0.3rem 0; }
  /* input / expected / output: a STACKED label over a pre-wrap value (mirrors the cockpit's
     ExampleCard.Field) so authored newlines + structured prompts (Source 1: … Source 2: …) keep
     their shape instead of collapsing into one wall of text. The value is mono + size-capped with a
     scroll so a giant retrieved-context block never dominates the receipt. */
  .case { display: grid; gap: 0.15rem; margin-top: 0.6rem; }
  .case > span { color: var(--rc-case-key); font-size: 11px; letter-spacing: 0.08em;
                 text-transform: uppercase; }
  .case > .val { color: var(--rc-case); white-space: pre-wrap; overflow-wrap: anywhere;
                 font: 12.5px/1.55 ui-monospace, SFMono-Regular, Menlo, monospace;
                 max-height: 16rem; overflow: auto;
                 background: color-mix(in srgb, var(--rc-line) 22%, transparent);
                 border-radius: 8px; padding: 0.5rem 0.65rem; }
  /* Structured retrieved-context render (the Advisor bench shape) — the SAME Question + source-card
     decomposition the cockpit shows for datasets/corpus/evals, reusing the shared parser. A flat
     pre-wrap blob becomes a question line over a stack of titled, cited source cards. */
  .ctx { display: grid; gap: 0.5rem; }
  .ctx-question { margin: 0; color: var(--rc-ink); }
  .ctx-sources-label { font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase;
                       color: var(--rc-faint); }
  .ctx-sources { display: grid; gap: 0.4rem; }
  /* Source card = the DS SourceDisclosure shell: a full neutral border on the raised card surface
     (NO left-edge accent — accent is reserved for the primary action / winner). Native <details>
     gives progressive disclosure with zero JS. */
  .src-card { border: 1px solid var(--rc-line); border-radius: 8px; background: var(--rc-card); }
  .src-head { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.3rem 0.5rem;
              padding: 0.45rem 0.6rem; }
  details.src-card > summary.src-head { cursor: pointer; list-style: none; }
  details.src-card > summary.src-head::-webkit-details-marker { display: none; }
  /* A rotating ▸ disclosure caret leads the summary so the expand affordance reads at a glance. */
  details.src-card > summary.src-head::before { content: "▸"; color: var(--rc-faint);
              font-size: 10px; margin-right: 0.1rem; transition: transform 0.12s ease; }
  details.src-card[open] > summary.src-head::before { transform: rotate(90deg); }
  details.src-card > summary.src-head:hover { background: color-mix(in srgb, var(--rc-ink) 5%, transparent); }
  .src-title { color: var(--rc-ink); font-weight: 500; }
  .src-id { font-size: 11px; color: var(--rc-faint);
            background: color-mix(in srgb, var(--rc-line) 30%, transparent);
            border-radius: 4px; padding: 0.05rem 0.35rem; }
  .src-class { font-size: 11px; color: var(--rc-faint); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  .src-body { border-top: 1px solid var(--rc-line); padding: 0.45rem 0.6rem; }
  .src-label { margin: 0 0 0.2rem; font-size: 12px; color: var(--rc-muted); }
  .src-excerpt { margin: 0; font-size: 12px; color: var(--rc-case); white-space: pre-wrap;
                 overflow-wrap: anywhere; }
  /* "Rerun it" provenance footer — the website's mono-labelled card, carrying the repro spine. */
  .provenance { border: 1px solid var(--rc-line); border-radius: 12px; background: var(--rc-card);
                padding: 1rem 1.1rem; margin: 1.5rem 0 0; }
  .provenance p.label { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11px;
                        letter-spacing: 0.18em; text-transform: uppercase; color: var(--rc-faint); margin: 0 0 0.6rem; }
  .provenance dl { margin: 0; }
</style>"""


def _quick_html(report: ProofReport, data: dict, theme: str | None) -> str:
    """HTML for an unscored quick-compare check: objective table + outputs + the pick."""
    brief = data["brief"]
    tokens = _tokens_by_candidate(report)
    pick = data["chosen_winner"]
    by_id = {c.id: c for c in report.run.candidates}
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(e['label'])}{' ⭐' if e['candidate_id'] == pick else ''}</td>"
        f"<td>{html.escape(e['provider_id'])}</td>"
        f"<td>{html.escape(e['privacy'])}</td>"
        f"<td>{e['avg_latency_ms']}ms</td>"
        f"<td>${e['total_estimated_cost_usd']:.4f}</td>"
        f"<td>{tokens.get(e['candidate_id'], 0)}</td>"
        "</tr>"
        for e in data["leaderboard"]
    )
    outputs = "".join(
        "<li><strong>{label}{star}</strong>"
        "<div class='case'><span>output</span><div class='val'>{body}</div></div></li>".format(
            label=html.escape(by_id[r.candidate_id].label if r.candidate_id in by_id else r.candidate_id),
            star=" ⭐" if r.candidate_id == pick else "",
            body=html.escape(f"error: {r.error}" if r.error else (r.output_text or "—")),
        )
        for r in report.results
    )
    theme_attr = f' data-theme="{theme}"' if theme in ("light", "dark") else ""
    return f"""<!doctype html>
<html lang="en"{theme_attr}>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Proof Receipt · Quick Check</title>
{_RECEIPT_STYLE}
</head>
<body>
<main>
  <p class="eyebrow">Proof Receipt · Quick check</p>
  <h1>{html.escape(data['verdict'])} — {html.escape(brief['decision_question'] or brief['task_name'])}</h1>
  <p class="metric"><span class="stat">QUICK CHECK · 1 example · not scored proof</span></p>
  <div class="rec"><strong>{html.escape(data['recommendation'])}</strong></div>
  <p class="muted">{html.escape(data['summary'])}</p>
  <dl>
    <dt>Decision</dt><dd>{html.escape(brief['decision_question'])}</dd>
    <dt>Task</dt><dd>{html.escape(brief['task_name'])}</dd>
    <dt>Generated</dt><dd>{html.escape(data['created_at'])}</dd>
    <dt>Receipt schema</dt><dd>v{data['receipt_version']}</dd>
  </dl>
  <h2>Head-to-head</h2>
  <table>
    <thead><tr><th>Candidate</th><th>Provider</th><th>Privacy</th><th>Latency</th><th>Cost</th><th>Tokens</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <h2>Outputs</h2>
  <ul class="failures">{outputs}</ul>
  <p class="muted">{html.escape(data['quick_note'])}</p>
  <section class="provenance">
    <p class="label">Provenance</p>
    <dl>
      <dt>Run id</dt><dd><code>{html.escape(data['run_id'])}</code></dd>
      <dt>Config hash</dt><dd><code>{html.escape(data['config_hash'])}</code></dd>
    </dl>
  </section>
</main>
</body>
</html>
"""


def _metric_spine(data: dict) -> str:
    """The mono metric line under the headline — the verdict's numbers at a glance. For a scored
    full run: pass-rate · pass-count · est. cost of the recommended candidate (the one being
    shipped). The accent <b> wraps the headline pass-rate so it pops, mirroring the website's
    metric eyebrow. Falls back gracefully when nothing is recommended (no-winner run)."""
    top = next((e for e in data["leaderboard"] if e.get("recommended")), None)
    if top is None:
        return ""
    pct = f"{top['pass_rate']:.0%}"
    cells = [
        f"<span class='stat'><b>{pct}</b> pass</span>",
        f"<span class='stat'>{top['pass_count']}/{top['total']} examples</span>",
        f"<span class='stat'>${top['total_estimated_cost_usd']:.2f}</span>",
    ]
    return f"<p class='metric'>{''.join(cells)}</p>"


def _figures_html(report: ProofReport) -> str:
    """The two inline SVG figures (pass-rate bars + cost-vs-quality scatter), reused verbatim from
    `figures`. Both self-omit (return "") on unscored/quick runs or when there's nothing to draw, so
    the receipt only shows a figure when it carries real meaning. Wrapped in a two-up grid."""
    parts = [pass_rate_svg(report), pareto_svg(report)]
    parts = [p for p in parts if p]
    if not parts:
        return ""
    return f"<div class='figures'>{''.join(parts)}</div>"


def _ledger_html(cost: dict) -> str:
    """The cost ledger as a small framed split (eval / judge / total) instead of a buried line."""
    return (
        "<div class='ledger'>"
        f"<div class='cell'><span>Eval</span><strong>${cost['candidate']:.4f}</strong></div>"
        f"<div class='cell'><span>Judge</span><strong>${cost['judge']:.4f}</strong></div>"
        f"<div class='cell'><span>Total</span><strong>${cost['total']:.4f}</strong></div>"
        "</div>"
    )


def _input_html(input_text: str) -> str:
    """Render an example's INPUT. When it's the flattened "retrieved public context" shape (the
    Advisor bench convention), parse it into a Question + source cards — the SAME structured
    rendering the cockpit shows for datasets / corpus / evals (reusing `parse_retrieved_context`).
    Otherwise degrade to a plain pre-wrap value. One parsing→rendering solution, two surfaces."""
    ctx = parse_retrieved_context(input_text)
    if ctx is None:
        return f"<div class='val'>{html.escape(input_text)}</div>"

    cards = []
    for src in ctx.sources:
        head = []
        if src.title:
            head.append(f"<span class='src-title'>{html.escape(src.title)}</span>")
        head.append(f"<code class='src-id'>{html.escape(src.id)}</code>")
        if src.class_:
            head.append(f"<span class='src-class'>{html.escape(src.class_)}</span>")
        body = []
        if src.label:
            body.append(f"<p class='src-label'>{html.escape(src.label)}</p>")
        if src.excerpt:
            body.append(f"<p class='src-excerpt'>{html.escape(src.excerpt)}</p>")
        # Progressive disclosure (native <details>, no JS — works in the sandboxed standalone
        # receipt) mirroring the cockpit's SourceDisclosure: a summary row that's always visible,
        # an excerpt/label body revealed on expand. Non-expandable when there's nothing to reveal.
        if body:
            cards.append(
                f"<details class='src-card'><summary class='src-head'>{''.join(head)}</summary>"
                f"<div class='src-body'>{''.join(body)}</div></details>"
            )
        else:
            cards.append(
                f"<div class='src-card src-card-flat'><div class='src-head'>{''.join(head)}</div></div>"
            )

    question = (
        f"<p class='ctx-question'>{html.escape(ctx.question)}</p>" if ctx.question else ""
    )
    return (
        f"<div class='ctx'>{question}"
        f"<div class='ctx-sources-label'>Retrieved context · {len(ctx.sources)} "
        f"source{'s' if len(ctx.sources) != 1 else ''}</div>"
        f"<div class='ctx-sources'>{''.join(cards)}</div></div>"
    )


def to_html(report: ProofReport, theme: str | None = None) -> str:
    """Self-contained HTML receipt (no external assets), calm and readable."""
    data = build_receipt(report)
    if data["mode"] == "quick":
        return _quick_html(report, data, theme)
    brief = data["brief"]

    rows = "".join(
        f"<tr{' class=\"rec-row\"' if e['recommended'] else ''}>"
        f"<td>{html.escape(e['label'])}{' ⭐' if e['recommended'] else ''}</td>"
        f"<td>{html.escape(e['provider_id'])}</td>"
        f"<td>{html.escape(e['privacy'])}</td>"
        f"<td>{e['pass_rate']:.0%} ({e['pass_count']}/{e['total']})</td>"
        f"<td>{html.escape(_cost_per_quality_label(e['cost_per_quality']))}</td>"
        f"<td>{e['avg_score']:.2f}</td>"
        f"<td>{e['avg_latency_ms']}ms</td>"
        f"<td>{html.escape(_tok_per_sec_label(e['tokens_per_second']))}</td>"
        f"<td>${e['total_estimated_cost_usd']:.2f}</td>"
        f"<td>{html.escape(_failures_label(e))}</td>"
        "</tr>"
        for e in data["leaderboard"]
    )

    failures = data["failure_cases"]
    reviews = _reviews_by_key(data)
    if failures:
        items = "".join(
            "<li><strong>{cid} · example {idx} · {reason}</strong>"
            "<div class='case'><span>input</span>{inp}</div>"
            "<div class='case'><span>expected</span><div class='val'>{exp}</div></div>"
            "<div class='case'><span>output</span><div class='val'>{out}</div></div></li>".format(
                cid=html.escape(f["candidate_id"]),
                idx=f["example_index"],
                reason=html.escape(
                    _failure_reason(f)
                    + _review_suffix(reviews.get((f["candidate_id"], f["example_index"])))
                ),
                inp=_input_html(f["input_text"]),
                exp=html.escape(f["expected_text"]),
                out=html.escape(f["output_text"] or "—"),
            )
            for f in failures
        )
        failures_html = f"<ul class='failures'>{items}</ul>"
    else:
        failures_html = "<p class='muted'>No failures — every candidate passed every example.</p>"

    variants = data["prompt_variants"]
    if variants:
        items = "".join(
            f"<li><strong>{html.escape(v['name'])}:</strong> {html.escape(v['system_prompt'])}</li>"
            for v in variants
        )
        variants_html = f"<h2>Prompt variants</h2><ul class='variants'>{items}</ul>"
    else:
        variants_html = ""

    return f"""<!doctype html>
<html lang="en"{f' data-theme="{theme}"' if theme in ("light", "dark") else ""}>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Proof Receipt · {html.escape(data['dataset']['name'])}</title>
{_RECEIPT_STYLE}
</head>
<body>
<main>
  <p class="eyebrow">Proof Receipt · {html.escape(data['dataset']['name'])}</p>
  <h1>{html.escape(data['verdict'])} — {html.escape(brief['decision_question'] or brief['task_name'])}</h1>
  {_metric_spine(data)}
  <div class="rec"><strong>{html.escape(data['recommendation'])}</strong></div>
  <p class="muted">{html.escape(data['summary'])}</p>
  {_figures_html(report)}
  <dl>
    <dt>Decision</dt><dd>{html.escape(brief['decision_question'])}</dd>
    <dt>Dataset</dt><dd>{html.escape(data['dataset']['name'])} (<code>{html.escape(data['dataset']['id'])}</code>)</dd>
    <dt>Rubric</dt><dd>{html.escape(_rubric_label(data['rubric']))}</dd>
    <dt>Scored by</dt><dd>{html.escape(data['scored_by'])}</dd>
    <dt>Generated</dt><dd>{html.escape(data['created_at'])}</dd>
    <dt>Receipt schema</dt><dd>v{data['receipt_version']}</dd>
  </dl>
  <h2>Leaderboard</h2>
  <table>
    <thead><tr>
      <th>Candidate</th><th>Provider</th><th>Privacy</th><th>Pass rate</th>
      <th>$ / quality</th>
      <th>Avg score</th><th>Avg latency</th><th>tok/s</th><th>Est. cost</th><th>Failures</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <h2>Cost ledger</h2>
  {_ledger_html(data['cost'])}
  <p class="muted">Run cost: candidate ${data['cost']['candidate']:.4f} · judge ${data['cost']['judge']:.4f} · total ${data['cost']['total']:.4f}</p>
  <h2>Failure cases ({len(failures)})</h2>
  {failures_html}
  {variants_html}
  {_hardware_html(report)}
  <section class="provenance">
    <p class="label">Rerun it</p>
    <dl>
      <dt>Run id</dt><dd><code>{html.escape(data['repro']['run_id'])}</code></dd>
      <dt>Config hash</dt><dd><code>{html.escape(data['repro']['config_hash'])}</code></dd>
      <dt>Rerun</dt><dd><code>{html.escape(data['repro']['rerun'])}</code></dd>
    </dl>
  </section>
</main>
</body>
</html>
"""
