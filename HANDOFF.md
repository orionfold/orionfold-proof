# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-22 · **SHIPPED: Quick-Compare → Proof Receipt (sub-project 3 of 3).** The
sequenced **Datasets → Leaderboard → Quick-Compare** arc is now COMPLETE (all 3 done). Sub-project 3
adds a 1-prompt × 2-candidate **"Quick ⚡"** third compare mode reusing the matrix engine + exporter:
both candidates generate unscored (`{kind:"none"}`), a head-to-head shows objective bars
(latency/cost/tokens) + human **pick-a-winner**, saved as a labeled **quick-check** Proof Receipt
(`mode`+`chosen_winner`, **`RECEIPT_VERSION` 7→8**) with a promote-to-full CTA. Proof scoring,
ranking, and `config_hash` untouched. 13 TDD commits on `main`. `main` is local-only; git remote +
push stay queued LAST until packaging is done (operator directive)._

## ▶️ START HERE NEXT SESSION
1. **Optional sanity check** (web source changed): for the EMBEDDED path (`uv run orionfold dev`,
   `:8787`) run `bash scripts/build.sh` first; otherwise live source `pnpm --dir web dev`.
   - ⚠️ `:8787` may be occupied by an unrelated app here — if so run the API on a free port
     (`uv run orionfold dev --port 8790`) and the UI with
     `VITE_DEV_PORT=5174 VITE_API_PROXY=http://127.0.0.1:8790 pnpm --dir web dev` (Vite may land on
     `:5175`).
   - Quick-Compare flow: Proof Run → **Compare by → Quick ⚡** → paste a prompt (2 mock candidates
     pre-selected in Sandbox) → Run → head-to-head with objective bars (neutral ink) → pick a winner
     → **Save as Proof Receipt** → Receipts → open it → the HTML preview reads **QUICK CHECK**,
     "Picked …", **Receipt schema v8**, + "Promote to a full scored run". (Already verified this
     session — see worklog.)
2. **Then decide the next work item** with the operator. The 3-part arc is done; remaining items are
   the backlog below. **Brainstorm scope FIRST** for anything non-trivial (packaging especially).

## ✅ LAST SESSION — Quick-Compare → Proof Receipt (sub-project 3 of 3)
> Evidence: `docs/worklog/2026-06-22-quick-compare.md`. Spec + plan under
> `docs/superpowers/specs|plans/2026-06-22-quick-compare*`. 13 TDD commits on `main`.

- **Engine:** `RubricKind` gains `"none"` → `iter_matrix` skips scoring (`score`/`passed` `None`) +
  captures `input_tokens`/`output_tokens` on `ResultRow`; `build_leaderboard` `None`-safe.
- **Provenance:** `ProofRun.mode` (`"full"|"quick"`) + `chosen_winner` (candidate id / `"tie"` /
  `None`). **Excluded from `config_hash`** (hash identical before/after a pick — tested).
- **API:** `RunRequest.examples`/`mode` → ephemeral `Dataset(id="quick-compare")` (no dataset row);
  `PATCH /api/runs/{id}/winner` records+validates the pick; `list_runs` hides un-picked quick runs.
- **Receipt:** `RECEIPT_VERSION` **8**; quick branch (pick-based verdict, objective columns
  latency/cost/tokens, no failure cases, "QUICK CHECK" banner + promote note) in `build_receipt` +
  dedicated quick MD/HTML; shared `_RECEIPT_STYLE` const (full HTML byte-identical).
- **Web:** third `Quick ⚡` mode in `RunSetup` (prompt + 2-candidate lane; dataset/scoring hidden);
  `ProofCockpit` quick state + 2-candidate cap + run branch + Decide-branch on `mode`;
  `QuickCompare.tsx` head-to-head (cards, neutral-ink bars, pick, save→`patchWinner`, promote);
  pure `quickCompareFormat.ts` helpers; `patchWinner` client.
- **Verification:** backend **271** passed; web **118** passed; `tsc` clean; `ruff` clean; e2e
  **5/5** (incl. new quick flow asserting the saved receipt reads QUICK CHECK); browser-verified
  head-to-head (neutral bars, pick → accent + Save enabled); quick MD/HTML/JSON are v8 + secret-free.

## BACKLOG — non-blocking (operator picks)
1. **`pickLabel` cleanup** — implemented + tested in `quickCompareFormat.ts` but unused by
   `QuickCompare.tsx` (label derived inline). Wire into receipt-confirmation copy or drop. Trivial.
2. **Quick-Compare promote carries the prompt** — "Promote to a full scored run" currently pre-fills
   a Models run with the same 2 candidates but NOT the ad-hoc prompt (by design; a quick prompt isn't
   a frozen dataset). Future enhancement if operators want the prompt seeded into a one-example set.
3. **Stored "Recommended on 0/5"** (carried over) — some 2026-06-21 stored full runs persisted
   `recommended:true` on a 0-pass candidate (pre-gate). New runs correct. Optional one-off backfill.
4. **Catalog price/source accuracy pass** — verify list prices + context windows (`current-docs-check`).
5. **Cross-product models×prompts** — N models × M prompts in one run. **Brainstorm FIRST.**
6. **DS-skin polish** — shared token-driven badge/chip/bar kit (`.of-tag`, `TONE_BAR`, strengthened
   `ProviderTag`, the new neutral objective bar are seeds); deepen per-figure mono; receipt
   proof-seal stamp.
