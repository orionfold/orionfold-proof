# 2026-06-22 — Quick-Compare → Proof Receipt (sub-project 3 of 3)

## Summary

Shipped the **final** of the three sequenced sub-projects (**Datasets → Leaderboard → Quick-Compare**):
a thin 1-prompt × 2-candidate **"Quick Compare"** entry mode that reuses the matrix engine + receipt
exporter. The operator enters a single prompt, both candidates generate (latency / cost / tokens
captured, **not scored**), and a head-to-head shows the two outputs with objective bars + a human
**pick-a-winner** (A / B / tie). The pick is saved into a clearly-labeled **quick-check Proof
Receipt** (`mode:"quick"` + `chosen_winner`, **`RECEIPT_VERSION` 7 → 8**) with a "Promote to a full
scored run" CTA. The proof engine's scoring, ranking, and the `config_hash` algorithm are untouched.

Spec: `docs/superpowers/specs/2026-06-22-quick-compare-design.md`.
Plan: `docs/superpowers/plans/2026-06-22-quick-compare.md`.

### Operator decisions (2026-06-22)
- **Judging = human pick + objective bars** — no expected answer, no rubric scoring. Bars show
  latency / cost / tokens; the winner is the operator's recorded pick.
- **Entry = third mode on the Proof Run page** — `Compare by: Models | Prompts | Quick ⚡`.
- **Receipt = same schema + a quick flag** — reuse the one exporter; add `mode` + `chosen_winner`,
  bump `RECEIPT_VERSION` to 8; quick receipts render objective columns, no failure cases, a
  "QUICK CHECK · not scored proof" banner + promote note.
- **Fork A (approved):** unscored rubric kind `{kind:"none"}` → `score`/`passed` are `None` (honest
  absence, not fake zeros).
- **Fork B (approved):** quick generation persists immediately (`chosen_winner:null`); a tiny
  `PATCH /api/runs/{id}/winner` records the pick. Un-picked quick runs are hidden from the list.
- **Tie** kept as a legitimate outcome.

## What changed (13 TDD commits on main)

Backend (`b034b32` → `c3c2a41`, `ed62680`, `f29caea`, `38944c8`, `5f965fa`, `a734d7c`):
1. `feat(engine)` — `RubricKind` gains `"none"`; `iter_matrix` skips scoring for it (`score=None`,
   `passed=None`) and captures `input_tokens`/`output_tokens` on every `ResultRow`;
   `build_leaderboard` made `None`-safe. `ProofRun.mode` + `chosen_winner` added (excluded from
   `config_hash` — verified by test).
2. `feat(api)` — `RunRequest.examples`/`mode`; `_resolve_dataset` builds an ephemeral
   `Dataset(id="quick-compare")` for inline runs (no dataset row); `PATCH /runs/{id}/winner` records
   + validates the pick.
3. `feat(storage)` — `list_runs` hides quick runs with no `chosen_winner`.
4. `feat(receipt)` — `RECEIPT_VERSION 8`; quick branch in `build_receipt` (pick-based verdict, no
   failure cases, `quick_note`) + dedicated quick Markdown/HTML renderers; shared `_RECEIPT_STYLE`
   const (full HTML byte-identical, verified by the palette-count test).

Frontend (`453012a`, `8e47ba5`, `2837fdf`, `56112ce`):
5. `feat(web)` — api schema (`none` rubric, nullable `score`/`passed` + tokens, `mode`/
   `chosen_winner`, `RunRequest.examples`/`mode`) + `patchWinner`; null-safe score guards in
   Inspector/FailureCases.
6. `feat(web)` — pure `quickCompareFormat.ts` helpers (`objectiveBar`, `totalTokens`, `pickLabel`).
7. `feat(web)` — third `Quick ⚡` compare mode in `RunSetup` (prompt textarea + 2-candidate lane,
   dataset/scoring hidden) + `ProofCockpit` quick state, 2-candidate cap, run branch.
8. `feat(web)` — `QuickCompare.tsx` head-to-head Decide view (output cards, objective bars in neutral
   ink, pick control, save → `patchWinner`, promote CTA) + `ProofCockpit` Decide branch on `mode`.

