# 2026-06-22 — Quick-Compare → Proof Receipt (sub-project 3 of 3)

Design spec. Third and final of the three sequenced sub-projects scoped from the Orionfold brand /
Arena research (**Datasets → Leaderboard → Quick-Compare**). A thin Arena-`CompareDuel` clone: a
**1-prompt × 2-candidate** head-to-head "Quick Compare" entry mode that reuses the existing matrix
run engine and receipt exporter, ends in a human **pick-a-winner**, and saves a clearly-labeled
single-example **quick check** Proof Receipt with a CTA to promote to a full scored run.

## Thesis

The product exists to help the operator **decide what AI to trust**. The full Proof Run is the
rigorous path — a frozen dataset, a rubric, scored standings. But the first instinct when comparing
two models on a real task is often faster and more visceral: *"give them both the same prompt, let
me read the two answers, and let me pick."* Quick-Compare is that low-friction on-ramp. It is
**not** a replacement for scored proof — it is the fast door that leads to it. Every quick check is
honestly labeled as a single-example, un-scored, human-judged check, and every quick check offers a
one-click **promote to a full scored run**.

## Decisions (operator, 2026-06-22)

1. **Judging = human pick + objective bars.** No expected answer, no rubric scoring. Both candidates
   generate on one shared prompt; the head-to-head shows the two outputs plus **objective** bars
   (latency / cost / tokens). The operator clicks the winner (**A / B / tie**); that pick is the
   recorded winner. Closest to Arena's `CompareDuel`.
2. **Entry point = third mode on the Proof Run page.** `Compare by: Models | Prompts | Quick ⚡`.
   Reuses the existing page, `StageStepper` (Configure → Run → Decide), and candidate pickers. No
   new nav item, no new route.
3. **Saved receipt = same schema + a quick mode flag.** Reuse the one `ProofReport` +
   Markdown/HTML/JSON exporter. Add `mode: "full" | "quick"` and `chosen_winner` to the report.
   **`RECEIPT_VERSION` 7 → 8** (additive). A quick receipt renders objective columns only,
   pass-rate/score as "—", winner = the human pick (★), no failure-cases section, a visible
   "single-example quick check — not scored proof" banner, and a "Promote to a full scored run" note.

### Implementation forks (operator-approved recommendations)

- **Fork A — unscored generation.** Add an unscored rubric kind `{kind: "none"}`. `iter_matrix`
  skips scoring for it (`score=None`, `passed=None`) — honest *absence* of a score, not a
  meaningless similarity-against-empty number written into a protected artifact.
- **Fork B — pick persistence.** Quick generation persists immediately
  (`mode:"quick"`, `chosen_winner:null`) and returns a `run_id`; a tiny
  `PATCH /api/runs/{id}/winner` records the pick. Reuses `save_report`/`get_report`. The Receipts
  list filters quick runs to those **with** a `chosen_winner`, so abandoned generations don't clutter.

**Kept:** the **tie** option (operator approved the design as presented, which included it). A tie is
a legitimate, honest outcome of an eyeballed check and is recorded as `chosen_winner: "tie"`.

**Deferred (explicitly out of this slice):** the free-form chat lane; live token streaming of output
as it generates; quick-compare across more than 2 candidates; quick-compare over more than 1 prompt.

## Current state (grounding)

- **Run engine is already dataset-*object*-shaped.** `run_proof(*, run_id, created_at, brief,
  dataset, candidates, rubric)` (`src/orionfold/proof/engine.py` ~133-156) and
  `iter_matrix(dataset, candidates, rubric)` (~65-114) take a `Dataset` *object*, not an id. The
  only thing forcing a stored dataset is the **route layer**: `create_run` /`create_run_stream`
  call `get_dataset(conn, body.dataset_id)` (`src/orionfold/server/routes.py` ~381, ~463) and 404
  if absent. Inline examples therefore need a route branch, **not** an engine change.
- **`RunRequest`** (`routes.py` ~90-96): `dataset_id: str` (mandatory), `candidate_ids`, `rubric`,
  `brief`, `prompt_variants`. No `examples`, no `mode`.
- **`Rubric`** (`src/orionfold/domain/models.py`): `kind: "similarity" | "keypoint" | "exact"`,
  `threshold`, `case_sensitive`, judge fields. No unscored kind.
- **`ResultRow`** (engine): carries per-cell output + score + passed. **`build_leaderboard`**
  (`src/orionfold/proof/leaderboard.py` ~17-75) ranks by
  `(_all_errored, -pass_rate, -avg_score, avg_latency_ms, total_estimated_cost_usd)`; sets
  `recommended=True` on `entries[0]` only if `pass_count > 0`.
- **Receipt:** `src/orionfold/receipts/export.py`, `RECEIPT_VERSION = 7`. `build_receipt(report)`
  (~105-156) is the single canonical structure; `to_json/to_markdown/to_html` render from it. MD and
  HTML leaderboard tables have **hardcoded headers + row templates** (edit both strings to change
  columns). Failure-cases section is rendered unconditionally from `report.failure_cases`.
