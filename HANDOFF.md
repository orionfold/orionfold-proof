# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-22 · **E2E verification of the shipped arc + 2 fixes.** Browser-walked all
three shipped sub-projects (Datasets · Leaderboard · Quick-Compare) end to end — all healthy. Fixed
(1) the **Receipts archive list** showing "No clear winner" for quick-compare receipts that had a
recorded pick (read `leaderboard.recommended`, always empty for unscored quick runs, instead of
`run.chosen_winner`; now "Picked &lt;label&gt;" / "Tie"), and (2) the **keyless Quick-Compare demo**
which was a degenerate good-vs-bad (mock_good rendered blank, mock_bad could randomly error) — now
mock_good condenses the prompt into a summary-shaped line and mock_bad never errors in quick mode.
Also removed the dead `pickLabel` helper. 5 commits on `main` (`b06face`, `aea1931`, `445990d`,
`9d9b577`, `0fe7c61`). The sequenced **Datasets → Leaderboard → Quick-Compare** arc remains COMPLETE.
`main` is local-only; git remote + push stay queued LAST until packaging is done (operator directive)._

## ▶️ START HERE NEXT SESSION
1. **No verification debt.** This session ran the full E2E browser walk of the shipped arc; all green
   and the one bug found is fixed (see below). No re-check needed before new work.
   - To bring the app up: live source `pnpm --dir web dev`; EMBEDDED path (`uv run orionfold dev`,
     `:8787`) needs `bash scripts/build.sh` first. ⚠️ `:8787` may be occupied by an unrelated app
     here — if so run the API on a free port (`uv run orionfold dev --port 8790`) and the UI with
     `VITE_DEV_PORT=5174 VITE_API_PROXY=http://127.0.0.1:8790 pnpm --dir web dev` (Vite may land on
     `:5175`). Both `:5174` and `:5175` proxy to the same API; the unrelated `:8787` app returns a
     different health shape (`{"ok":true,"token_required":true}`) — ours is `{"status":"ok",...}`.
2. **Decide the next work item** with the operator. The 3-part arc is done; remaining items are the
   backlog below. **Brainstorm scope FIRST** for anything non-trivial (packaging especially).

## ✅ LAST SESSION — E2E verification + Receipts-list quick-pick fix
> Evidence: 2 TDD commits on `main` (`b06face` fix, `aea1931` cleanup) atop the quick-compare arc.
> Prior arc evidence: `docs/worklog/2026-06-22-quick-compare.md`.

