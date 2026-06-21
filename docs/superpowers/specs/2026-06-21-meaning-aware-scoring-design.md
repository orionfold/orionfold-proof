# 2026-06-21 — Meaning-aware scoring (Finding 2: similarity-rubric weakness)

> Design spec. Brainstormed and approved 2026-06-21. The last of the three live-review
> findings from the decision-recipes run. Implementation: writing-plans next.

## Problem

The v0 default rubric is **string-similarity @ threshold 0.8** (`scoring/rubric.py`,
`difflib.SequenceMatcher` over normalized text). It measures *character-sequence overlap*,
not meaning. Live evidence: Haiku produced a factually complete Markdown table (revenue
$48.2M / 22% YoY / 118% NRR / 79% margin + drivers — arguably better than the terse expected
prose) and scored **0.12 / Fail**. The rubric rewards matching the expected text's
*phrasing and format*, not its meaning. For summarization this is too crude and produces
dishonest proof.

## Goal

Add **meaning-aware scoring** without losing two charter-protected invariants:

1. **Keyless determinism** — the full proof suite must run with zero API keys and stay
   reproducible/testable (`scoring/rubric.py` docstring; ADR-0001 §7).
2. **Keyless-mock default** — a fresh `orionfold up` with no keys must Just Work.

## Decisions (locked in brainstorming)

| Decision | Choice |
| --- | --- |
| Ambition | **Both** — a deterministic keypoint-coverage kind *and* an opt-in LLM judge. |
| Keypoint source | **Per-example authored** `keypoints: list[str]` on `Example`. |
| Default rubric | **Keypoint if any example has keypoints, else similarity.** Judge is never auto-selected. |
| Judge basis | The judge grades the candidate output's meaning **vs `expected_text`**, 0..1. |
| Sequencing | **One slice** covering keypoint + judge + UI. |
| Judge UI | **Full in-app judge picker** (scoring-method + judge-model selector, reusing the selection machinery). |

## Architecture

### 1. Rubric kinds

`RubricKind` extends additively — `similarity`/`exact`/`contains` are **unchanged**:

```
RubricKind = Literal["exact", "contains", "similarity", "keypoint", "judge"]
```

- **`keypoint`** (deterministic, keyless): fraction of authored required facts present in the
  output. New default when the dataset carries keypoints.
- **`judge`** (opt-in, needs a key): an LLM grades meaning vs `expected_text`. Deterministic
  `MockJudge` keeps tests/CI keyless.

### 2. Data-model changes (`domain/models.py`)

```python
class Example(BaseModel):
    input_text: str
    expected_text: str
    keypoints: list[str] = []           # authored required facts; [] = none

class Rubric(BaseModel):
    kind: RubricKind = "similarity"     # Pydantic default unchanged (back-compat)
    threshold: float = 0.8
    case_sensitive: bool = False
    judge_provider_id: str | None = None  # only used when kind == "judge"
    judge_model: str | None = None        # recorded in provenance
```

Both surfaces flow into `config_hash` for free — `keypoints` via the dataset dump, the judge
fields via `rubric.model_dump()`.

**Intentional `config_hash` change (NOT a regression).** Once these fields exist, every run's
dump gains `keypoints: []` / `judge_*: null`, so `config_hash` moves even for non-users.
Unlike Finding 1 (untouched provenance was the invariant), Finding 2 *intentionally* changes
the scoring contract, so the hash *should* move. Consequences: regenerate sample receipts;
re-pin any hash-pinned test.

### 3. Scoring (`scoring/rubric.py`)

`score(expected, output, rubric)` keeps its signature for the deterministic kinds. New logic:

- **keypoint**: `matched / total`, where a keypoint matches if its normalized text is a
  substring of the normalized output (reuse `normalize()` + `case_sensitive`). **Empty
  keypoints on a row → per-row fallback to `similarity`** (handles mixed datasets;
  deterministic, documented). Keypoints are authored as canonical literal tokens the output
  is expected to contain — **no fuzzy numeric parsing in v0** (YAGNI; documented limitation:
  author "$48.2M" as the token you expect, not "$48.2 million" hoping for a fuzzy match).

