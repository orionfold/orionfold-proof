# Worklog — 2026-06-23 · WS-A3 Cloud LLM judge + sane Sandbox-OFF default

## Summary

Stage 3, Task 3 (WS-A3, HIGH). Fixed the defect where a cloud-only operator running an
**LLM-judge** proof with Sandbox OFF silently landed on the **Mock judge** — contradicting
"real evaluation." The judge step now opens on a **real** judge when one exists, and is
**disabled with a hint** when none does.

The spec's "CORRECTION" note held: the backend `selection_panel()` already emits key-gated
cloud providers (with `available` reflecting live key resolution), and `filterJudgeModels`
already surfaces them under the Hosted cell. The only defects were the **default selection**
(hardcoded Local+Cheapest → `mock_judge`) and the absence of a disabled state. **Frontend-only
change — no backend edit, no migration, mock `config_hash` untouched.**

## What changed

- **`scoring.ts`** — new pure `defaultJudgeCell(panel, sandbox)` → `JudgeCell | null`:
  - Sandbox ON → `{local, economy, mock_judge}` (the keyless Mock judge's spec-invariant home).
  - Sandbox OFF → first cell (cloud first, then local; cheapest tier first) whose **options**
    contain a real (non-mock) judge, preferring recommended → latest → first. Scans `options`,
    not `defaultProviderId`, because the Local+Cheapest cell always pins Mock as its UI default
    even when a real Ollama model is present.
  - No real judge + Sandbox OFF → `null` (caller disables the method).
- **`ScoringMethod.tsx`** — reads `["selection"]` + `["settings"].sandbox_enabled`; selecting the
  judge method seeds `judge_provider_id`/`judge_model` from `defaultJudgeCell` (not hardcoded
  `mock_judge`). The LLM-judge card is **disabled** (with "add a provider key or start Ollama"
  copy) when ready and `defaultJudgeCell` is null. `judgeReady = settings loaded && (sandbox ||
  panel loaded)`; `judgeCell` is `undefined` until ready, and the judge method **only commits when
  `judgeCell` is a real cell** — never a guessed `mock_judge`. This closes a stale-Mock bug the diff
  review caught: clicking judge before `["selection"]` resolved used to emit `mock_judge`, which then
  diverged from the (now-real) dropdown and silently graded with Mock.
- **`JudgeFilter.tsx`** — new optional `initialCell` prop opens the Run-on / Optimize axes on the
  sane default cell (Hosted + real judge when Sandbox is off).
- **`MethodCard.tsx`** — optional `disabled` prop (dim + non-interactive; guidance stays readable).

## Verification (evidence, not claims)

- **Backend:** `uv run pytest` → **291 passed** (unchanged — no Python touched).
- **Frontend:** `npx vitest run` → **136 passed** (was 128; +5 `defaultJudgeCell` units in
  `scoring.test.ts`, +3 net in `ScoringMethod.test.tsx`). `tsc --noEmit` + `vite build` clean.
  - `scoring.test.ts` asserts the invariant: Sandbox OFF + cloud key → cloud judge (never mock);
    Sandbox OFF + local-only → real Ollama (never mock); no real judge + Sandbox OFF → `null`.
  - `ScoringMethod.test.tsx`: Sandbox OFF + no real judge → judge card **disabled**, no rubric
    emitted (no Mock fallback); Sandbox OFF + cloud key → defaults to `anthropic/haiku` (and asserts
    `mock_judge` was never emitted across the full call history); clicking judge **before the panel
    loads** is a no-op (no stale Mock); Sandbox ON → keyless Mock judge.
- **Browser (real keys, Sandbox OFF, :5175 → API :8790):**
  - Live `/api/selection` shows all cloud providers `available=True`; `/api/settings`
    `sandbox_enabled=False`, thresholds at A2 defaults.
  - Selecting **LLM judge** opened on **Run on → Hosted · Optimize → Cheapest · Judge model →
    "Claude Haiku 4.5 · Anthropic"** — a real cloud judge, NOT "Mock judge".
  - End-to-end run (Claude Haiku 4.5 + Gemini 3.1 Flash-Lite, summarization dataset, no task
    instruction): completed with a **clear winner** — *RECOMMENDED Gemini · gemini-3.1-flash-lite,
    Passed 3/5 (60%), avg score 0.78*, **"Scored by LLM judge · claude-haiku-4-5"**, judge cost
    $0.0059 / total $0.0131. Graded by a real model; not "no winner."

## Product impact

The first real LLM-judge proof a cloud-only user runs now grades with a real model and reads as
trustworthy — closing _IDEAS issue #6. The disabled-with-hint path keeps the product honest: it
never labels a Mock-graded run as "real evaluation."

## Risks / deferrals

- The in-browser **disabled** path could not be reproduced live (real keys make a "no judge"
  state impossible without removing credentials); it is covered by the `ScoringMethod.test.tsx`
  unit. Low risk — the guard is a pure `panel !== undefined && defaultJudgeCell === null`.
- Out of scope per spec: judge ensembles / multi-judge; judge cost optimization beyond the
  existing tier toggle.

## Next recommended step

Task 4 — **WS-B: check-hint → scoring-method mapping + selectable Exact card** (MED). See
`_SPECS/2026-06-22-trustworthy-proof-and-polish.md` §WS-B and the HANDOFF NEXT TASKS queue.