- **Persistence:** `save_report(conn, report, *, is_sample=False)`
  (`src/orionfold/storage/repository.py` ~97-109) stores `report.model_dump_json()` as a blob in the
  `runs` table keyed by `report.run.id`; `get_report(conn, run_id)` round-trips via
  `ProofReport.model_validate_json`. **No new column / migration needed** — `mode` + `chosen_winner`
  live inside the JSON report blob.
- **Frontend run host:** `web/src/features/proof/ProofCockpit.tsx` owns all run state
  (`datasetId`, `selected`, `brief`, `rubric`, `compareBy: "models" | "prompts"`, `promptVariants`,
  `promptModel`, `progress`, `openFailure`); computes stage (`configure → run → decide`); fires
  `createRunStream` with a `RunRequest`.
- **Setup form:** `web/src/features/proof/RunSetup.tsx` — the "Compare by" toggle (~103-122) and a
  `recipes` slot (~143). `web/src/features/proof/Leaderboard.tsx` renders the standings table;
  `leaderboardFormat.ts` holds the pure helpers (`passRateTone`, `formatCostPerQuality`, `medalFor`);
  `badges.tsx` `ProviderTag` renders provider/privacy tags.

## Components

### Backend

1. **`Rubric` — unscored kind.** Add `"none"` to `kind`. In `iter_matrix`, when `rubric.kind ==
   "none"`, skip the scorer: the cell's `score`/`passed` are `None`. `ResultRow.score` and
   `.passed` must already be (or become) `float | None` / `bool | None` to carry the absence.
2. **`RunRequest` — inline + mode.** Add `examples: list[Example] | None = None` and
   `mode: Literal["full", "quick"] = "full"`.
3. **Route branch (`create_run` + `create_run_stream`).** If `body.examples` is provided, build an
   ephemeral `Dataset(id="quick-compare", name="Quick Compare", examples=body.examples)` instead of
   `get_dataset`. The `ProofRun` stores `dataset_id="quick-compare"`, `dataset_name="Quick Compare"`
   — honest provenance. Persist as normal (`save_report`).
4. **`ProofRun` / `ProofReport` — mode + pick.** Add `mode: Literal["full","quick"] = "full"` and
   `chosen_winner: str | None = None` (a `candidate_id`, the literal `"tie"`, or `null`).
   **`chosen_winner` and `mode` are provenance/presentation only and are EXCLUDED from
   `config_hash`** so repro hashing is unchanged (config_hash continues to hash brief + candidates +
   rubric + dataset identity only).
5. **`build_leaderboard` — quick branch.** When results are unscored (quick), do **not** rank by
   score. Preserve **candidate selection order** (A then B). `recommended` is **not** set from
   `pass_count`; the winner is conveyed by `report.chosen_winner`, not the leaderboard. (Quick
   `LeaderboardEntry` rows still carry latency/cost/tokens; `pass_rate`/`avg_score` are `None`.)
6. **`PATCH /api/runs/{id}/winner`.** Body `{chosen_winner: str}`. Validates the run exists, is
   `mode=="quick"`, and `chosen_winner` ∈ the run's candidate ids ∪ `{"tie"}`. Sets
   `report.run.chosen_winner`, re-saves via `save_report`, returns the updated `ProofReport`.
7. **`RECEIPT_VERSION 7 → 8` + `build_receipt` quick branch.** When `report.run.mode == "quick"`:
   - leaderboard table: objective columns only (**Candidate · Provider · Privacy · Latency · Cost ·
     Tokens**); score/pass-rate columns omitted (or "—"); the `chosen_winner` row gets a ★ "picked"
     marker.
   - verdict line: `Picked: <label> (<provider>) — your pick` (or `Tie — no clear winner`).
   - **no** failure-cases section.
   - a banner: `QUICK CHECK · 1 example · not scored proof`.
   - a note: `Promote to a full scored run for repeatable proof.`
   - MD + HTML get a quick-mode template path; JSON serializes `mode` + `chosen_winner` automatically.
8. **Receipts list filter.** The runs/receipts listing excludes `mode=="quick"` runs whose
   `chosen_winner is None` (abandoned generations).

### Frontend

9. **`ProofCockpit` — quick state + branch.** `compareBy` gains `"quick"`. New state: `quickPrompt:
   string`, `quickPick: string | null`. When `compareBy === "quick"`, the run mutation builds a
   `RunRequest` with `examples: [{ input_text: quickPrompt, expected_text: "" }]`,
   `candidate_ids: [A, B]`, `rubric: { kind: "none" }`, `mode: "quick"`, and the existing `brief`
   (task name carried, decision question optional). Fires the **same** `createRunStream`.