- **judge**: a small `Judge` seam so scoring stays testable:
  - `LLMJudge(provider, model)` — builds a fixed grading prompt (expected + output → "rate
    0..1 how well the output captures the meaning of the expected answer"), calls the judge
    provider through the registry at temperature 0, and parses one number robustly.
  - `MockJudge` — deterministic stand-in (e.g. difflib-derived) used for keyless/test runs so
    the suite stays keyless and a judge run is reproducible.
  - **Error path**: provider error or unparseable score → `row.error` set, `score = 0.0`,
    `passed = False`. This reuses Finding-1's error-vs-fail distinction so an unjudgeable /
    all-errored judge candidate ranks **last** and is never recommended.

### 4. Engine (`proof/engine.py`)

Judge makes scoring **networked** for the first time (today `score()` is pure stdlib). The
per-row path in `iter_matrix` gains a judge branch:

- Deterministic kinds (`exact`/`contains`/`similarity`/`keypoint`) → call `score()` as today.
- `kind == "judge"` → resolve the judge once per run via `get_provider(rubric.judge_provider_id)`
  and grade each non-errored row through the `Judge` seam. A candidate's own provider error
  still short-circuits to `score 0.0 / error` before the judge is consulted.

The judge runs **once per (candidate × example) cell** — N×M judge calls. Cost/latency of the
judge is **not** folded into the candidate's measured cost/latency (that would distort the
candidate's own numbers); v0 keeps judge cost out of the candidate columns and the receipt
states the judge model so the cost is attributable. (Surfacing aggregate judge cost is a
possible follow-up, not in scope.)

`run_proof` validates up front: `kind == "judge"` requires a resolvable `judge_provider_id` +
`judge_model`; if missing/unavailable → a clear error at run start (no silent fallback —
silent fallback would make provenance dishonest). The keyless default never selects judge.

### 5. Default selection

`default_rubric_for(dataset) -> Rubric`: `kind="keypoint"` if any example has keypoints, else
`"similarity"`. The Pydantic default stays `"similarity"` for back-compat. The **demo dataset
gets keypoints authored**, so the keyless demo shows meaning-aware scoring out of the box — the
reformatted-but-correct output that scored 0.12 now passes.

### 6. Provenance & receipt (`receipts/export.py`)

- **`RECEIPT_VERSION 4 → 5`** (one bump covers the whole slice).
- A calm **"Scored by"** line across cockpit + all 3 receipt formats:
  `Keypoint coverage` / `Similarity` / `LLM judge · <judge_model>`. Honest about *how* trust
  was measured.
- **The judge key never appears** in any receipt, log, or screenshot (security-secrets-review
  gate). `judge_provider_id`/`judge_model` are safe to show; the key is not.

### 7. Frontend — full in-app judge picker

A small **Scoring method** section in the cockpit run config:

- Method selector: Auto (default-selection) · Keypoint · Similarity · LLM judge.
- When **LLM judge** is chosen: a judge-model picker that **reuses the existing selection
  machinery** — `/api/catalog` ∩ availability + `KeyEntry` — so only available providers/models
  are offered and a greyed cloud judge unlocks in place exactly like a candidate (composes with
  #4 picker + #5 recipes; no second model-picker invented).
- The selected method + judge model render in the "Scored by" line in the cockpit and receipts.

### 8. API

- The run-config endpoints carry the rubric (`kind`, `threshold`, `judge_provider_id`,
  `judge_model`). Validation: judge kind without a resolvable judge model → 422 (reuse the
  global input-stripping handler; never echo a key).
- No new secret surface: `/api/credentials` is the only key-write path and is unchanged; the
  judge model selection reuses `/api/selection` + `/api/catalog` (leak no secrets).

## Error handling summary

| Situation | Behavior |
| --- | --- |
| Candidate provider errors | `score 0.0`, `error` set (unchanged) — judge not consulted for that row. |
| keypoint kind, empty keypoints on a row | per-row fallback to `similarity` (deterministic). |
| judge provider error / unparseable score | `score 0.0`, `passed False`, `row.error` set → ranks like a fail-to-error (last). |
| judge kind, no resolvable judge model | clear error at run start (422 / validation), no silent fallback. |

## Testing

- **Unit (`scoring`)**: keypoint full/partial/zero coverage, empty-keypoints→similarity
  fallback, case-sensitivity, normalization; `default_rubric_for` selection; judge parse
  (valid/garbage), `MockJudge` determinism, judge error path; `config_hash` moves with the
  new fields.
- **Engine**: a keyless keypoint run is deterministic and produces the expected pass/fail; a
  judge run via `MockJudge` is deterministic; judge-without-model raises at run start.
- **Receipt**: `RECEIPT_VERSION == 5`; the "Scored by" line renders per kind in MD/HTML/JSON;
  no secrets (`receipt-quality-review` + `security-secrets-review`).
- **Frontend (Vitest)**: scoring-method selector renders; judge selection surfaces the judge
  model; "Scored by" displays per kind.
- **e2e (Playwright)**: the keyless proof the fix works — on the keypointed demo dataset a
  reformatted-but-correct output now **passes** where similarity failed; the cockpit shows
  "Scored by: Keypoint coverage".

## Non-regressions to hold

- Finding-1 invariants: leaderboard never recommends a 0-pass/all-errored candidate; calm
  NEUTRAL no-winner state; errored rows say "errored, no output". A judge error is an
  *error*, not a low-scoring fail.
- `similarity`/`exact`/`contains` scoring is byte-for-byte unchanged.
- Keyless mock default still Just Works (default selection never picks judge; `MockJudge`
  keeps the suite keyless).
- Tailwind v4 CSS-var parenthesis shorthand in any new UI.
- Test-contract strings preserved; `RECEIPT_VERSION` lands at exactly 5.

## Out of scope (YAGNI)

- Fuzzy/numeric keypoint matching (author canonical tokens instead).
- Folding judge cost/latency into candidate columns (judge model is named for attribution).
- Multi-judge panels / judge ensembles. Per-criterion rubric weights.
- Auto-extracting keypoints from `expected_text`.
```
