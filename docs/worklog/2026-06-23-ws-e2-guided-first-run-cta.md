# Worklog — 2026-06-23 · WS-E2 Guided first-run CTA (Task 10)

## Summary
Built the one-click **"Run the demo proof on real models"** CTA on the empty Proof Run
state. A single click seeds the bundled sample (if needed), selects it, preselects two
cheap cloud candidates, lets `ScoringMethod` auto-apply the LLM judge (the demo-judge
default shipped in `50155bb`), and **auto-runs** the proof — landing on a clear-winner
receipt in ~30s without the user touching the setup form. This is the activation path the
charter's onboarding promise calls for: turn a blank form into a finished, client-shareable
proof.

The blocker for this task (the bundled demo reading "NO CLEAR WINNER" under lexical scoring)
was cleared by the demo-judge-default fix (`50155bb`); this CTA rides that default.

## Operator decisions this session (via AskUserQuestion)
1. **CTA behavior = preselect + auto-run when ready.** The judge default resolves
   asynchronously inside `ScoringMethod`'s effect (rubric: null → judge), so the CTA can't
   preselect state AND fire the run in the same tick. A guarded `useEffect` waits until the
   sample is selected AND the rubric has resolved to `judge`, then fires once. (Truest to
   "one-click → receipt", vs. the simpler "preselect, user clicks Run".)
2. **No-key fallback = hide the CTA.** The CTA only appears when ≥2 cheap, available cloud
   candidates exist, so its "real models" promise stays honest. Otherwise the existing
   empty-state copy (add a key / enable Sandbox / seed sample data) stands.

## What shipped — FE-only, 5 files
- **`web/src/features/proof/scoring.ts`** — new pure `cheapCloudCandidates(panel, count=2)`:
  scans **available cloud** providers cheapest-first (cost_class `free < $ < $$ < $$$`, then
  recommended → latest within a class) and returns the first N distinct candidate ids. Cloud
  only (Local/Mock are the Sandbox path's job). Returns fewer than 2 when not enough cloud is
  configured — the caller hides the CTA unless it gets exactly 2.
- **`web/src/features/proof/ProofCockpit.tsx`** — the CTA wiring:
  - `sampleDataset = datasets.data?.find(d => d.is_sample)` (detect by the `is_sample`
    column, not a hardcoded id — sample-detection invariant).
  - `cheapCloud` (memoized) + `canRunDemo = cheapCloud.length === 2` gate.
  - `seedMutation` (`POST /api/sample-data/seed`) invalidates `["datasets"]`.
  - `startGuidedDemo()` preselects sample + cheap cloud, leaves rubric alone (so
    `ScoringMethod`'s once-per-dataset latch auto-applies the judge — clearing it here would
    leave it null forever), seeds if absent, and arms.
  - An **arm effect** keeps the sample selected through the seed→refetch race.
  - An **auto-run effect** fires the run once the sample is selected AND `rubric.kind ===
    "judge"` — passing that exact non-null judge rubric into `runMutation.mutate`, so the
    backend keypoint fallback is **unreachable**. One-shot via `setDemoArmed(false)` before
    mutate. Also **disarms** (no spin) if the user had pre-picked a non-judge method (latch
    spent → judge can never arrive); safety holds — never a run with the wrong rubric.
  - `EmptyResults` gained the CTA (interactive `--color-accent-strong` button, `animate-breathe`
    like the Run button), shown only when `onRunDemo` is passed.
- Tests: `scoring.test.ts` (+5: cheapest-first, cloud-only, skip-unavailable, recommended/
  latest tiebreak, undefined panel); `ProofCockpit.test.tsx` (+3: hides without cheap cloud,
  auto-runs with judge rubric + cheap cloud, disarms on pre-picked non-judge);
  `proof.spec.ts` (+1: CTA presence matches the live `/api/selection` cloud count — passes
  with or without keys, never clicks a paid run).

## Verification (evidence, not claims)
- **Unit/type/build:** `pnpm vitest run` → **212 FE** (was 204; +8), `uv run pytest` → **298
  BE unchanged** (confirms FE-only), `tsc --noEmit` exit 0, `vite build` clean.
- **e2e:** re-embedded `web/dist` → `src/orionfold/server/static`, `CI=1 pnpm e2e` →
  **13/13 Playwright** (+1 CTA smoke).
- **Real-browser, real models** (Sandbox OFF; Anthropic+OpenAI keys in `.env.local`; cost
  OK'd): loaded the empty Proof Run state → the CTA rendered beneath the empty-state copy.
  One click →
  - Task name switched to **"Sample · investment memo summarization"** (`is_sample`).
  - Scoring auto-selected **LLM judge**, Hosted/Cheapest → **Claude Haiku 4.5 · Anthropic**.
  - Candidates auto-selected the **2 cheapest cloud models** (Claude Haiku 4.5 + GPT-5.4 nano).
  - The run **auto-fired** and finished on real models. Persisted run `run_593bbe577f05`,
    `dataset_id: sample-investment-memo`, `rubric.kind: judge`.
  - Verdict **RECOMMENDED · OpenAI · gpt-5.4-nano** — a **clear winner**. Passed 4/5 (80%),
    avg 0.73, total $0.0130. (Which cheap model wins varies run-to-run; either way it's a
    clear winner, not "NO CLEAR WINNER".)
  - Receipt records **"Scored by: LLM judge · claude-haiku-4-5"**.
  - **All 3 exports (md/HTML/JSON) secret-free** (scanned for `sk-…`/`sk-ant-…`/`AIza…`/
    `sk-or-v1-…` — 0 hits each).
- **Fresh-context diff-reviewer:** **PASS** — faithful, no invariant violations, no
  correctness bugs (double-fire/race/loop all sound). It flagged one non-blocking liveness
  edge (armed-forever spinner if the user pre-picks a non-judge method); hardened it (disarm
  branch + a covering test) before commit.

## Product impact
The blank Proof Run state now offers a true one-click path to a real-model, judge-scored,
client-shareable receipt — the charter's activation promise, delivered. New users with cloud
keys see a finished proof in ~30s without learning the setup form first.

## Risks / notes
- The CTA is hidden for keyless / Sandbox-only users (by operator decision) — they keep the
  existing empty-state guidance. The "real models" label never over-promises.
- The auto-run depends on `ScoringMethod`'s FE judge default. If that component's latch logic
  changes, re-verify the CTA still reaches a judge rubric (the `rubric.kind === "judge"` gate
  fails safe — it just won't run — so a regression there degrades to "nothing happens", never
  "wrong rubric").
- The `e2e` CTA smoke asserts presence-matches-availability rather than clicking (a real run
  costs money + needs keys); the click path is covered by unit tests + the live-browser run.

## Next recommended step
**Task 11 — WS-F (DS application-consistency pass, LOW; may split)** is the last open queue
item: F1 seed sample metadata; F2/F3 sortable + mono-microcap leaderboard headers; F4 distinct
Mock badge; F5 inspector-less route layout. After that, the remaining work is deferred backlog
(packaging·licensing·distribution, then git remote+push LAST per operator directive).
_ref:_ `_SPECS/2026-06-22-trustworthy-proof-and-polish.md` §WS-F · DS #1–#5.
