# Worklog — 2026-06-23 · Decide insight layer: score toggle + explainer (Task 7)

## Summary
Two additions to the WS-D1 cost-vs-quality scatter make a *mismatched-scorer* run legible
instead of demoralizing. When the scorer is stricter than the task, pass rate collapses to
0% for every candidate and the scatter shows a row of failing dots with no winner — but the
raw avg score still ranks the field. The 2026-06-23 real run proved it: 3 Anthropic tiers on
the flagship summarization set, all 0% pass under Similarity@0.55, yet avg scores Opus 0.20 /
Haiku 0.05 / Sonnet 0.05 — Opus is plainly ~4× better and that signal was being discarded.

1. **Pass rate ⇄ Avg score Y-axis toggle** on `FrontierScatter.tsx` (segmented control, same
   idiom as the `compareBy` toggle). Default stays **Pass rate** (WS-D1 behavior unchanged).
   Flipping to Avg score rescues the ranking — the dots spread vertically and the Pareto
   frontier (which was flat at Y=0) redraws through the genuine cost/quality trade-off.
2. **Deterministic plain-English explainer** beneath the chart — `decideInsights.ts`
   `deriveDecideInsight(entries)`, a pure rule-based function (NOT an LLM call, so it's free
   and reproducible — the receipt's repeatability promise holds). It names what the data shows:
   why everything failed, who actually leads on raw score, and what to try.

**Key invariant — recommended accent ≠ metric leader.** `buildScatterPoints(entries, metric)`
recomputes the frontier per metric, but `recommended` always passes through from the
leaderboard, never re-derived. A point can top Avg score yet carry no cyan accent because it
passed nothing — that disagreement *is* the insight the explainer puts into words.

**FE-only:** no backend, no migration, no `RECEIPT_VERSION` bump, no `config_hash` touch — pure
display + derivation over existing `LeaderboardEntry` fields. Mock `config_hash 467ddd96c9a5`
untouched by construction. Recharts only (no second charting lib).

### New / changed files
- `web/src/features/proof/decideInsights.ts` (new) — pure `deriveDecideInsight(entries)`:
  5 ordered rules (all-errored→warn; all-fail-but-real-scores→warn, names the avg-score leader
  + suggests the LLM judge; clear-winner→ok; tight-cluster→info; fallback→info). Constants
  `REAL_SCORE_FLOOR=0.03`, `CLEAR_WINNER_GAP=0.2`. Returns `{headline, detail, tone}` | null.
- `web/src/features/proof/decideInsights.test.ts` (new) — 9 tests, one per rule branch + range
  collapse, scores-below-floor fall-through, single candidate, empty.
- `web/src/features/proof/paretoFrontier.ts` — `buildScatterPoints(entries, metric)` gained the
  `ScatterMetric = "pass_rate" | "avg_score"` param (default pass_rate); `avg_score` reads
  `e.avg_score`; frontier recomputes per metric; `recommended` passes through.
- `web/src/features/proof/FrontierScatter.tsx` — metric state + segmented toggle; YAxis name/
  label + tooltip relabel per metric; `<DecideExplainer>` rendered inside the panel beneath the
  chart (tone dot via `--color-ok/warn/ink-muted`, NEVER the cyan accent). Exported
  `CandidateDot` so the accent invariant can be unit-tested (jsdom can't compute dot geometry).
- `web/src/features/proof/{paretoFrontier,FrontierScatter}.test.*` — +6 tests (metric mapping +
  default; toggle default/flip; explainer tone; metric-agnostic text; accent-ring invariant).
- `e2e/playwright/proof.spec.ts` — added toggle + explainer assertions to the proof-loop test.

## Verification
- **178 FE tests** pass (was 163, +15), `tsc --noEmit` clean, `pnpm build` clean.
- **298 BE tests** pass — unchanged, confirming FE-only.
- **11/11 Playwright** pass. (Required re-embedding the fresh `web/dist` into
  `src/orionfold/server/static` — the e2e webServer runs `orionfold up`, which serves the
  *embedded* build, not the dev source.)
- **Real-model browser verification** (Sandbox OFF, real keys, 3 Anthropic tiers,
  Similarity@0.55, config `7f2bed41f3f4`): reproduced the headline case exactly — all 3 at 0%
  pass; avg Opus 0.20 / Haiku 0.05 / Sonnet 0.05. **Pass-rate view** = 3 flat dots, no accent,
  no frontier line. **Avg-score view** = dots spread (Opus rises to ~20%), frontier redraws
  through the trade-off. **Explainer** reads *"0% pass, but the scores still rank the field …
  the scorer looks stricter than the task. Flip the Y axis to Avg score: Anthropic ·
  claude-opus-4-8 leads. For paraphrased or free-form answers, try the LLM judge or lower the
  threshold in Settings."* — and stays byte-identical across the toggle (metric-agnostic).
  Light + dark both graded; no secrets on screen.
- **Fresh-context diff-reviewer**: faithful to plan, all invariants intact, no correctness bugs.

## Product impact
Directly de-risks the "no winner" first impression that the WS-D1 real run surfaced as the
flagship demo's biggest legibility gap. A user whose scorer is mismatched no longer sees a dead
end — they see *which model is actually best* and a one-line, reproducible explanation of what
to do (flip the axis; try the LLM judge or lower the threshold). This makes the *existing*
outcome legible; it does NOT change scoring (that's the separate scorer-default fix, still
queued). It also unblocks WS-E2 (guided first-run CTA), whose blocker was landing users on a
"no winner" screen.

## Risks
- The explainer is a cockpit aid, deliberately **not** part of the proof artifact (no receipt/
  export change). If the operator later wants it on the receipt, that's a follow-up.
- Non-recommended dot tone derives from `passRateTone(p.quality)` where `quality` is the toggled
  metric value — cosmetic, consistent with the displayed Y, diff-reviewer OK'd. Not an accent
  violation (accent stays gated on `recommended`).
- The scorer-default fix (Similarity@0.55 too strict for paraphrased summaries → should default
  to LLM judge for free-form datasets) remains the real fix; this task makes the symptom legible,
  it does not cure it. WS-E2 still blocks on the scorer-default fix.

## Next recommended step
**Task 8 — WS-D2 (run-level cost ledger / spend panel).** Per-provider tokens + $ and a run
total in the Inspector or under the leaderboard. `RunCostSummary` is already on the report;
surface it (don't recompute). Reuse ainative `ledger.ts` + `cost-dashboard.tsx` + micro-viz,
porting the micro-viz to the Recharts foundation laid in WS-D1 (no second charting lib). Verify
the panel's sums match the verdict banner's existing "Run cost" line (this run: candidate
$0.0827 · judge $0.0000 · total $0.0827).
