# Design — Prompt-aware mocks (keyless prompt-compare gets a real signal)

- **Date:** 2026-06-21
- **Status:** Approved (operator-approved, brainstorm)
- **Scope:** `src/orionfold/providers/mock.py` + tests. No UI, no receipt schema change, no
  `RECEIPT_VERSION` bump, no new dependency.
- **Builds on:** #6 prompt-variant candidates (`system_prompt` is a field on `Candidate`).

## Problem

In keyless prompt-compare (`Compare by: Prompts` on a mock model), `mock_good`/`mock_bad`
ignore `candidate.system_prompt`, so every prompt variant returns identical output → identical
scores → no winner. The plumbing demonstrably works (one leaderboard row per variant, receipt
records each prompt), but the demo has **no decision signal**: the operator cannot see *which
wording wins* without configuring a real model + key.

## Goal

Make the mocks deterministically vary their output with the system prompt, so the keyless
Baseline-vs-Concise starter demo produces an **intuitive, explainable winner** — while keeping
the model-compare path (system_prompt is None) **byte-identical** to today.

## Non-goals

- No randomness / hash-driven quality (an arbitrary winner undercuts the "defensible proof"
  thesis). Rejected approach B.
- No new comparison axis, no cross-product, no UI change, no receipt schema change.
- The mocks do not become a faithful model emulator — this is a deliberately small *simulation*
  of prompt-sensitivity, clearly labeled "Mock ·…", to give the no-keys demo a signal.

## Approach — cue-driven output shaping

A single pure helper shapes whatever base output a mock would otherwise return. The base output
is unchanged: `expected_text` for `mock_good`, `_GENERIC_ANSWER` for `mock_bad`.

```python
output = _shape_for_prompt(base, candidate.system_prompt)
```

`_shape_for_prompt(base: str, system_prompt: str | None) -> str`:

1. **`system_prompt is None` → return `base` verbatim.** This is the model-compare path; it must
   stay byte-identical (preserves the "100% (5/5)" contract, the sample receipts, and
   `config_hash 467ddd96c9a5`).
2. Compute a **verbosity budget** `b ∈ (0, 1]` from concise cues (case-insensitive substring
   match against the prompt), graded in two tiers:
   - **strong** (`b = 0.4`): `"as few words as possible"`, `"fewest"`, `"terse"`,
     `"one sentence"`, `"tl;dr"`
   - **mild** (`b = 0.6`): `"concise"`, `"brief"`, `"short"`, `"minimal"`
   - **no cue** → `b = 1.0`
   When both a strong and a mild cue are present, the **strongest (smallest b)** wins.
3. **`b >= 1.0` → return `base` verbatim** (an unrecognized prompt does not perturb the output —
   honest: no recognized instruction, no change).
4. Otherwise truncate to the first `max(1, ceil(b * word_count))` whitespace-split words and
   re-join with single spaces. Truncation drops trailing content → lower keypoint coverage *and*
   lower similarity ratio, so the signal is **rubric-agnostic** (works for keypoint and
   similarity datasets alike).

### Determinism & invariants

- Pure function of `(base, system_prompt)` — no hashing, no `Date`/`random`, no process state.
- Latency stays keyed on `input_text` (`_stable_int`); unchanged.
- `mock_bad` still raises its simulated failure on `_stable_int(input_text) % 5 == 0` *before*
  shaping → "Failure cases (5)" / "simulated provider failure" contracts intact.
- Verbatim guarantee: steps 1 and 3 return the original string object untouched (no
  split/re-join), so whitespace in `expected_text` is never normalized on the unshaped paths.

### Resulting default demo (mock_good, keypoint scoring)

`investment_memo_summarization` ex0 — expected: *"Revenue grew 22% to $48.2M on enterprise
expansion, with 118% net retention and margins improving to 79%."* (keypoints `22%`, `$48.2M`,
`118%`, `79%`).

- **Baseline** (full task instruction, no concise cue) → `b = 1.0` → full text → **100%**.
- **Concise** (`"Answer in as few words as possible…"`) → strong cue → `b = 0.4` → first ~7 of 17
  words ≈ *"Revenue grew 22% to $48.2M on enterprise"* → keypoints `22%`, `$48.2M` present ≈
  **~50%**.

Baseline wins; the result reads as "the concise prompt dropped key figures." Deterministic, no
keys.

## Testing

Unit (`tests/unit/test_mock*.py` — extend or add):
- `system_prompt is None` → `mock_good` returns `expected_text` verbatim (regression lock for the
  byte-identical model-compare path).
- A non-cue `system_prompt` → returns `base` verbatim (arbitrary prompts don't perturb).
- A strong concise cue → truncated output, strictly shorter, with strictly fewer keypoints than
  the full output on the demo example.
- A mild cue truncates less aggressively than a strong cue (`b=0.6` keeps more than `b=0.4`).
- Determinism: same `(example, system_prompt)` → identical output across repeated calls.
- `mock_bad` still raises on the failing-subset inputs regardless of `system_prompt`.

Integration (`tests/integration/test_proof_api.py`):
- A prompt-compare run on `mock_good` with Baseline vs Concise yields **different** leaderboard
  scores, Baseline strictly greater than Concise. (The existing
  `test_prompt_variant_run_produces_one_entry_per_variant` stays green: it asserts ids/labels,
  not scores.)

## Verification

`uv run pytest` · `uv run ruff check src tests` · `pnpm --dir web test` · `pnpm --dir web build`
· rebuild embed + `pnpm --dir web e2e` (the keyless prompt-compare e2e asserts labels + receipt
count, not scores → stays green) · confirm sample `config_hash` is still `467ddd96c9a5` (no
receipt regeneration needed; model-compare output is byte-identical). Real browser check of the
keyless prompt-compare run showing Baseline > Concise on the leaderboard.

## Risks

- **Cue vocabulary is finite.** A concise instruction phrased outside the cue list falls to
  `b=1.0` (no change). Acceptable: the starter demo uses recognized phrasing, and the helper is
  one obvious place to extend. Documented as a known limit.
- **Whitespace normalization on the truncated tail** (re-join with single spaces). Only the
  shaped/truncated variant is affected; verbatim paths are untouched. Cosmetic and demo-only.
