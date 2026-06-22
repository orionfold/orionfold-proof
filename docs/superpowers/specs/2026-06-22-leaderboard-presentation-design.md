# 2026-06-22 — Leaderboard presentation (sub-project 2 of 3)

Design spec. Second of the three sequenced sub-projects scoped from the Orionfold brand /
Arena research (**Datasets → Leaderboard → Quick-Compare**). Clones the *presentation* clarity
of an Arena-style leaderboard onto our already-captured data. **Additive only**: ranking logic,
the proof engine, and provenance are untouched; one schema field (`cost_per_quality`) crosses the
receipt boundary and bumps `RECEIPT_VERSION` 6 → 7.

## Thesis

The product exists to help the operator **decide what AI to trust**. The leaderboard is where that
decision is read. Today it is a flat 7-column table; it carries the right data but does not *rank*
visually, does not surface cost-efficiency, and buries the local/private signal. This slice makes
the standings legible at a glance — rank + podium, a traffic-light pass-rate bar, a `$ / quality`
efficiency column, and a stronger local tag — without changing what the numbers *mean* or how
candidates are ordered.

## Decisions (operator, 2026-06-22)

1. **`$ / quality` lives in the receipt** — a computed `cost_per_quality` field stored on
   `LeaderboardEntry`, serialized into Markdown/HTML/JSON receipts. **`RECEIPT_VERSION` 6 → 7**
   (additive). It is a first-class trust metric clients should see in the exported receipt.
   **Ranking sort key is NOT changed** — `$/quality` is presentation only.
2. **Score bar = pass rate.** Bar length + traffic-light color encode `pass_rate` (the headline
   "how often can I trust it" number), not `avg_score`.
3. **Medals only with a real winner.** 🥇🥈🥉 decorate the top 3 rows **only when a candidate
   actually passed** (a winner is `recommended`). In the no-winner state, plain rank numbers, no
   medals — never crown a loser (consistent with the 2026-06-20 recommendation-fix gate).
4. **Local badge: strengthen per-row only.** No header banner. The privacy signal stays in the
   table rows via `ProviderTag`, with stronger (still calm) styling for the `local` variant.

**Deferred (explicitly out of this slice):** the sort toggle and the Pareto / frontier scatter
plot. Any change to the ranking sort key.

## Current state (grounding)

- **Component:** `web/src/features/proof/Leaderboard.tsx` — a scrollable `<table>` (not cards),
  `Leaderboard({ entries }: { entries: LeaderboardEntry[] })`. 7 columns: Candidate (+ inline
  "Recommended" badge when `e.recommended`), Provider (`<ProviderTag>`), Pass rate, Avg score,
  Avg latency, Est. cost, Failures.
- **Frontend type:** `web/src/lib/api.ts` `LeaderboardEntry` (Zod schema, 15 fields). No
  efficiency field.
- **Backend model:** `src/orionfold/domain/models.py` `LeaderboardEntry` (Pydantic, 15 fields,
  lines ~103-121). Built in `src/orionfold/proof/leaderboard.py`. **No `$/quality` / cost-efficiency
  field exists anywhere** today.
- **Ranking sort key** (`leaderboard.py`): `(_all_errored, -pass_rate, -avg_score, avg_latency_ms,
  total_estimated_cost_usd)`. `recommended` set on `entries[0]` only if `entries[0].pass_count > 0`.
- **Receipt:** `src/orionfold/receipts/export.py`, `RECEIPT_VERSION = 6`. JSON dumps every model
  field automatically (`[e.model_dump() for e in report.leaderboard]`). **MD and HTML leaderboard
  tables have hardcoded column headers + row templates** — a new column requires editing both
  strings.
- **Privacy badge:** `web/src/features/proof/badges.tsx` `ProviderTag` — `local` → `HardDrive` +
  "Local", `cloud` → `Cloud` + "Cloud", `provider_id.startsWith("mock")` → `FlaskConical` + "Mock".
  No standalone privacy badge; the local signal is carried only here.
- **Status tokens** (`web/src/styles/index.css`, light + dark): `--color-ok` (green, PASS),
  `--color-warn` (amber, caution), `--color-danger` (red, fail). Distinct from `--color-accent`
  (cyan, interactive only).

