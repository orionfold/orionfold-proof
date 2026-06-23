# 2026-06-23 — WS-C: Decision-question integrity (config + Quick)

## Summary
Stage 3, Task 5 of the approved spec (`_SPECS/2026-06-22-trustworthy-proof-and-polish.md` §WS-C).
The Proof Brief's **decision question** headlines the receipt, so it must never silently contradict
what's under test. Fixed two surfaces with one rule ("don't carry a question that no longer matches"):

- **Config-time (#1):** Added `decisionQuestionTouched` state, symmetric to the existing
  `taskNameTouched`. An *untouched* question now **clears** on dataset change — unlike the task name
  there's no dataset→question mapping to re-derive from, so clearing (falling back to the placeholder)
  is the honest behavior. A typed or recipe-selected question is "touched" and survives dataset
  switches. `onSelectRecipe` marks touched so a deliberately chosen recipe question persists.
- **Quick mode (#2):** Quick has no dataset to anchor a title, so the saved Quick receipt headline
  now **derives from the Quick prompt** via a new pure `quickDecisionHeadline()` (whitespace-collapsed,
  trimmed, 120-char cap with ellipsis; blank → empty so `QuickCompare` falls back to task name) —
  never the stale question carried over from a prior Models-mode config.

Pure logic lives in a new `briefHelpers.ts` (`effectiveDecisionQuestion`, `quickDecisionHeadline`)
for unit testing, matching the codebase's `*Helpers.ts`/`*Format.ts` convention.

**Frontend-only.** No backend, no migration, no `RECEIPT_VERSION` bump — `decision_question` is a
content field that was never part of `config_hash`, so the canonical mock matrix `467ddd96c9a5` is
unaffected. (Spec confirmed no schema change.)

_files:_ `web/src/features/proof/briefHelpers.ts` (new) · `briefHelpers.test.ts` (new) ·
`ProofCockpit.tsx` (state + `effectiveBrief` + `handleBriefChange` + `onSelectRecipe` + Quick payload) ·
`ProofCockpit.test.tsx` (+2 integration tests). Commit `1864b35`.

## Verification
- **FE unit:** `pnpm test` → **150 passed** (+9: 7 `briefHelpers` + 2 `ProofCockpit` integration).
- **Types/build:** `tsc --noEmit` + `vite build` clean.
- **BE:** `uv run pytest` → **298 passed**, unchanged (FE-only change; mock hash intact by construction).
- **Browser (real keys in `.env.local`, Sandbox OFF, cost OK'd), Playwright-driven:**
  1. Fresh load → Decision question field **empty** (no stale default "Which model should I trust for
     client memo summaries?").
  2. Select "Different providers" recipe → question = "Same model, different hosts…"; switch dataset
     (Investment memo → Support ticket triage) → task name re-derives to the new dataset, recipe
     **question survives** (deliberate choice = touched). No contradiction.
  3. Enter Quick mode → carried question gone (field hidden); type prompt "Write a one-sentence
     haiku-free summary of why local-first AI proof receipts matter."; run Haiku 4.5 vs Gemini
     3.1 Flash-Lite → QuickCompare headline = **the prompt**. Pick Gemini → Save.
  4. Persisted run (`GET /api/runs`) `brief.decision_question` = the prompt; **exported MD**
     (`receipt.md`) `**Decision:**` line = the prompt, `**Task:**` = "Support ticket triage v1".
     Receipt **secret-free**.
- **Review:** fresh-context `diff-reviewer` confirmed the diff faithfully implements WS-C, the
  touch-detection logic is correct against the empty-baseline, and all invariants are preserved.

## Product impact
The protected artifact (Proof Receipt) can no longer headline with a question that contradicts the
dataset or the ad-hoc prompt it was actually run on — both at config time and frozen into a saved
Quick receipt. Directly closes _IDEAS issues #1 (stale at config) and #2 (frozen into Quick receipt).

## Risks
- `DEFAULT_BRIEF.decision_question` seed is now effectively dead on first paint (always suppressed
  until touched). Harmless — the spec accepts clear-unless-touched; could be tidied later.
- The export-path headline correctness is verified manually (browser→API→MD), not by an automated
  integration test — matches the spec's stated minimum ("FE unit on the clear/derive logic").

## Next recommended step
**Task 6 — WS-D1 (Pareto cost-vs-quality scatter, MED).** Reuse Arena `FrontierScatter.jsx` beneath
the leaderboard; accent only the recommended point. Verify: Vitest on `paretoFrontier()` +
Playwright mount on a populated run. (§WS-D1 · feature #2.)
