# 2026-06-20 — Leaderboard recommendation fix (Finding 1 + Finding 3)

Design spec. Addresses the highest-priority live-review finding: the leaderboard recommends a
candidate that produced **nothing**. Bundles the small catalog cleanup (Finding 3) that made the
bug surface. Finding 2 (similarity rubric) is **out of scope** — its own brainstorm.

## Problem

`src/orionfold/proof/leaderboard.py:48-50`:

```python
entries.sort(key=lambda e: (-e.pass_rate, e.avg_latency_ms, e.total_estimated_cost_usd))
if entries:
    entries[0].recommended = True
```

Two compounding defects:

1. **The tiebreak rewards errors.** A candidate that errors across the provider boundary reports
   `0 ms / $0.00` (graceful `ProviderResult` with no output). At a 0%-pass tie the tiebreak is
   lowest latency then lowest cost, so an errored candidate *wins because it failed fastest and
   cheapest*.
2. **`recommended` is set unconditionally** — even when the top candidate passed 0/5. The product
   crowns a "winner" that produced nothing, defeating the "what to trust" thesis.

Verified twice live (2026-06-20): _Cost vs quality_ crowned `claude-fable-5` (0/5, errored — not
available on the account) over `claude-haiku-4-5` (ran, avg 0.05); _Cheapest that passes_ crowned
`ollama:llama3.2` (0/5, HTTP 404 "model not found"). The frontend faithfully amplifies it:
`DecisionSummary` and `ReceiptsView` both compute `find(recommended) ?? leaderboard[0]`, so even the
fallback badges a loser.

`ResultRow.error` already distinguishes an errored cell (no output) from a low-scoring one, so the
fix can rank errored candidates last using data already captured.

## Decisions (operator, 2026-06-20)

- **Ranking rule:** explicit error-last signal — add `error_count`, rank a fully-errored candidate
  strictly last, *before* the score/latency/cost tiebreaks. Closes the residual 0.00-vs-error tie
  hole. Adds a receipt schema field → bump `RECEIPT_VERSION` 3 → 4.
- **No-winner state:** verdict `"No clear winner"` with a one-line reason, standings still shown
  (least-bad first, errored last), no badge; errored candidates marked "errored, no output".
- **Scope:** bundle Finding 3 (remove `claude-fable-5` from `catalog.json`) into this slice — one
  sample-receipt regen; the cost-vs-quality "Frontier" arm resolves to `claude-opus-4-8`.

## Components

### 1. Ranking + recommend gate — `proof/leaderboard.py`, `domain/models.py`

- **`LeaderboardEntry.error_count: int`** (new field) = `sum(1 for r in rows if r.error is not None)`.
- **`all_errored`** (derived in the sort, not stored) = `total > 0 and error_count == total`.
- **Sort key:** `(all_errored, -pass_rate, -avg_score, avg_latency_ms, total_estimated_cost_usd)`.
  `False` (ran) sorts before `True` (all errored). Any real output beats a fully-errored candidate
  even at a 0.00 score tie; quality (`avg_score`) breaks pass-rate ties before latency/cost.
- **Recommend gate:** `if entries and entries[0].pass_count > 0: entries[0].recommended = True`.
  Otherwise **no** entry is marked recommended.
- Docstring updated to state the new ordering and the gate.

### 2. Receipt — `receipts/export.py`

- **`RECEIPT_VERSION = 4`** (a new leaderboard field is a schema change; `.claude/rules/receipts.md`
  mandates the bump). Update the version comment.
- `has_winner = top is not None and top.pass_count > 0`.
- `verdict = _verdict(top) if has_winner else "No clear winner"`.
- `recommendation = _recommendation_line(top) if has_winner else`
  `f"No candidate passed the rubric (threshold {run.rubric.threshold:.2f})."`
- Markdown/HTML already gate the ⭐ marker on `e["recommended"]`, so no star appears when nothing is
  recommended — no change needed there. Add an **"errored, no output"** annotation to leaderboard
  rows where `error_count == total` (small helper used by both MD and HTML renderers).
- `_verdict`/`_recommendation_line` signatures unchanged; the no-winner branch is handled by the
  caller (`build_receipt`), keeping those helpers about a real `top` only.

### 3. Frontend — `lib/api.ts`, `ProofCockpit.tsx`, `ReceiptsView.tsx`, `Leaderboard.tsx`

- **`api.ts`:** add `error_count: z.number()` to the `LeaderboardEntry` schema (and the TS type if
  declared separately).
