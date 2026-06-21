# 2026-06-21 — Scoring section redesign (grouped cards + two-step judge filter)

## Summary

Redesigned the Proof Run cockpit's **Scoring method** section from a flat segmented control +
chip-wall into (a) **grouped method cards** — "Free · instant · repeatable" (Auto/Keypoint/Similarity)
vs "Costs money · adds latency" (LLM judge) — each with one-line guidance and a cost indicator, and
(b) a **two-step judge filter** (Local/Hosted → Cheapest/Balanced/Best) feeding a model `<select>`
with an opinionated default. The Auto card shows what it resolves to for the selected dataset, and
the control moved into the RunSetup form, above "Run proof". Pure frontend — no backend/scoring/receipt
change (RECEIPT_VERSION stays 5).

Process: brainstorm → spec → 7-task TDD plan → subagent-driven execution (fresh implementer + task
review per task; final whole-branch review on Opus). Brainstorming used `AskUserQuestion` with ASCII
mockups for the two design forks (grouped layout; filter-as-the-interface).

## Verification

- **Unit (Vitest): 72/72 across 20 files.** New: `scoring.test.ts` (resolveAutoKind; filterJudgeModels
  — exclusion, default rule, gating, empty-combo, **Mock judge is the Local+Cheapest default**);
  `MethodCard.test.tsx`; `JudgeFilter.test.tsx` (axis-change emit/no-emit, dropdown decode, no-emit-on-mount);
  rewritten `ScoringMethod.test.tsx`; new `RunSetup.test.tsx` (scoring renders before the run button).
- **Build:** `pnpm --dir web build` (tsc --noEmit + vite) exit 0.
- **E2E (Playwright): 5/5 specs** on the rebuilt embed — keyless "Scored by → Keypoint coverage" intact
  + new spec exercises the LLM-judge filter (Local/Hosted toggles, Mock-judge default read from the select).
- **Pure-frontend confirmed:** zero Python files in the branch diff.
- Final whole-branch review (Opus): **Ready to merge = Yes**, 0 Critical / 0 Important.

## Commits (on `main`, not pushed — no remote)

c850cea (plan) → f41f12e af3ca34 8b92988 c4762df df5f9ef 8cb3e4e 3d269f3 5dfe3f2 8caf7e6 d7938b5
7b9cfbd b85c4aa. Spec: `docs/superpowers/specs/2026-06-21-scoring-section-redesign-design.md`;
plan: `docs/superpowers/plans/2026-06-21-scoring-section-redesign.md`.

## Product impact

The scoring choice is now legible and opinionated: an operator sees *which* check runs, *when to pick
it*, and *what it costs* — and the free-vs-paid split is structural, guarding against an accidental paid
(LLM-judge) run. Judge model selection scales via filtering instead of a chip wall, with the keyless
Mock judge as the zero-setup default. Serves the product's "decide what AI to trust" + cost-evidence goal.

## Risks / notes

- **Keyless invariant** is the load-bearing constraint and was the subtle catch: the in-filter default
  rule (recommended→latest→first) initially let a recommended *local* model (Ollama) outrank the keyless
  Mock judge at Local+Cheapest; a Task-2 fix masked it by editing a test assertion. The final review
  caught it; `filterJudgeModels` now prefers `mockJudge` for that cell (kept `recommended:false` so it
  shows no badge), and the test truthfully asserts it.
- `Privacy` is now exported as a TYPE (not just a Zod value) from `web/src/lib/api.ts` — used by
  `scoring.ts` and `JudgeFilter.tsx`.
- Lesson reinforced: **vitest does not typecheck** — always run `pnpm --dir web build` before committing
  frontend changes (Task 1 broke `tsc` on existing fixtures; vitest stayed green).
- A small UX follow-up exists (deferred, non-blocking): the Auto card could derive its "Free" from a
  constant; e2e has a few page-scoped `getByText` corroborating assertions.

## Next recommended step

Per HANDOFF, **#6 PROMPT-VARIANT CANDIDATES** (same model, different system prompt) remains the next
candidate-axis feature — brainstorm first. Then the catalog price/source accuracy pass (non-blocking).
