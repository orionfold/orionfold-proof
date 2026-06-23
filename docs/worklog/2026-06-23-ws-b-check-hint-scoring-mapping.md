# Worklog — 2026-06-23 · WS-B check-hint → scoring-method mapping + Exact card

## Summary
Stage 3, Task 4 (WS-B, MED) — recovered after a Claude Code crash mid-task, verified, and
committed. A dataset's display **check-hint** now drives the Auto-resolved scoring method, and
**Exact** equality is exposed as a selectable scoring card. Closes the hint↔method vocabulary gap
(_IDEAS issue #3, spec §WS-B).

**Crash recovery:** the prior session's WS-B edits were left uncommitted in the working tree. On
resume I inspected `git status`/diff against the last commit (`7d1eeba`, WS-A3), confirmed the dirty
changes were a near-complete WS-B (all named files + tests), verified every dependency the edits
relied on already existed (`get_dataset_meta`/`DatasetMeta.check_hint`, `checkHintLabel`,
`Dataset.check_hint`, the `exact` rubric schema), ran the full gate, then committed. No rewrites were
needed — the recovered work was coherent and complete.

## What changed
- **Backend** (`scoring/rubric.py`): `_HINT_KIND` maps `exact`/`numeric` → `exact`, `substring` →
  `contains`. `default_rubric_for(dataset, overrides, *, check_hint=None)` — an explicit hint wins
  over the keypoint heuristic; `eyeball`/empty stay on the keyless heuristic (Auto must never require
  a configured judge). `numeric` is normalized equality in v0 (tolerance check out of scope).
- **Backend** (`server/routes.py`): both Auto run-sites (`create_run`, `create_run_stream`) pass the
  dataset's `check_hint` via the existing `get_dataset_meta` — no new check logic, no migration
  (`kind="exact"`/`"contains"` already implemented in v0).
- **Frontend** (`scoring.ts`): `AutoKind` type + `HINT_KIND` mirror of the backend map; `resolveAutoKind`
  consults `dataset.check_hint` first.
- **Frontend** (`ScoringMethod.tsx`, `selectionMeta.ts`): selectable **Exact** card joins the grid
  (now 5-col); the Auto card surfaces the resolution — *"From your dataset hint: Exact match → Exact
  match."* The Exact card seeds `{kind:"exact", threshold:1, case_sensitive:false}`.

## Verification (evidence, not claims)
- **Backend:** `uv run pytest` → **298 passed** (291 → 298: +7 hint tests). Mock-hash invariant
  suite (`-k 467 or mock_hash or config_hash`) → **8 passed**; `config_hash 467ddd96c9a5` unchanged
  (mock matrix has no hint → still keypoint@0.8).
- **Frontend:** `pnpm test` → **141 passed** (136 → 141: +5 `resolveAutoKind` hint tests).
  `pnpm build` (tsc --noEmit + vite) → **clean**.
- **Browser** (Playwright, real keys in `.env.local`, Sandbox OFF, cost OK'd):
  - No-hint dataset (Investment memo) → Auto card reads "…here, Similarity", no hint line. ✓
  - Exact-hint dataset (Support ticket triage v1) → Auto card reads "…here, Exact match" + line
    *"From your dataset hint: Exact match → Exact match."* ✓ Exact card present & selectable. ✓
  - **End-to-end real run** (triage dataset + A1 classify instruction + Auto→Exact, 2 cloud
    candidates): both **100% (5/5)**, avg score 1.00, **zero failures** — "No failures — every
    candidate passed every example." 🥇 Gemini gemini-3.1-flash-lite (Recommended, $0.0001/quality),
    🥈 Anthropic claude-haiku-4-5. This is the spec's "re-verify the A1 triage proof now scores
    correctly" gate — before WS-B, Auto→Similarity would have scored exact labels partially.
  - **Receipt** (`run_6640270e9c7e`): "Rubric: exact ≥ 0.8 · Scored by: Exact match"; classify
    instruction recorded per candidate; **secret scan empty**.
  - Screenshots saved to session scratchpad (wsb-01/02/03).

## Product impact
The first real classification/extraction proof now grades correctly out of the box: a dataset tagged
"Exact match" makes Auto grade by equality (clean pass/fail) instead of partial similarity, and users
can pick Exact explicitly. Couples with A1 (task instruction) — instruction makes the model emit bare
labels; exact scoring grades them cleanly → a trustworthy "clear winner" instead of "NO CLEAR WINNER."

## Risks / notes
- The Auto-resolved exact rubric shows `≥ 0.8` (the `Rubric.threshold` field default; "exact" isn't in
  `DEFAULT_THRESHOLDS`). Harmless — exact is a **binary** check (score 1.0/0.0), so any threshold in
  (0,1] gives identical pass/fail. Not a regression; numeric-tolerance/threshold redesign is fenced
  out of WS-B scope.
- `CLAUDE.md` was also dirty from an earlier self-improvement pass (unrelated to WS-B) — committed
  **separately** (`1dc3eb1`) so history stays bisectable.

## Commits
- `5307ae5` — feat(scoring): check-hint → scoring-method mapping + selectable Exact card (WS-B)
- `1dc3eb1` — docs(claude): steering-doc refinements (separate self-improvement pass)

## Next recommended step
**Task 5 — WS-C (Decision-question integrity, MED).** Clear-unless-touched decision question on
dataset change (`decisionQuestionTouched` symmetric to `taskNameTouched`); on entering Quick mode
clear the carried question + derive the Quick receipt headline from the Quick prompt. _files:_
`ProofCockpit.tsx:84-93/243-246`, `QuickCompare.tsx:33`. See spec §WS-C.