- **`DecisionSummary` (`ProofCockpit.tsx`) and the winner lookup in `ReceiptsView.tsx`:** replace
  `find((e) => e.recommended) ?? leaderboard[0]` with `find((e) => e.recommended) ?? null`. On
  `null`, render a **calm, neutral (non-accent)** card: heading "No clear winner", body "No candidate
  passed the rubric." The standings table (`Leaderboard.tsx`) still renders below unchanged.
- **`Leaderboard.tsx`:** rows where `error_count === total` show an "errored, no output" annotation
  next to the pass-rate cell (so the least-bad-first ordering is legible).

### 4. Finding 3 — catalog — `catalog/catalog.json`

- Remove the `claude-fable-5` entry.
- Set `"latest": true` on `claude-opus-4-8` so a `pick=latest` Frontier resolver lands on the real
  frontier model. Verify the cost-vs-quality recipe's Frontier arm now resolves to
  `claude-opus-4-8` (live `GET /api/recipes` check after a server restart).
- `default_model_for("anthropic")` stays `claude-haiku-4-5` (unaffected) — the `test_catalog.py`
  drift-guard remains green. No change to provider `DEFAULT_MODEL`s.

### 5. Tests + samples

- **TDD unit (`tests/unit/test_leaderboard.py`, new or extend):**
  - An all-errored candidate (0/5, `error_count == total`) ranks **below** a candidate that ran but
    scored low (0/5, real output) — synthetic `ResultRow`s, keyless.
  - No entry is `recommended` when the top candidate has `pass_count == 0`.
  - The top candidate **is** `recommended` when it passes ≥ 1.
  - `error_count` is computed correctly (mix of errored + real rows).
- **TDD unit (`receipts` test):** `build_receipt` yields `verdict == "No clear winner"` and the
  threshold-bearing recommendation line when no candidate passed; `receipt_version == 4`.
- **Vitest:** a no-winner fixture (all entries `recommended: false`, `pass_count: 0`) → `DecisionSummary`
  renders the calm no-winner card and **no** "Recommended" badge.
- **Samples:** `uv run python scripts/gen_samples.py` once. The bundled sample keeps its real winner
  (`mock_good` 5/5); the diff is the new `error_count` field (+ `mock_bad`'s non-zero count from its
  ~1-in-5 deterministic errors) and `receipt_version` 4.
- **`receipt-quality-review`:** generate an ad-hoc all-fail receipt (e.g. a rubric threshold of 1.0
  or two failing candidates) to eyeball the no-winner Markdown/HTML/JSON copy; confirm no secrets,
  clear "no winner" messaging. Committing that extra sample is optional.

## Test contract (must not regress)

Existing happy-path strings stay green because the bundled sample keeps `mock_good` 5/5:
`"100% (5/5)"`, `"Failure cases (5)"`, `"simulated provider failure"`, heading "Orionfold Proof",
button `/Run proof/`, regions Leaderboard / Failure cases / Proof Receipt export,
"Export Markdown|HTML|JSON". The verdict vocabulary gains `"No clear winner"` for the new state.

## Out of scope / invariants held

- **Finding 2** (similarity rubric / LLM-as-judge) — separate brainstorm.
- **Provenance untouched:** no change to `config_hash`, `run.*`, `proof/engine.py`, or the provider
  boundary. The only schema change is the additive `error_count` field, reflected by the
  `RECEIPT_VERSION` bump.
- Keyless mock default unchanged; mocks stay bare-id. Tailwind v4 CSS-var shorthand `bg-(--color-x)`.
- No secrets in receipts/UI/logs (unchanged surfaces).

## Files touched

- `src/orionfold/domain/models.py` — `error_count` field.
- `src/orionfold/proof/leaderboard.py` — sort key + recommend gate + docstring.
- `src/orionfold/receipts/export.py` — `RECEIPT_VERSION` 4, no-winner verdict/recommendation,
  errored-row annotation.
- `src/orionfold/catalog/catalog.json` — remove `claude-fable-5`, flag `claude-opus-4-8` latest.
- `web/src/lib/api.ts` — `error_count` in schema.
- `web/src/features/proof/ProofCockpit.tsx` — `DecisionSummary` no-winner card.
- `web/src/features/proof/ReceiptsView.tsx` — winner lookup → null-safe.
- `web/src/features/proof/Leaderboard.tsx` — errored-row annotation.
- `web/src/test/fixtures.ts` (+ a no-winner fixture) and the relevant `*.test.tsx`.
- `tests/unit/test_leaderboard.py` (new/extended), receipts test, `samples/receipts/*` (regen).
