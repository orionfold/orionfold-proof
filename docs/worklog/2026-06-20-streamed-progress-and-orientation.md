# 2026-06-20 — Streamed run progress + orientation touches

## Summary
Long runs no longer go silent. Replaced the cockpit's single "pending" boolean with **live,
streamed progress** (the operator's recurring pain: an LM Studio run took ~39s with no feedback),
and added four calm **orientation** touches so a newcomer always knows where they are and what's
next. Folded in **ADR-0003** to record the streaming architecture and the path to the owed
progress-based timeout.

### Streamed progress (backend + frontend; ADR-0003)
- **Engine iterator.** `engine.iter_matrix()` yields one scored `ResultRow` per cell,
  candidate-major; `run_matrix()` is now `list(iter_matrix(...))`. Identical cell logic/ordering
  — only the shape differs; engine stays deterministic and clock-free.
- **SSE endpoint.** New `POST /api/runs/stream` (`text/event-stream`) beside the unchanged batch
  `POST /api/runs`. Frames: `start` (total, n_examples, ordered candidates), `progress`
  (cumulative `done` + last cell's pass/error), `report` (full persisted `ProofReport`).
  Validation runs synchronously before the stream opens, so a bad request is a normal 4xx.
- **Tiny frames, client-derived detail.** Because cells run candidate-major, the client computes
  the currently-running cell (`candidates[floor(done/n)]`, example `done%n`) and each candidate's
  completion (`clamp(done−k·n,0,n)`) from `done` + the `start` plan — so progress frames carry
  only a number. `createRunStream` reads the stream via `fetch` + `ReadableStream` and resolves
  with the validated report, so it drops into the existing TanStack mutation unchanged.
- **`RunProgress.tsx`** (new): spinner + determinate bar (`done/total`), "Now running {candidate}
  · example x/n" with provider tag, and a per-candidate completion list. No new deps, no jobs.

### Orientation touches (all calm, `prefers-reduced-motion`-safe)
- **Stage stepper** (`StageStepper.tsx`): a quiet "Configure → Run → Decide" map atop the
  workspace; current stage is accent, past stages get a check. Derived from run/report state.
- **First-run nudge**: the Run proof button gets a soft `breathe` ring only before the first run
  (and only when runnable); gone once you've run.
- **Inline field helpers**: one-line plain-language hints under Dataset, Candidates, and Decision
  question in `RunSetup`.
- **Calm result reveal**: results fade/slide in (`animate-reveal`) and the winner card gets one
  quiet lift (`animate-emphasis`) when a run completes. Motion tokens registered in `@theme`;
  the existing reduced-motion guard neutralizes them.

New files: `RunProgress.tsx`, `RunProgress.test.tsx`, `StageStepper.tsx`,
`docs/adr/0003-streaming-run-progress.md`. Touched: engine, routes, `lib/api.ts`,
`ProofCockpit.tsx`, `RunSetup.tsx`, `styles/index.css`, the API integration test.

## Verification
- **Tests (all green):** `uv run pytest` → **67** (+2: stream emits start/progress/report &
  persists; stream rejects unknown dataset). `ruff check` clean; `uv run pyright src` → **0**.
  `pnpm --dir web test` → **10** (+2: RunProgress derives the current cell/per-candidate counts
  from `done`; shows finishing message). `pnpm --dir web build` clean. `pnpm --dir web e2e` →
  **1** (happy path now exercises the SSE run end-to-end in a real browser).
- **Browser visual** (Playwright against `orionfold up`, fresh build/temp DB, listener PID
  asserted mine): _configure_ (stepper Configure, field helpers, first-run CTA), _progress_
  (CDP-throttled so frames trickle — captured at 9/10 with the determinate bar + "Now running
  Mock·bad · example 5 of 5", stepper on Run), _decide_ (stepper Configure✓ Run✓ Decide, results
  revealed, inspector populated). Evidence: `samples/screenshots/stream-{configure,progress,
  decide}.png`. Mocks don't sleep, so the throttle is how the live panel is observed honestly.

## Product impact
A run is now legible while it happens — how far along, which candidate/example is active, and
when it's wrapping up — which matters most exactly when it matters least to be in the dark (slow
local models). The stepper, helpers, and first-run nudge lower the "what do I do / where am I"
barrier for a first-time user without adding dashboard noise. The streaming substrate is also the
liveness signal a future idle timeout will key off (ADR-0003 §follow-up).

## Risks / follow-ups
- Two run endpoints (batch + stream) to keep in step; mitigated by the shared engine iterator.
- The progress-based **idle timeout** itself is deliberately deferred (ADR-0003 follow-up):
  per-class defaults in `providers/http.py` + the four providers, with its own verification.
- Mock providers complete near-instantly, so the live panel only shows meaningfully for real/slow
  providers; the throttled capture and the `RunProgress` unit test cover it.

## Next recommended step
Operator review of the streamed progress + orientation (screenshots above). On approval, the
remaining owed item is ADR-0003's follow-up: implement the progress-based idle timeout.
