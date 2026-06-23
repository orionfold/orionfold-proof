# Worklog — 2026-06-23 · WS-F DS application-consistency pass (Task 11)

## Summary

Closed Task 11 — the **last open queue item** in Stage 3. WS-F is a design-system
*application-consistency* pass (NOT color drift — the token foundation already matches the
reference kit: `#14c8c0` cyan, Geist). Shipped all five items in one session per operator decision.

- **F1 — seed sample dataset metadata.** `repository.insert_sample_dataset` now writes the same
  display-metadata columns a user-imported dataset gets (`created_at` / `source` / `check_hint`);
  `sample_data.seed_sample_data` passes `SAMPLE_CREATED_AT` (`2026-06-19T12:00:00Z`),
  `SAMPLE_SOURCE="Bundled with Orionfold"`, and `SAMPLE_CHECK_HINT="eyeball"` (summaries are
  paraphrased free-form, graded by judgment — the demo defaults to the LLM judge — so "eyeball" is
  the honest hint). The seeded "Sample · investment memo summarization" card now reads
  `5 examples · created 6/19/2026 · Bundled with Orionfold` + an "Eyeball / judgment" hint chip,
  matching the user-set "Support ticket triage v1" card. **No migration** — the
  `tags/created_at/source/check_hint` columns already exist (migration index 5); the bug was that the
  *sample* insert path skipped them while the *user-import* path wrote them. Display-only columns;
  the engine never reads `check_hint`, so `config_hash` is untouched.
  - ⚠️ The fix only takes effect on **(re)seed** — a stale pre-fix sample row keeps its bare metadata
    until `POST /api/sample-data/seed` (Settings → Seed sample data) re-seeds it (`seed_sample_data`
    calls `remove_sample_data` first, idempotent).

- **F2/F3 — sortable + mono-microcap leaderboard headers.** `Leaderboard.tsx` gained client-side
  column sorting (per the reference `.tbl`): each sortable header is a real `<button>` (keyboard/AT),
  the `<th>` carries `aria-sort`, the active column turns cyan accent with a directional arrow
  (`↕` inactive / `↑` asc / `↓` desc). Headers wear the reference mono micro-caps voice
  (`font-mono text-[10px] uppercase tracking-[0.06em] text-(--color-ink-muted)`). **The server
  ranking is the default on load** (`column: null` → rows untouched, podium medals meaningful); once
  the user clicks a column we enter a transient explore-sort and **medals are suppressed** (the
  verdict order is left behind) — the recommended-row highlight stays tied to `entry.recommended`, not
  index. Pure sort logic extracted to new `leaderboardSort.ts` (+test): stable sort with the server
  order as tiebreak, natural first-click direction per column (best-first), null `$/quality` always
  sinks to the bottom regardless of direction.

- **F4 — distinct Mock badge.** The Mock `ProviderTag` now carries a quiet warn tint
  (`border-(--color-warn)/40 bg-(--color-warn)/10 text-(--color-warn)`) per the reference `.badge.warn`
  — simulated ≠ real reads at a glance, distinct from the neutral Cloud/Local identity tags. Cloud and
  Local are unchanged. The base `<span>` no longer hardcodes `border/bg`; each kind owns its full
  surface via a `cls` (Cloud/Local share a `NEUTRAL_SURFACE` const, Mock the warn tint) so the kinds
  never collide on a Tailwind property. Warn = "not a real run" (caution), never green (PASS) or cyan
  (a control).

- **F5 — inspector-less route layout.** `ViewShell` (Datasets / Candidates / Receipts / Settings)
  wraps its content in a `max-w-5xl` left-anchored column so it no longer reads as full-bleed sprawl
  vs the cockpit's `main + 22rem inspector` grid. **Widen-main-column-only** (operator decision) — no
  new right-rail content/fetches.

## Verification

- **Backend:** `uv run pytest` → **298 passed** (unchanged; F1 extended an existing seed test). The
  byte-identical receipt guard `test_html_receipt_carries_both_palettes` passed — `receipts/export.py`
  untouched, so the full-receipt HTML is byte-identical.
- **Frontend:** `pnpm test` → **230 passed** (+18 net: 11 in `leaderboardSort.test.ts`, +7 across
  `Leaderboard.test.tsx`/`badges.test.tsx`). `tsc --noEmit` exit 0; `pnpm build` clean.
- **Lint/types (touched py):** `ruff check` + `pyright` clean.
- **E2E:** `pnpm exec playwright test` → **13/13 passed** (re-embedded the build into the gitignored
  `src/orionfold/server/static`).
- **Real browser, light + dark** (`browser-visual-verification`):
  - F1 — Datasets sample card shows the full metadata line + "Eyeball / judgment" chip (after a
    re-seed of the stale row).
  - F2 — clicking "Avg latency" reordered rows latency-ascending, turned the header cyan with `↑`,
    set `aria-sort`, and swapped medals→plain ranks; recommended highlight stayed put.
  - F3 — headers render mono micro-caps with `↕` arrows in both themes.
  - F4 — a keyless mock run (Sandbox ON, then restored OFF) shows the amber warn-tinted Mock badge,
    distinct from the neutral Cloud tags; AA-readable in both themes.
  - F5 — Datasets/Settings content width-capped + left-anchored, balanced.
  - Secret-free; no API keys on screen.
  - Restored Sandbox OFF + theme dark (operator defaults) after the check.

## Product impact

The first-proof and leaderboard surfaces now read with the reference kit's "receipt voice" and let
the user explore the verdict by any dimension without losing the recommended call-out. The seeded
sample no longer looks thinner than a user's own dataset, and simulated Mock candidates are
unmistakable from real Cloud/Local ones — all reinforcing "this is a trustworthy, repeatable proof."

## Risks / deferrals

- **Stale sample metadata (F1):** existing installs with a pre-fix seeded sample keep the bare
  metadata line until they re-seed. Acceptable — the demo path (CTA / Settings seed) re-seeds; a fresh
  install seeds correctly on first startup. No backfill migration (display-only, low value).
- An ad-hoc keyless **mock run** was written to `~/.orionfold/proof.db` during F4 verification (free,
  Sandbox since restored OFF). Clear via Settings → data management for a pristine demo state if wanted.

## Next recommended step

**The point queue is now EMPTY.** Remaining work is all deferred backlog: packaging · licensing ·
distribution (BRAINSTORM first) → then git remote + push **LAST** (operator directive — do not surface
until packaging is done). No further Stage-3 point-tasks.
