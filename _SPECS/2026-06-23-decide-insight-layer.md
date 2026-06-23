# Spec — Decide-step insight layer: score toggle + plain-English explainer

_Status: approved (operator, 2026-06-23) · Tier: single-feature, FE-only, ~1 page · Sequence:
**ahead of WS-D2** in the Stage-3 queue (de-risks the "no winner" first impression directly)._

## Why

The WS-D1 cost-vs-quality scatter plots **pass rate** on Y. A real 3-tier Anthropic run on the
flagship summarization dataset (2026-06-23) returned **0% pass for all three** — yet the raw
**avg scores (0.06 / 0.06 / 0.15)** still ranked them: Opus was 2.5× better. The pass-rate view
discarded that signal and showed three failing dots with no winner. When the scorer is mismatched
to the dataset or the threshold is too strict, **pass rate collapses but raw score still carries
the insight.** (See `_IDEAS/issues.md` → "REAL-RUN: the flagship demo … NO CLEAR WINNER".)

Two additions rescue the insight without adding noise:
1. A **Y-axis toggle** on the existing scatter: **Pass rate ⇄ Avg score**.
2. A **deterministic, plain-English explainer** beneath the scatter that names what the data shows
   (why everything fails, who actually leads on score, what to try) — rule-based, not an LLM call,
   so it's free and reproducible (the receipt's repeatability promise must hold).

The original WS-D1 spec line already allowed "cost (x) × **pass-rate or avg-score** (y)" — this
formalizes that as a user-facing toggle plus the insight text.

## Scope (smallest vertical slice)

**FE-only.** No backend, no migration, no `RECEIPT_VERSION` bump, no `config_hash` touch. Pure
display + derivation over the existing `LeaderboardEntry[]` (which already carries `pass_rate`,
`avg_score`, `total_estimated_cost_usd`, `recommended`, `error_count`, `total`).

### 1. Y-axis metric toggle — `FrontierScatter.tsx`
- Add a `metric: "pass_rate" | "avg_score"` toggle control in the scatter header (segmented
  control, same idiom as the `compareBy` Models/Prompts/Quick toggle). Default = `pass_rate`
  (unchanged first paint).
- `buildScatterPoints(entries, metric)` gains the metric param: `quality` reads the selected field.
  `avg_score` is already 0–1, so the Y domain `[0,1]` and `%`-style ticks stay valid; relabel the
  axis ("Pass rate" / "Avg score") and the tooltip line per metric.
- **Frontier recomputes per metric** — `paretoFrontier` is metric-agnostic (operates on `{cost,
  quality}`), so the same skyline math just runs on the new Y. The **recommended accent stays tied
  to `entry.recommended`** (the leaderboard's verdict), NOT to whichever point leads the current
  metric — recommended is a run-level fact, not a per-view one. (A point can lead on Avg score yet
  not be `recommended` because it passed nothing; that disagreement is exactly what the explainer
  calls out.)

### 2. Deterministic explainer — new `web/src/features/proof/decideInsights.ts` (pure, unit-tested)
- `deriveDecideInsight(entries): { headline: string; detail: string; tone: "ok"|"warn"|"info" }`
  computed purely from the leaderboard. Rules (first match wins; all thresholds are constants at
  the top of the file):
  - **All errored** (every entry `error_count === total`, `total>0`): "No candidate produced
    output — all calls errored. Check keys/host before reading scores." (tone warn)
  - **All-fail but real scores** (no `recommended`, max `pass_rate === 0`, max `avg_score >=`
    ~0.03): "All candidates show 0% pass, but scores cluster at {min}–{max}. The scorer looks
    stricter than the task. **{leader}** scored highest — for paraphrased/free-form answers, try
    **LLM judge** or lower the threshold in Settings." (tone warn) ← the case we hit
  - **Clear winner, well separated** (`recommended` exists, its `pass_rate` − runner-up ≥ ~0.2):
    "**{winner}** is the clear pick — {pass}% pass at {cost}. The frontier confirms it's not just
    cheapest." (tone ok)
  - **Winner but tight cluster** (`recommended` exists, spread < ~0.2): "**{winner}** edges it,
    but the field is close ({minPass}–{maxPass}% pass). Decide on **cost / latency** — see the
    frontier." (tone info)
  - **Fallback**: a neutral one-liner naming the leader + metric.
- Numbers come straight from the entries (no recomputation of scores). Keep copy in the calm,
  technical-but-humane north-star voice; no exclamation, no hype.

### 3. Wire-up — `FrontierScatter.tsx`
- Render the explainer as a compact line/card directly beneath the chart (inside the same panel),
  with a small `ℹ`/status dot tinted by `tone` using **status tokens** (`--color-ok` / `warn` /
  reuse `--color-ink-muted` for `info` — NOT the cyan accent; accent stays reserved for the
  recommended point per the DS split). The explainer text is metric-agnostic (it reasons about the
  run, not the current Y view), so it does not change when the toggle flips — but it should
  reference avg-score explicitly in the all-fail case so the user knows to flip to it.

## Out of scope
- No LLM-generated prose (cost + non-reproducible + hallucination — explicitly rejected).
- No second permanent chart (one scatter + toggle; avoids the noisy-dashboard failure mode).
- No change to scoring, thresholds, or the recommendation logic (that's the separate scorer-default
  fix in `_IDEAS/issues.md`). This task makes the *existing* outcome legible; it does not change it.
- No receipt/export change (the explainer is a cockpit aid, not part of the proof artifact — at
  least in v1; revisit only if the operator wants it on the receipt).

## Verify
- **Vitest** `decideInsights.test.ts`: each rule branch (all-errored; all-fail+real-scores with
  correct leader/min/max; clear winner; tight cluster; fallback), plus boundary cases (single
  candidate, empty).
- **Vitest** `paretoFrontier`/`buildScatterPoints`: `buildScatterPoints(entries, "avg_score")`
  maps quality from `avg_score` and recomputes the frontier; recommended passthrough unchanged.
- **Vitest** `FrontierScatter.test.tsx`: toggle renders, switching to Avg score re-labels the axis;
  explainer renders with the right tone class; recommended dot stays accent across both metrics.
- **Playwright**: on the populated run, toggle to Avg score and assert the axis label + that the
  scatter still mounts; assert the explainer region is visible.
- **Browser (per CLAUDE.md):** re-run the 3-tier Anthropic case → confirm Avg-score view spreads
  Opus above the others while Pass-rate view is flat, and the explainer reads the "0% pass but
  scores 0.06–0.15 … try LLM judge" line. Light + dark.

## Invariants to NOT regress
- FE-only; mock `config_hash 467ddd96c9a5` untouched (no scoring/hash path touched).
- DS accent/status split: `--color-accent` only on the recommended point; explainer tone uses
  status/ink tokens only. Recommended accent tied to `entry.recommended`, never to the metric leader.
- Recharts only (no second charting lib — see the `charting-library-recharts` memory).
- Default first paint = Pass rate (the WS-D1 behavior); the toggle is additive.