- **Bug fixed (`ReceiptsView.tsx`):** the archive list derived its summary winner only from
  `leaderboard.find(e => e.recommended)`. Quick runs are unscored (`{kind:"none"}`) → nothing is
  recommended → every *picked* quick receipt collapsed to a misleading **"No clear winner"** (the
  receipt *detail* was correct — it reads `chosen_winner`). The card now branches on
  `run.mode === "quick"`, resolves `run.chosen_winner` (id / `"tie"` / `null`) against
  `run.candidates`, and renders **"Picked &lt;label&gt;"** + `ProviderTag` (or "Tie — no clear
  winner"). Scored-run path unchanged, gated behind `!isQuick`. TDD: 2 new `ReceiptsView` tests
  (a quick `QUICK_REPORT` fixture), red→green, **browser-confirmed** the list now reads "Picked Mock
  · good".
- **Cleanup (`aea1931`):** removed the dead `pickLabel` helper + its test (was built/tested but never
  wired — it emitted candidate *ids*, while the UI resolves *labels*).
- **Keyless quick-compare demo fix (`0fe7c61`, spec `9d9b577`):** in quick mode there is no expected
  answer (`{input_text, expected_text: ""}`), so the keyless mock pair was degenerate — `mock_good`
  returned the empty expected → blank "—", and `mock_bad` could randomly error (~1/5). Keyed on the
  quick-mode signal **`expected_text == ""`** (no provider-interface change): `mock_good` now
  synthesizes a plausible on-topic output via **`_condense`** (strip a leading "instruction:" clause,
  keep the leading sentence capped to a ~28-word budget, trimmed at a word boundary); `mock_bad`
  suppresses its 1-in-5 error in quick mode (always a weak answer). Scored/dataset runs are
  **unchanged** (good echoes expected byte-identically; bad still errors ~1/5 → failure-case browser
  intact). Spec: `docs/superpowers/specs/2026-06-22-quick-compare-mock-demo-design.md`.
- **Verification:** web **119** passed; backend **275** passed (+4 mock tests); `tsc` + `ruff` clean;
  worktree clean. E2E browser walk confirmed Datasets, Leaderboard (ranking, $/quality, failure
  browser, recommendation gate, receipt export panel), and the full Quick-Compare save→v8-receipt
  path are all healthy; browser-confirmed the keyless quick head-to-head now reads good-vs-bad.

### Arc reference — Quick-Compare → Proof Receipt (sub-project 3, shipped earlier)
- **Engine:** `RubricKind` `"none"` → `iter_matrix` skips scoring (`score`/`passed` `None`) +
  captures `input_tokens`/`output_tokens`; `build_leaderboard` `None`-safe.
- **Provenance:** `ProofRun.mode` + `chosen_winner`, **excluded from `config_hash`**.
- **API:** ephemeral `Dataset(id="quick-compare")` (no row); `PATCH /api/runs/{id}/winner`;
  `list_runs` hides un-picked quick runs.
- **Receipt:** `RECEIPT_VERSION` **8**; quick branch + dedicated quick MD/HTML; shared
  `_RECEIPT_STYLE` (full HTML byte-identical).
- **Web:** `Quick ⚡` mode in `RunSetup`; `ProofCockpit` Decide-branch on `mode`; `QuickCompare.tsx`
  head-to-head (neutral-ink bars, pick, save→`patchWinner`, promote).

## BACKLOG — non-blocking (operator picks)
1. **Quick-Compare promote carries the prompt** — "Promote to a full scored run" pre-fills a Models
   run with the same 2 candidates but NOT the ad-hoc prompt (by design; a quick prompt isn't a frozen
   dataset). Future enhancement if operators want the prompt seeded into a one-example set.
2. **Stored "Recommended on 0/5"** (carried over) — some 2026-06-21 stored full runs persisted
   `recommended:true` on a 0-pass candidate (pre-gate). New runs correct. Optional one-off backfill.
3. **Catalog price/source accuracy pass** — verify list prices + context windows (`current-docs-check`).
4. **Cross-product models×prompts** — N models × M prompts in one run. **Brainstorm FIRST.**
5. **DS-skin polish** — shared token-driven badge/chip/bar kit (`.of-tag`, `TONE_BAR`, strengthened
   `ProviderTag`, the new neutral objective bar are seeds); deepen per-figure mono; receipt
   proof-seal stamp.
6. **Richer sample data** — extend `sample_data.py` if onboarding wants it.
7. **Packaging · licensing · distribution** — LICENSE + source headers, PyPI metadata (dist
   `orionfold-proof`, CLI `orionfold`; reserve `orionfold` + `orionfold-arena`),
   `uv tool install orionfold-proof` → `orionfold up`, release notes / demo script. **Scope FIRST.**
8. **git remote + push** — **LAST item; do NOT surface or start until packaging (#7) is done**
   (operator directive). No remote configured; `main` holds all work unpushed.

_Done since last handoff: dead `pickLabel` removed (`aea1931`); keyless quick-compare demo fixed
(`0fe7c61`) — was the prior backlog #1._

## Key invariants to NOT regress
- **Quick-Compare (new):** `mode`/`chosen_winner` live on `ProofRun` (JSON report blob) ONLY and are
  **EXCLUDED from `config_hash`** (a quick run's hash is identical before/after a pick). The unscored
  rubric `{kind:"none"}` yields `ResultRow.score=None`/`passed=None`; `build_leaderboard` must stay
  `None`-safe (`r.score or 0.0`). Quick runs use an ephemeral `Dataset(id="quick-compare")` — **no
  dataset row written**. `list_runs` hides quick runs with `chosen_winner is None`. Quick receipts
  use objective columns + neutral-ink bars — **never `--color-accent` (interactive) or `--color-ok`
  (PASS)** for the bars; the pick selection legitimately uses the accent (interactive).
- **Receipts archive list (`ReceiptsView.tsx`):** the per-row summary winner is **mode-specific** —
  full runs read `leaderboard.recommended` ("Winner … % … Scored by"); quick runs read
  `run.chosen_winner` resolved against `run.candidates` ("Picked &lt;label&gt;" / "Tie — no clear
  winner"). Do NOT collapse quick runs onto the `recommended` path — nothing is ever recommended in an
  unscored run, so it would always show the wrong "No clear winner".
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
  them only when Sandbox is on. Scored mock matrix `config_hash 467ddd96c9a5` unchanged. **Quick-mode
  signal inside a mock = `example.expected_text == ""`** (the keyless ad-hoc prompt): `mock_good` then
  returns `_condense(input_text)` instead of the (empty) expected; `mock_bad` skips its 1-in-5 error.
  **Do NOT regress the scored path** — with a non-empty expected, `mock_good` still echoes it
  byte-identically and `mock_bad` still errors ~1/5 (the "always a failure case" guarantee).
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

The sequenced Datasets → Leaderboard → Quick-Compare arc is COMPLETE (all 3 sub-projects shipped) and
was fully E2E-verified in a browser last session — no verification debt. Decide the next backlog item
with the operator. BRAINSTORM scope FIRST for anything non-trivial.

RECENT WORK (committed to main; no git remote):
- (latest) KEYLESS QUICK-COMPARE DEMO FIX (0fe7c61, spec 9d9b577): quick mode has no expected answer,
  so the mock pair was degenerate — mock_good rendered blank, mock_bad could randomly error. Keyed on
  expected_text=="" : mock_good now condenses the prompt into a summary-shaped line (_condense), mock_bad
  never errors in quick mode. Scored/dataset path unchanged. TDD +4 backend tests; backend 275, ruff
  clean; browser-confirmed good-vs-bad reads clearly.
- RECEIPTS-LIST QUICK-PICK FIX (b06face) + dead-pickLabel removal (aea1931): the Receipts archive list
  showed "No clear winner" for picked quick-compare receipts (read leaderboard.recommended, always
  empty for unscored quick runs, instead of run.chosen_winner). Now "Picked <label>" / "Tie",
  mode-specific. Web 119 pass.
- QUICK-COMPARE → Proof Receipt (sub-project 3 of 3): 1-prompt × 2-candidate "Quick ⚡" mode reusing
  the matrix engine + exporter; unscored {kind:"none"}; head-to-head objective bars + human pick;
  saved as a quick-check Proof Receipt (ProofRun.mode + chosen_winner, RECEIPT_VERSION 8, excluded
  from config_hash) + promote CTA. Evidence: docs/worklog/2026-06-22-quick-compare.md.

BACKLOG (operator picks): quick-promote carries the prompt; stored recommended-on-0/5 backfill;
catalog price pass; cross-product models×prompts (BRAINSTORM); DS-skin polish; richer sample data;
packaging·licensing·distribution (BRAINSTORM); git remote + push — LAST, do NOT surface until
packaging is done (operator directive).

Do NOT regress invariants in HANDOFF.md (Quick-Compare mode/chosen_winner on ProofRun only + EXCLUDED
from config_hash / {kind:"none"} → None score+passed / build_leaderboard None-safe / ephemeral
quick-compare dataset writes no row / list_runs hides un-picked quick / quick receipt v8 + neutral-ink
bars never accent-or-ok / _RECEIPT_STYLE shared full HTML byte-identical; leaderboard $/quality on
LeaderboardEntry only never a ranking key; datasets metadata DB+API-only; append-only migrations next
index 6; mock bare-ids + config_hash 467ddd96c9a5; DS accent/status split; compareBy now
models|prompts|quick).
```
