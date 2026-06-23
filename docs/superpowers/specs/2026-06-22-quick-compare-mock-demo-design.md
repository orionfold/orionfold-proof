# Design — keyless Quick-Compare reads as a clear good-vs-bad

- **Date:** 2026-06-22
- **Status:** Approved (operator, 2026-06-22)
- **Scope:** `src/orionfold/providers/mock.py` only. Doubles as the implementation plan
  (test list + steps below) — a one-file change does not warrant a separate plan doc.

## Problem

In **Quick-Compare** mode the operator pastes one ad-hoc prompt; there is no expected
answer, so the ephemeral example is sent as `{input_text: <prompt>, expected_text: ""}`
(`web/.../ProofCockpit.tsx:213`). The keyless mock pair then makes a **degenerate**
head-to-head:

- `MockGoodProvider` returns `_shape_for_prompt(example.expected_text, …)` (`mock.py:66`)
  → an **empty string** → the head-to-head card and receipt render a blank "—".
- `MockBadProvider` returns its fixed generic line **and** deterministically errors on
  ~1-in-5 inputs (`_stable_int(input) % 5 == 0`, `mock.py:88`) → in a single-example
  quick check that is a ~20% chance the "bad" side simply errors.

Net: a first-time, keyless user sees `good` blank and `bad` showing text (or an error),
and would paradoxically pick "bad". This undercuts Quick-Compare's "eyeball the outputs
and pick a winner" promise on the no-API-key onboarding path.

This is a **demo/UX gap, not a correctness bug** — the mocks were designed for the scored
dataset path (`mock_good` echoes the expected answer), an assumption that does not hold
when there is no expected answer.

## Decision

Make the **keyless** quick head-to-head read as a clear good-vs-bad, entirely within the
mock providers. No provider-interface change; the engine, API, and receipt format are
untouched (they render whatever output the mock produced).

**The "quick mode" signal, inside a mock, is `example.expected_text == ""`.** The quick
path sends empty expected; every dataset/bundled example has a real expected. Keying off
empty-expected keeps the change self-contained — no `mode` flag threaded through the
provider boundary.

### `mock_good`

- `base = expected_text or _condense(input_text)`, then the existing
  `_shape_for_prompt(base, system_prompt)` wrapper (dataset path stays byte-identical;
  concise cues still apply to the condensed base).
- `_condense(text)`: deterministic, on-topic, summary-shaped:
  1. Strip a leading **instruction clause** — content before the first `:` when that lead
     is short (≤ ~60 chars) and there is substantive content after it (handles
     "Summarize this for a client memo: …"). Otherwise keep the whole text.
  2. Take the leading content up to the first sentence terminator (`.`/`!`/`?`) **or** a
     ~28-word budget, whichever comes first; trim at a word boundary. Append `…` only if
     truncated mid-content.
  3. Fall back to the stripped input if the result is empty (defensive — the UI requires a
     non-empty prompt to run).

### `mock_bad`

- Skip the `_stable_int(input) % 5 == 0` error **when `expected_text == ""`** (quick mode);
  always return the generic line there. Otherwise unchanged — still errors ~1-in-5 on
  dataset runs, keeping the error path + a real failure case for the scored leaderboard.

## Tests (TDD — all in the empty-expected branch)

1. `mock_good` on an empty-expected example → non-blank, on-topic condensed output
   (contains salient input tokens, excludes the stripped instruction prefix); deterministic
   across repeated calls.
2. `_condense` strips a leading "instruction:" clause.
3. `_condense` caps a long input to the word budget and trims at a word boundary.
4. `mock_bad` on an empty-expected example → **never errors** (incl. an input that *would*
   error in dataset mode) and returns the generic line.
5. Regression guard: `mock_good` still returns `expected_text` verbatim on a dataset
   (non-empty expected) example.
6. Regression guard: `mock_bad` still errors on the known erroring dataset input.

Existing `tests/unit/test_providers.py` cases use non-empty expected text and stay green.

## Verification

- Backend `uv run pytest` (all green; new cases added).
- Browser: keyless quick head-to-head shows `good` with a real-looking condensed summary
  and `bad` with the generic line (no error); screenshot.

## Known trade-off

A *dataset* example authored with a genuinely empty expected would now get condensed-input
output from `mock_good` and no error from `mock_bad`. Acceptable — that is a degenerate,
unscoreable example, and the mocks are demo fixtures.

## Out of scope

- Real providers (already produce real outputs).
- The receipt format / schema (unchanged; `RECEIPT_VERSION` stays 8).
- Threading a formal `mode` into the provider interface (deferred; empty-expected suffices).