7. **Richer sample data** — extend `sample_data.py` if onboarding wants it.
8. **Packaging · licensing · distribution** — LICENSE + source headers, PyPI metadata (dist
   `orionfold-proof`, CLI `orionfold`; reserve `orionfold` + `orionfold-arena`),
   `uv tool install orionfold-proof` → `orionfold up`, release notes / demo script. **Scope FIRST.**
9. **git remote + push** — **LAST item; do NOT surface or start until packaging (#8) is done**
   (operator directive). No remote configured; `main` holds all work unpushed.

## Key invariants to NOT regress
- **Quick-Compare (new):** `mode`/`chosen_winner` live on `ProofRun` (JSON report blob) ONLY and are
  **EXCLUDED from `config_hash`** (a quick run's hash is identical before/after a pick). The unscored
  rubric `{kind:"none"}` yields `ResultRow.score=None`/`passed=None`; `build_leaderboard` must stay
  `None`-safe (`r.score or 0.0`). Quick runs use an ephemeral `Dataset(id="quick-compare")` — **no
  dataset row written**. `list_runs` hides quick runs with `chosen_winner is None`. Quick receipts
  use objective columns + neutral-ink bars — **never `--color-accent` (interactive) or `--color-ok`
  (PASS)** for the bars; the pick selection legitimately uses the accent (interactive).
- **`RECEIPT_VERSION` is now 8.** The quick receipt is the protected artifact's lightweight variant:
  always labeled "QUICK CHECK · not scored proof" + promote CTA; never claims scored proof.
  `_RECEIPT_STYLE` is shared by full + quick HTML (full output must stay byte-identical — guarded by
  the palette-count test in `test_receipts.py`).
- **Leaderboard `$/quality`:** `cost_per_quality` on `LeaderboardEntry` only; never a ranking key.
  Ranking sort key `(_all_errored, -pass_rate, -avg_score, avg_latency_ms,
  total_estimated_cost_usd)`.
- **Datasets metadata:** `tags`/`created_at`/`source`/`check_hint` on the DB row + API `DatasetRow`
  ONLY — never the domain `Dataset`/`Example`. Migrations append-only; next index **6**.
- **Mocks:** bare ids `mock_good`/`mock_bad`; engine labels `Mock · good`/`Mock · bad`; picker groups
  them only when Sandbox is on. Scored mock matrix `config_hash 467ddd96c9a5` unchanged.
- **Sample detection:** receipts by `run_sample…` id prefix; datasets by the `is_sample` column.
- **The accent/status split (DS skin):** cyan `--color-accent` = the only interactive colour; green
  `--color-ok` = PASS/verified ONLY; semantic-token layer only; light + dark + AA; dark is `@theme`
  default; categorical value tags neutral/squared.
- **Proof Run setup:** shared `WorkflowStep`; `compareBy` is now `"models" | "prompts" | "quick"`;
  decision recipes render only in the Models branch (recipes.json loads at backend startup — restart
  to see edits).

## Paste prompt for the next session
```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001/0002/0003,
latest worklog 2026-06-22-quick-compare, and the specs/plans under docs/superpowers/).

The sequenced Datasets → Leaderboard → Quick-Compare arc is COMPLETE (all 3 sub-projects shipped).
Optionally sanity-check the Quick-Compare flow in a browser (Proof Run → Compare by → Quick ⚡ → prompt
→ 2 mock candidates → Run → pick → Save → Receipts → receipt reads "QUICK CHECK" + schema v8), then
decide the next backlog item with the operator. BRAINSTORM scope FIRST for anything non-trivial.

RECENT WORK (committed to main; no git remote):
- (latest) QUICK-COMPARE → Proof Receipt (sub-project 3 of 3): 1-prompt × 2-candidate "Quick ⚡" third
  compare mode reusing the matrix engine + exporter; unscored {kind:"none"} generation; head-to-head
  objective bars (latency/cost/tokens, neutral ink) + human pick-a-winner; saved as a labeled
  quick-check Proof Receipt (ProofRun.mode + chosen_winner, RECEIPT_VERSION 7→8, excluded from
  config_hash) with a promote-to-full CTA. Verified: backend 271, web 118, tsc/ruff clean, e2e 5/5,
  browser + receipt-quality (v8, secret-free). Evidence: docs/worklog/2026-06-22-quick-compare.md.

BACKLOG (operator picks): pickLabel cleanup (unused); quick-promote carries the prompt; stored
recommended-on-0/5 backfill; catalog price pass; cross-product models×prompts (BRAINSTORM); DS-skin
polish; richer sample data; packaging·licensing·distribution (BRAINSTORM); git remote + push — LAST,
do NOT surface until packaging is done (operator directive).

Do NOT regress invariants in HANDOFF.md (Quick-Compare mode/chosen_winner on ProofRun only + EXCLUDED
from config_hash / {kind:"none"} → None score+passed / build_leaderboard None-safe / ephemeral
quick-compare dataset writes no row / list_runs hides un-picked quick / quick receipt v8 + neutral-ink
bars never accent-or-ok / _RECEIPT_STYLE shared full HTML byte-identical; leaderboard $/quality on
LeaderboardEntry only never a ranking key; datasets metadata DB+API-only; append-only migrations next
index 6; mock bare-ids + config_hash 467ddd96c9a5; DS accent/status split; compareBy now
models|prompts|quick).
```