10. **`RunSetup` — third toggle + quick lane.** Add a `Quick ⚡` button to the Compare-by group.
    When active, replace the dataset selector + `CandidatePicker`/`PromptVariants` block with a
    minimal lane: a **prompt textarea** + **two candidate slots** (reusing the candidate picker,
    capped at exactly 2). `canRun` (quick) = prompt non-empty **and** exactly 2 candidates selected.
11. **`QuickCompare.tsx` (Decide view).** Replaces the leaderboard/failure view when `mode==="quick"`:
    two output cards side-by-side; **objective bars** (latency / cost / tokens, each normalized
    across the 2 rows); a `[A wins] [B wins] [tie]` control bound to `quickPick`; **"Save as Proof
    Receipt"** enabled only once a pick is made → fires `PATCH …/winner`; a **"Promote to a full
    scored run"** link that pre-fills a normal Models run with the same 2 candidates + the prompt as
    a starting note.
12. **Formatters.** Extend `leaderboardFormat.ts` (or a sibling `quickCompareFormat.ts`) with a pure
    objective-bar scaler (normalize latency/cost/tokens across two rows → 0..1 widths) and a
    pick-label helper. Bars use **status/neutral tokens, never `--color-accent`**.
13. **`api.ts` schema.** `RunRequest` gains `examples?`, `mode?`; `Rubric.kind` gains `"none"`;
    `ProofRun`/report schema gains `mode`, `chosen_winner` (`.optional()` for pre-v8 receipts); add a
    `patchWinner(runId, chosen_winner)` client call.

## Data flow

```
Proof Run › Compare by [Quick ⚡]
  → prompt textarea + pick exactly 2 candidates (A, B)
  → POST /api/runs/stream { examples:[{input_text:<prompt>, expected_text:""}],
                            candidate_ids:[A,B], rubric:{kind:"none"},
                            mode:"quick", brief }
  → engine generates A & B (latency/cost/tokens captured, NOT scored)
  → save_report (mode:"quick", chosen_winner:null) → returns run_id
  → Decide: QuickCompare — two output cards + objective bars + [A wins][B wins][tie]
  → pick → PATCH /api/runs/{run_id}/winner { chosen_winner }
  → "Save as Proof Receipt" → receipt (MD/HTML/JSON): QUICK CHECK banner, picked ★, promote note
```

## Error handling

- **Provider error on a candidate** → its output card surfaces `ProviderResult.error` (existing
  pattern); the other side still renders; the operator can still pick (typically the working side)
  or tie. A run where **both** error still saves (honest record) but the head-to-head shows two error
  cards and the pick control is disabled with a hint to rerun.
- **Quick `canRun` guards** → empty prompt or ≠2 candidates disables Run with an inline hint.
- **PATCH winner validation** → unknown id / non-quick run / id not in candidates → 400; the UI
  surfaces a toast and leaves the pick unsaved.

## Testing

- **Backend (pytest):**
  - `kind:"none"` → `iter_matrix` yields `score is None`, `passed is None`; no scorer invoked.
  - inline `examples` run builds an ephemeral `Dataset(id="quick-compare")`, persists, **writes no
    dataset row**.
  - quick `ProofReport` has `mode=="quick"`, `chosen_winner is None` at generation.
  - `PATCH …/winner` sets the pick, re-saves, round-trips; rejects unknown id / non-quick run / bad
    winner (400).
  - `build_leaderboard` quick branch preserves selection order, sets no score-based `recommended`.
  - receipt is **v8**, quick branch: objective columns, no failure section, banner + promote note,
    `chosen_winner` serialized; **`config_hash` excludes `mode`/`chosen_winner`** (same hash with and
    without a pick set).
- **Frontend (Vitest):** quick-mode `canRun` gating; objective-bar scaler (two-row normalization,
  zero-cost / zero-latency edge); pick interaction enables Save; promote-CTA pre-fill mapping.
- **e2e (Playwright, mock candidates, keyless):** `Compare by Quick → enter prompt → pick mock_good
  & mock_bad → Run → pick A → Save → receipt preview shows "QUICK CHECK" + picked ★ + promote note`.

## Invariants preserved

- **`config_hash` algorithm untouched**; `mode` + `chosen_winner` are excluded from it (a quick run's
  hash is identical before and after a pick).
- **No migration** — `mode`/`chosen_winner` live inside the JSON report blob; migrations stay
  append-only (next index unchanged at 6).
- **Accent/status split** — objective bars use status/neutral tokens, **never `--color-accent`**;
  green `--color-ok` stays reserved for PASS (a quick check has no PASS, so no green).
- **Mock bare-ids + deterministic path** keep the e2e keyless; `config_hash 467ddd96c9a5` for the
  existing mock matrix is unaffected (quick runs use a different dataset identity).
- **Receipt is the protected artifact** — quick receipts are clearly demarcated as un-scored quick
  checks; they never claim scored proof, and they always offer promotion to a full run.