## Components

### 1. `cost_per_quality` — `domain/models.py`, `proof/leaderboard.py`

- **New field:** `LeaderboardEntry.cost_per_quality: float | None = None`.
- **Computation** (in the leaderboard builder, alongside the other derived fields):
  - `avg_score > 0` → `total_estimated_cost_usd / avg_score` (dollars per quality point; lower is
    better; comparable across candidates because all run the same N examples).
  - `avg_score == 0` → `None` (no quality to be efficient about → renders "—").
  - `total_estimated_cost_usd == 0` with `avg_score > 0` → `0.0` (free local/mock → renders
    "Free"; this is the local-first win, intentionally the best efficiency).
- **Ranking sort key UNCHANGED.** The field is derived and stored but never enters the sort. This
  protects the existing `test_leaderboard.py` ordering cases and the no-winner/error-last behavior.
- Docstring note: `cost_per_quality` is presentation-only and does not affect ranking.

### 2. Receipt — `receipts/export.py`

- **`RECEIPT_VERSION = 7`** (additive schema field; `.claude/rules/receipts.md` mandates the bump).
  Update the version comment.
- **JSON:** no code change — `model_dump()` picks up `cost_per_quality` automatically.
- **Markdown:** add a `$ / quality` column to the hardcoded leaderboard header string and the
  per-row `lines.append(...)` format. Formatting helper (shared by MD + HTML):
  `None → "—"`, `0.0 → "Free"`, else `f"${v:.4f}"`.
- **HTML:** add the matching `<th>` and `<td>` to the hardcoded `<thead>` / row template.
- **Samples:** regenerate with `uv run python scripts/gen_samples.py`. Diff = new
  `cost_per_quality` field on every entry + `receipt_version` 7. The bundled sample keeps
  `mock_good` 5/5 as the winner (mock cost $0.00 → `cost_per_quality` 0.0 → "Free").

### 3. Frontend type — `lib/api.ts`

- Add `cost_per_quality: z.number().nullable()` to the `LeaderboardEntry` Zod schema (TS type is
  inferred). Tolerate `null` and (defensively) `undefined` for older receipts that predate v7.

### 4. Leaderboard table — `Leaderboard.tsx` (presentational)

7 → 9 columns. All new cells derive from fields the row already has plus `cost_per_quality`.

- **Rank column (new, leading, narrow):** value = row index + 1 (entries arrive pre-sorted).
  `hasWinner = entries.some((e) => e.recommended)`. When `hasWinner`, rows 0/1/2 render 🥇/🥈/🥉;
  all other rows and the entire no-winner state render the plain rank number. Medals are decoration
  on the rank, not a separate column.
- **Pass-rate cell → score bar:** a horizontal bar whose width = `pass_rate` (0–1), fill color by
  traffic-light thresholds using **status tokens** (not the accent):
  - `pass_rate >= 0.8` → `--color-ok`
  - `pass_rate >= 0.5` → `--color-warn`
  - else → `--color-danger`
  The exact text `{Math.round(pass_rate*100)}% ({pass_count}/{total})` stays beside the bar for
  precision and screen readers. A small shared helper maps `pass_rate → token` to keep thresholds
  in one place. Use Tailwind v4 CSS-var shorthand `bg-(--color-ok)` etc.
- **`$ / quality` column (new):** render `cost_per_quality` via the same display rule as the
  receipt: `null → "—"`, `0 → "Free"`, else `$0.0012` (4 decimals). Placed after Pass rate.
- **Local tag strengthened:** in `badges.tsx`, give the `ProviderTag` `local` variant stronger but
  calm styling (e.g. a lock glyph + subtle tinted background) so the private signal reads clearly
  in each row. `cloud` and `mock` variants unchanged. Confirm any other `ProviderTag` usages still
  look right (it is shared).

### 5. Tests + samples

- **Backend `tests/unit/test_leaderboard.py` (extend):**
  - `cost_per_quality == total_estimated_cost_usd / avg_score` for a normal candidate.
  - `avg_score == 0` (all-errored or all-fail) → `cost_per_quality is None`.
  - `total_estimated_cost_usd == 0`, `avg_score > 0` (mock/local) → `cost_per_quality == 0.0`.
  - Ranking order is **unchanged** by the new field (re-assert an existing ordering case).
