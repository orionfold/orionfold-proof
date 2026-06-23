# Worklog — 2026-06-23 · Bundled demo defaults to the LLM judge (unblocks Task 10 / WS-E2)

## Summary
Made the bundled **"Sample · investment memo summarization"** demo (the seeded
`is_sample` dataset, id `sample-investment-memo`) default its run's scoring method to the
**LLM judge** instead of Auto/Keypoint. This is the prerequisite the handoff flagged for
**Task 10 (WS-E2 guided first-run CTA)**: real-run evidence (`_IDEAS/issues.md`) showed the
demo reads "NO CLEAR WINNER" under lexical scoring at *any* threshold (re-runs scored
0.06–0.15 even at the shipped 0.55 Similarity default), so a one-click CTA would land users
on failing dots — worse than a blank form. The honest fix is the scorer, not the threshold.

**Operator decisions this session (via AskUserQuestion):**
1. Take path **(a)** — fix the demo scorer default first (the demo-critical thread), over
   the unblocked-but-lower-value Task 11 (WS-F DS pass).
2. Put the default in the **frontend** (Auto-prefers-judge for the sample), not the backend
   `default_rubric_for` — FE-only, reuses the battle-tested A3 judge gate, no
   backend/`config_hash` risk. (The keyless backend scoring core can't resolve a concrete
   judge model anyway — that resolution lives in `defaultJudgeCell`.)

## What shipped (`50155bb`) — FE-only, 4 files
- **`web/src/features/proof/scoring.ts`** — new pure `prefersSampleJudge(dataset, judgeCell)`:
  `true` iff `dataset.is_sample === true` AND `judgeCell` is a resolved, **non-`mock_judge`**
  cell. The tri-state gate is the whole subtlety: `undefined` (default not resolved yet),
  `null` (no real judge configured, Sandbox OFF), and `mock_judge` (Sandbox keyless) all
  return `false` — so a keyless user stays on Auto and **never silently grades with Mock**,
  and Sandbox keeps its existing keyless clear-winner demo unchanged.
- **`web/src/features/proof/ScoringMethod.tsx`** — a `useRef`-latched `useEffect` that fires
  `selectMethod("judge")` **once per sample-dataset arrival**, only while `value === null`
  (user hasn't chosen a method). The latch (keyed on `dataset.id`, set *before* the call)
  prevents re-fire/clobber of a later deliberate switch back to Auto. It routes through the
  existing `if (judgeCell)` commit gate, so it can only ever emit a **real** judge (A3
  invariant preserved — belt-and-suspenders with `prefersSampleJudge`).
- Tests: `scoring.test.ts` (7 pure-helper cases) + `ScoringMethod.test.tsx` (5 component
  cases incl. sample→judge, no-key→Auto, non-sample→Auto, no-clobber, Sandbox-stays-keyless).

## Verification (evidence, not claims)
- **Unit/type/build:** `pnpm vitest run` → **204 FE** (was 192; +12), `uv run pytest` → **298
  BE unchanged**, `tsc --noEmit && vite build` clean.
- **e2e:** re-embedded `web/dist` → `src/orionfold/server/static`, `pnpm e2e` → **12/12
  Playwright**. The Sandbox e2e still asserts the *catalog* demo defaults to **Keypoint**
  (unaffected — the catalog `investment-memo-summarization` is `is_sample: false`).
- **Real-browser, real models** (Sandbox OFF; Anthropic+OpenAI keys in `.env.local`; cost
  OK'd): seeded the sample via `POST /api/sample-data/seed`, selected it in Configure →
  Scoring method **auto-selected LLM judge**, judge model **Claude Haiku 4.5 · Anthropic**
  (resolved by `defaultJudgeCell`, Hosted/Cheapest). Ran a real proof (Haiku 4.5 + GPT-5.4
  nano), config hash `4193ef79ba57`:
  - Verdict **RECOMMENDED · Anthropic · claude-haiku-4-5** — a **clear winner**, NOT "NO
    CLEAR WINNER". Passed 3/5 (60%), avg score 0.71 (> nano 0.68), total $0.0135.
  - Receipt records **"Scored by: LLM judge · claude-haiku-4-5"**, rubric `judge ≥ 0.8`.
  - **All 3 exports (MD/HTML/JSON) secret-free** (scanned for `sk-…`/`sk-ant-…`/`AIza…`/
    `sk-or-…` — none).
  - Negative cases verified live: fresh load on the catalog (non-sample) dataset → **Auto**;
    Sandbox ON + sample → stays Auto (no mock-judge auto-select).
- **Fresh-context diff-reviewer:** faithful to the plan, no bugs/regressions/invariant
  violations/scope creep; non-null assertion sound; eslint-disable justified.

## Product impact
The flagship demo now produces a trustworthy, client-shareable proof out of the box on real
models. This directly unblocks **Task 10 (WS-E2 guided first-run CTA)** — a one-click "run the
demo on real models" now lands on a clear winner, not three failing dots.

## Risks / notes
- The frontend default keys on `is_sample`, so it fires only for the **seeded** sample
  (`sample-investment-memo`), not the loadable catalog set (`investment-memo-summarization`).
  This matches the CTA's target (the bundled demo). A user who picks the raw catalog
  summarization set still gets Auto→Keypoint — acceptable, by design.
- `method` state persists across dataset switches (existing behavior, no reset effect): once
  the auto-default fires for the sample, switching away keeps "judge" selected, exactly as a
  manual method choice would persist. Returning to the sample later does **not** re-fire (the
  latch holds the id) — a benign edge.
- Two pre-existing `act(...)` warnings in `ScoringMethod.test.tsx` (query resolution outside
  `act`, present before this change). Out of scope; candidate for a future test cleanup.

## Next recommended step
**Task 10 — WS-E2 (Guided first-run CTA)** is now **unblocked**. Build the one-click "Run the
demo proof on real models" on the empty Proof Run state, targeting the seeded sample dataset
+ 2 cheap cloud candidates; it will now reach a clear-winner receipt in ~30s.
_ref:_ `_SPECS/2026-06-22-trustworthy-proof-and-polish.md` §WS-E2 · feature #5.
