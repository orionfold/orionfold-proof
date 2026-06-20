# 2026-06-20 — Wire the left-rail destinations (Datasets · Candidates · Receipts)

## Summary
Turned the cockpit's three "soon" rail markers into real, navigable views. **Frontend-only —
no backend, endpoint, noun, or receipt-schema change**; all three views are fed by endpoints that
already existed (`GET /api/datasets`, `GET /api/candidates`, `GET /api/runs`). Operator decision
this pass (via `AskUserQuestion`): a Receipts row, when clicked, **reopens that past run in the
Proof Run cockpit** (leaderboard + failures + inspector) rather than being a separate viewer.

- **Rail is now navigation.** `App.tsx` `NAV` items became real `<button>`s with `aria-current`;
  the `soon` markers are gone. A `useState<View>` switches the content area — **no router library**
  (4 flat destinations don't justify a dependency or URL routing in v0). Proof Run is the default,
  so every existing vitest/e2e assertion (heading, "Connected", `/Run proof/`, both mocks) still
  passes untouched.
- **State lifted to App.** The cockpit's `report` moved up to `App` so a Receipts row can seed it
  and switch views. `ProofCockpit` is now **controlled** (`report` + `onReport` props); the run
  mutation calls `onReport` on success and invalidates the `["runs"]` query so the Receipts archive
  stays current. A `useEffect` keyed on `report.run.id` clears any failure-case selection when the
  shown run changes (fresh run or one reopened from Receipts).
- **Proof Run stays mounted** (toggled with `display:none` via the `hidden` class, not unmounted)
  so an in-flight run, the brief, and the result survive a side trip to the other views. `display:
  none` also drops it from the a11y tree / tab order, so the rail never tabs into hidden cockpit
  controls. The `contents` class lets the cockpit's own grid be the content-column grid item.
- **New views** (`features/proof/`): `DatasetsView` (each dataset + a `<details>` of its
  input/expected examples), `CandidatesView` (label · `ProviderTag` · provider id · pinned model —
  the provider boundary reads at a glance), `ReceiptsView` (past runs newest-first: decision,
  winner, pass rate, config hash in mono, timestamp, three download links; clickable summary
  reopens the run). Shared `ViewShell`/`ViewNotice` keep the frame and loading/error/empty states
  consistent. New API client fn `getRuns()`.
- HTML correctness: each receipt's clickable summary is a `<button>` and the download `<a>`s live
  **outside** it (anchors must never nest inside a button).

New files: `App` views `DatasetsView.tsx`, `CandidatesView.tsx`, `ReceiptsView.tsx`,
`ViewShell.tsx`; tests `ReceiptsView.test.tsx`, `test/fixtures.ts`; evidence script
`scripts/capture_rail_views.mjs`.

## Verification
- **Tests (all green):** `pnpm --dir web test` → **8 passed** (3 new: rail→Datasets nav,
  Receipt→cockpit round trip, ReceiptsView list/click/empty; 5 existing unchanged). `pnpm --dir web
  build` (tsc + vite) clean. Backend untouched but re-run to be safe: `uv run pytest` → **65
  passed**, `ruff check .` clean, `uv run pyright src` → **0 errors**. `pnpm --dir web e2e` →
  **1 passed** (charter happy path against the embedded build — default Proof Run view intact).
- **Browser visual verification** (Claude-in-Chrome + Playwright against `orionfold up` on a
  provably-free port, embedded build, temp DB, listener PID asserted ours):
  - _Proof Run (default)_ — rail shows four real items, Proof Run active; setup + mocks render.
  - _Datasets_ — card with description + expandable Input/Expected examples (all 5).
  - _Candidates_ — every candidate with Mock/Local/Cloud tag + pinned model.
  - _Receipts (empty)_ — calm "No proof runs yet" notice on a fresh DB.
  - _Receipts (populated)_ — after a run, the new receipt appears (cache invalidation), with
    winner, config hash, timestamp, and Markdown/HTML/JSON download links.
  - _Round trip_ — clicking the receipt switched to Proof Run with that run loaded (same config
    hash `b7b5b150bb67`, winner band, leaderboard).
  - _Keyboard_ — teal `:focus-visible` ring on the rail buttons; tab order logical.
  - Evidence: `samples/screenshots/rail-{datasets,candidates,receipts}.png`.

## Product impact
The product map the rail promised is now real: a builder can browse the frozen datasets and the
available candidates (and see at a glance which are free/private vs. paid/cloud), and — most
importantly — find every past Proof Receipt in one place and reopen any of them back into the
cockpit to re-read the verdict. The decision artifact is no longer trapped in a single session.

## Risks / follow-ups
- Settings remains a disabled `soon` marker (out of scope; deliberate).
- View state is in-memory `useState` (no deep-linkable URL). Fine for v0; revisit only if shareable
  view links become a real need.
- `scripts/capture_rail_views.mjs` is a dev-only evidence helper (run from `web/` with a server
  port); not wired into CI.
- ADR-0003 (progress-based streaming timeout) still owed — untouched this pass.
- Screenshots + code are **uncommitted**, awaiting operator review (this project commits to `main`
  only when the operator asks).

## Next recommended step
Operator review of the four views (screenshots above). On approval, commit to `main`. Then
ADR-0003 (progress-based timeout) is the main remaining owed item.
