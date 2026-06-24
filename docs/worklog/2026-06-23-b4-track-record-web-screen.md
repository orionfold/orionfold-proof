# Worklog — 2026-06-23 · B4 Track Record web screen

## Summary

Shipped **BACKLOG B4** (operator-picked from the post-Stage-3 deferred backlog): the cockpit's
cross-run **Track Record** screen. This exposes the already-built pure core function
`track_record()` (`src/orionfold/proof/leaderboard.py`, from the CLI-widen slice `b2bf9d3`) over
HTTP and renders it — the "FE-only rollup reflex" the dual-distribution pivot had corrected is now
closed properly: the rollup lives in the shared core, the web screen just displays it.

The view answers one question at a glance — **which candidate has earned trust across repeated
runs** — grouped by comparable slice (dataset × rubric kind), ranked by **pooled** pass-rate
(Σpasses / Σexamples, so a larger run carries more weight), with a dataset dropdown filter.

**Additive only — no migration, no scoring/`config_hash` change.** The core fn reads existing
`LeaderboardEntry`/`ProofRun` fields and re-runs no scoring, so the mock matrix `467ddd96c9a5`
is untouched by construction.

## What changed

### Backend (1 thin route + 2 tests)
- **`server/routes.py`**: new `GET /api/track-record` (optional `?dataset_id=`) — a thin shell over
  `track_record(list_runs(conn), dataset_id=...)` (ADR-0004 §3 thin-CLI/route pattern). Imports
  `TrackRecordGroup`; registered before `/runs/{run_id}` (distinct literal path, no shadowing).
- **`tests/integration/test_proof_api.py`** (+2): `test_track_record_pools_runs_over_the_same_comparable_slice`
  (two scored runs → one group, pooled rate = Σpasses/Σexamples, won-count = recommended-count) and
  `test_track_record_filter_and_quick_exclusion` (`?dataset_id` narrows; quick/unscored runs excluded).
  Tests assert rollup invariants by reading the resolved rubric kind, not a hardcoded `"keypoint"`.

### Frontend (api client + view + nav + 2 tests)
- **`lib/api.ts`**: extracted `rubricKindSchema` (the 6-member `RubricKind` union, no behavior change to
  `rubricSchema`); added `trackRecordEntrySchema` + `trackRecordGroupSchema` (field-by-field mirror of
  the Pydantic models, reusing `Privacy`), exported types, and `getTrackRecord(datasetId?)`
  (`encodeURIComponent` on the param).
- **`features/proof/TrackRecordView.tsx`** (new): `ViewShell`-framed; a `SelectField` dataset filter
  driving the `["track-record", datasetId]` queryKey; group sections (`dataset_name` ·
  `RUBRIC_KIND_LABEL` · N runs); candidates kept in server rank order (best pooled pass-rate first),
  each a row with `ProviderTag` (privacy **carried**, not guessed), a **`--color-ok` pass-rate bar**,
  `tabular-nums` percentage, run count, and a `won N×` trophy marker when `times_recommended > 0`.
  Loading / error / two empty states (no history vs. no runs for the filtered dataset).
- **`features/proof/TrackRecordView.test.tsx`** (new, +4): renders a slice with rubric label + pooled
  rate; best-first ordering + won-count; filter narrows the query; calm empty state.
- **`app/App.tsx`**: 3 edits — `View` union += `"track-record"`, `NAV` += `TrendingUp` item (after
  Receipts), conditional render.
- **`e2e/playwright/proof.spec.ts`** (+1): nav smoke — reaches the view, asserts the heading + that the
  body is alive (empty notice OR a populated group `<h3>`), scoped to the visible `<main>` so the
  hidden mounted cockpit's text can't satisfy it.

## DS

The accent/status split holds: pass-rate bars use `--color-ok` (verified-quality = status), the view
introduces **no `--color-accent`**. Mock badges stay warn-tinted, Cloud/Local neutral (WS-F F4
preserved). Section headers are `--color-ink`; rubric subtitle / run-count are `--color-ink-faint`
(the same muted-meta tone used across `ReceiptsView` and the cockpit — an established choice, not new).

## Verification

- **Backend**: `uv run pytest` → **344 passed** (+2). `ruff` clean. `uv run pyright` → **0 errors** (full
  tree). The 8 `467ddd96c9a5` freeze-tests pass (no scoring/hash code touched).
- **Frontend**: `pnpm --dir web test` → **234 passed** (+4). `tsc --noEmit` clean. `vite build` clean
  (re-embedded into the gitignored `src/orionfold/server/static`). **14/14 Playwright** (+1 nav smoke).
- **Real-browser grade** (`browser-visual-verification`, live `:5174` over real API `:8790`,
  richly-populated DB — 11 groups spanning judge/similarity/exact/contains/keypoint, up to 18 pooled
  runs / 13 candidates):
  - **Populated** (dark + light): groups render with `dataset · rubric · N runs` headers; pooled bars
    correct (Mock·good "45/45 · 9 runs · 100%" = 5×9 pooled); `won N×` only on recommended; Cloud/Local/
    **Mock(amber)** badges distinct; theme-adapts via `var(--color-x)` (no hardcoded hex).
  - **Filter**: selecting *Investment memo summarization* narrowed to exactly its 2 groups (judge +
    similarity). **Empty**: a no-runs dataset shows "No scored runs for this dataset yet."
  - **AA**: primary text (labels, bold %) at **16.47:1** (AAA); only `ink-faint` meta is low-contrast
    (pre-existing app-wide token, supplementary not sole-carrier). **Secret-free** (0 key patterns).
  - Restored dark theme after.
- **Fresh-context diff-reviewer**: **PASS — ship it.** No invariant violations, no bugs, no scope
  creep; Zod↔Pydantic field-by-field match confirmed; config_hash/migration/DS-split verified clean.
  Flagged one tautological test assertion → replaced with a real pooled-total check before commit.

## Product impact

The cockpit now has a durable, evidence-first **scoreboard** beyond the per-run receipt: repeat the
same proof and the candidate that *consistently* earns trust surfaces, credibility-weighted by example
volume. Directly serves the north star ("decide what AI to trust"), and it's the first screen to render
a dual-distribution core fn the CLI already exposes (`orionfold track-record`) — same data, two surfaces.

## Risks

Low. FE display + one read-only route over existing data; no engine/migration/hash surface touched.
One minor UX seam surfaced and logged (does **not** block): the filter dropdown lists *current*
datasets while groups reflect *historical* run ids — so "All datasets" can show groups the dropdown
can't isolate, and a selectable dataset may have no runs (correct empty state). Captured as
`_IDEAS/backlog.md` **B8** with a low-effort fix option (drive filter options from the groups).

## Next recommended step

Operator picks from the deferred backlog. Natural next: **#7 packaging · licensing · distribution**
(BRAINSTORM/scope first per CLAUDE.md) or **B7 private-strategy symlink migration** (blocks #8 git
remote). #8 git remote + push stays LAST, gated on both. `main` local-only, all work committed.