Tests: `a7cdc59` (e2e), `fcc42aa` (ruff E402 import hoist).

## Verification (evidence, not claims)

- **Backend:** `uv run pytest -q` → **271 passed** (+9 new: unscored rubric, `config_hash` exclusion,
  inline-examples run, PATCH winner ×3, list filter, quick receipt ×2, quick MD, quick HTML). `ruff
  check src tests` clean.
- **Frontend:** `pnpm --dir web test` → **118 passed** (27 → 29 files; +4 quick formatter, +2
  QuickCompare, +2 RunSetup quick). `tsc --noEmit` exit 0.
- **e2e:** `bash scripts/build.sh` then `playwright test proof.spec.ts` → **5 passed**, including the
  new `quick compare: run → pick → save receipt` (keyless mocks) — which exercises the full path and
  asserts the saved receipt's iframe reads **QUICK CHECK**, "Picked Mock · good", and the promote
  note. (The previously-flagged `:89` recipe test now passes — fixed in `9d5e4c2`.)
- **Browser (live `:5175` → `:8790`):** entered `Quick ⚡`, ran two mock candidates on a prompt,
  confirmed the head-to-head — two output cards, objective bars (latency 73ms vs 193ms, cost $0.0000,
  tokens 21 vs 30) in **neutral grey ink (never accent/green)**; picking "Mock · good" tints the card
  + fills the wins button with the accent and enables **Save as Proof Receipt**. Run config inspector
  shows dataset "Quick Compare", rubric "none · threshold 0".
- **Receipt quality + secrets:** generated quick MD/HTML/JSON → all `receipt_version: 8`, **zero**
  secret markers (`api_key`/`sk-`/`bearer`/…), verdict names the pick, promote CTA present.

## Invariants preserved

- **`config_hash` algorithm untouched** — `mode`/`chosen_winner` excluded; a quick run's hash is
  identical before and after a pick (test `test_config_hash_excludes_mode_and_chosen_winner`,
  `test_patch_winner_records_pick_and_keeps_config_hash`).
- **No migration** — `mode`/`chosen_winner` live in the JSON report blob; next migration index still 6.
- **Accent/status split** — objective bars use neutral ink, never `--color-accent`; green
  `--color-ok` stays PASS-only (a quick check has no PASS).
- **Mock bare-ids + keyless deterministic path** — quick e2e runs keyless via Sandbox mocks; the
  scored mock matrix `config_hash 467ddd96c9a5` is unaffected (quick uses the `quick-compare`
  dataset identity).
- **Receipt is the protected artifact** — quick receipts are clearly demarcated as un-scored quick
  checks and always offer promotion to a full scored run.

## Risks / follow-ups (out of scope this slice)

1. **`pickLabel` (quickCompareFormat.ts)** is implemented + unit-tested but unused by the component
   (the view derives its label inline). Harmless; wire into receipt-confirmation copy or drop in a
   future cleanup.
2. **Promotion is a fresh full run** — "Promote to a full scored run" pre-fills a Models run with the
   same 2 candidates but does NOT carry the ad-hoc prompt into a stored dataset (by design — a quick
   prompt isn't a frozen dataset). If operators want the prompt seeded, that's a future enhancement.
3. **Stored "Recommended on 0/5"** (backlog 0b) — unchanged; pre-gate stored full runs still show a
   medal. Optional one-off backfill.

## Product impact

The product now has a fast on-ramp that matches the first instinct of comparing two models —
"give them the same prompt, let me read both and pick" — without diluting the Proof Receipt's
score-backed integrity: every quick check is honestly labeled un-scored and nudges toward a full run.
With sub-projects 1–3 done, the Datasets → Leaderboard → Quick-Compare arc is complete.

## Next recommended step

Operator's pick from the backlog. Likely candidates: **packaging · licensing · distribution**
(brainstorm first) — after which the queued **git remote + push** becomes appropriate. Smaller items:
catalog price/source accuracy pass; DS-skin polish (shared token-driven badge/bar kit); optional
stored-recommended-on-0/5 backfill.