- **Backend `tests/unit/test_receipts.py` (extend):** `receipt_version == 7`; the `$ / quality`
  column header + a value appear in MD and HTML; the field is present in JSON. Update the existing
  hardcoded MD-header contract string to include the new column (expected with a schema change).
- **Frontend `web/src/features/proof/Leaderboard.test.tsx` (new):**
  - Medals render for top 3 only when a winner exists; no-winner fixture → plain numbers, no medals.
  - Score-bar color: a ≥0.8 row uses the ok token, a 0.5–0.8 row warn, a <0.5 row danger.
  - `$/quality` formatting: `null → "—"`, `0 → "Free"`, value → `$…`.
- **Frontend `badges.test.tsx` (extend):** the strengthened `local` variant renders its
  glyph/label; `cloud`/`mock` unchanged.

### 6. Verification (beyond unit tests)

- `pnpm --dir web test` + `tsc`, `uv run pytest`, `ruff`, `pyright` on changed files.
- **`browser-visual-verification`** on the leaderboard route with a winner fixture and a no-winner
  fixture — screenshot, confirm: medals only when a winner exists, bar colors match thresholds,
  `$/quality` column reads cleanly, local tag is legible. Calm, not noisy.
- **`receipt-quality-review`** (receipt structure changed): generate a sample receipt, inspect the
  new `$ / quality` column in MD/HTML/JSON, confirm no secrets, confirm the column is clear and
  client-shareable.
- `bash scripts/build.sh` + the existing Playwright smoke (leaderboard/receipt path) green.

## Test contract (must not regress)

Existing happy-path strings stay green because the bundled sample keeps `mock_good` 5/5:
`"100% (5/5)"`, `"Failure cases (5)"`, heading "Orionfold Proof", `/Run proof/`, the Leaderboard /
Failure cases / Proof Receipt export regions, "Export Markdown|HTML|JSON", and the no-winner verdict
vocabulary (`"No clear winner"`). The **MD leaderboard header contract string changes** (gains
`$ / quality`) — that is the intended, version-bumped schema change, not a regression.

## Out of scope / invariants held

- **Provenance untouched:** no change to `config_hash` (`467ddd96c9a5`), `run.*`, `proof/engine.py`,
  the provider boundary, or the domain `Dataset`/`Example`/`Candidate` models. `cost_per_quality`
  lives on the derived `LeaderboardEntry` report object only.
- **Ranking determinism held:** the sort key is unchanged; the new field never enters ranking.
- **No-winner state held:** medals + recommend badge both gate on `recommended`; the score bar shows
  red bars and `$/quality` shows "—" for 0-score rows. Coherent with the 2026-06-20 fix.
- **DS skin held:** the score bar uses **status** tokens (`--color-ok`/`--color-warn`/
  `--color-danger`), never the cyan `--color-accent` (interactive only). Calm instrument, not a
  noisy traffic-light dashboard. Tailwind v4 CSS-var shorthand `bg-(--color-x)`.
- **Deferred:** sort toggle, Pareto/frontier scatter.
- No secrets in receipts/UI/logs (unchanged surfaces). Migrations: none (no DB change; the field is
  a derived report value, not a persisted dataset column).

## Files touched

- `src/orionfold/domain/models.py` — `cost_per_quality` field.
- `src/orionfold/proof/leaderboard.py` — compute `cost_per_quality` (ranking unchanged) + docstring.
- `src/orionfold/receipts/export.py` — `RECEIPT_VERSION` 7, `$ / quality` column in MD + HTML,
  shared format helper.
- `web/src/lib/api.ts` — `cost_per_quality` in the schema.
- `web/src/features/proof/Leaderboard.tsx` — Rank/medals column, score bar, `$ / quality` column.
- `web/src/features/proof/badges.tsx` — strengthened `local` `ProviderTag` variant.
- `tests/unit/test_leaderboard.py`, `tests/unit/test_receipts.py` (extend).
- `web/src/features/proof/Leaderboard.test.tsx` (new), `badges.test.tsx` (extend), fixtures as
  needed.
- `samples/receipts/*` — regenerated (`scripts/gen_samples.py`).
