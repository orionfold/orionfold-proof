# Prompt-aware mocks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `mock_good`/`mock_bad` deterministically vary their output with the candidate's
system prompt, so the keyless prompt-compare demo produces an intuitive winner — while the
model-compare path (`system_prompt is None`) stays byte-identical.

**Architecture:** A single pure helper `_shape_for_prompt(base, system_prompt)` in
`src/orionfold/providers/mock.py` truncates the mock's base output by a "verbosity budget"
derived from concise cues in the prompt. Both mocks call it on their base output. Verbatim on
`None` and on any cue-less prompt; truncated only when a concise cue is recognized.

**Tech Stack:** Python 3.12+, pytest, FastAPI TestClient (integration). No new dependency.

## Global Constraints

- Verbatim guarantee: `system_prompt is None` **and** any cue-less prompt return the original
  `base` string object untouched (no split/re-join) — preserves the "100% (5/5)" contract,
  sample receipts, and `config_hash 467ddd96c9a5`. (model-compare byte-identical)
- Deterministic: pure function of `(base, system_prompt)` — no hashing, no `random`, no state.
- `mock_bad` still raises its simulated failure on `_stable_int(input_text) % 5 == 0` **before**
  shaping → "Failure cases (5)" / "simulated provider failure" contracts intact.
- Verbosity budget tiers (copied verbatim from spec):
  - strong `b = 0.4`: `"as few words as possible"`, `"fewest"`, `"terse"`, `"one sentence"`, `"tl;dr"`
  - mild `b = 0.6`: `"concise"`, `"brief"`, `"short"`, `"minimal"`
  - no cue → `b = 1.0`; strongest (smallest b) wins when both present.
- Truncate to first `max(1, ceil(b * word_count))` whitespace-split words, re-joined with single
  spaces. Only the truncated path normalizes whitespace.
- No UI change, no receipt schema change, no `RECEIPT_VERSION` bump.

---

### Task 1: `_shape_for_prompt` helper + wire into both mocks

**Files:**
- Modify: `src/orionfold/providers/mock.py`
- Test: `tests/unit/test_providers.py`

**Interfaces:**
- Consumes: `Candidate.system_prompt: str | None` (already exists), `Example`, `ProviderResult`.
- Produces: module-level `_shape_for_prompt(base: str, system_prompt: str | None) -> str` in
  `mock.py`; `MockGoodProvider.generate` / `MockBadProvider.generate` now pass their base output
  through it.

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_providers.py` (the existing `_example`, `Candidate`, `MockGoodProvider`,
`MockBadProvider`, `safe_generate`, `load_dataset` imports are already present at the top):

```python
from math import ceil

from orionfold.providers.mock import _shape_for_prompt


def _demo_ex0():
    # The bundled example whose expected_text carries 4 keypoints (22%, $48.2M, 118%, 79%).
    return load_dataset("investment-memo-summarization").examples[0]


def test_shape_verbatim_when_system_prompt_is_none():
    base = "Revenue grew 22% to $48.2M, with 118% net retention and 79% margins."
    # Identity (same object) — model-compare path must not even re-join whitespace.
    assert _shape_for_prompt(base, None) is base


def test_shape_verbatim_when_no_concise_cue():
    base = "Revenue grew 22% to $48.2M, with 118% net retention and 79% margins."
    assert _shape_for_prompt(base, "Be neutral and complete.") is base


def test_shape_strong_cue_truncates_to_40_percent():
    base = " ".join(f"w{i}" for i in range(10))  # 10 words
    out = _shape_for_prompt(base, "Answer in as few words as possible.")
    assert out == " ".join(f"w{i}" for i in range(ceil(0.4 * 10)))  # first 4 words


def test_shape_mild_cue_keeps_more_than_strong_cue():
    base = " ".join(f"w{i}" for i in range(10))
    mild = _shape_for_prompt(base, "Be concise.")
    strong = _shape_for_prompt(base, "Be terse.")
    assert len(mild.split()) > len(strong.split())


def test_shape_strongest_cue_wins_when_both_present():
    base = " ".join(f"w{i}" for i in range(10))
    both = _shape_for_prompt(base, "Be concise and terse.")  # mild + strong
    assert both == _shape_for_prompt(base, "terse")  # strong (0.4) dominates


def test_shape_keeps_at_least_one_word():
    assert _shape_for_prompt("solo", "as few words as possible") == "solo"


def test_mock_good_drops_keypoints_under_concise_prompt():
    provider = MockGoodProvider()
    ex = _demo_ex0()
    full = provider.generate(ex, Candidate(id="m", label="m", provider_id="mock_good"))
    concise = provider.generate(
        ex,
        Candidate(id="m#c", label="c", provider_id="mock_good",
                  system_prompt="Answer in as few words as possible."),
    )
    assert full.output_text == ex.expected_text  # baseline still perfect
    assert len(concise.output_text) < len(full.output_text)
    present = lambda kps, text: sum(1 for k in kps if k in text)
    assert present(ex.keypoints, concise.output_text) < present(ex.keypoints, full.output_text)


def test_mock_good_prompt_shaping_is_deterministic():
    provider = MockGoodProvider()
    ex = _demo_ex0()
    cand = Candidate(id="m#c", label="c", provider_id="mock_good", system_prompt="Be terse.")
    assert provider.generate(ex, cand) == provider.generate(ex, cand)


def test_mock_bad_still_errors_regardless_of_system_prompt():
    provider = MockBadProvider()
    cand = Candidate(id="b#c", label="b", provider_id="mock_bad", system_prompt="Be terse.")
    results = [safe_generate(provider, _example(f"input number {i}"), cand) for i in range(40)]
    assert any(r.error is not None for r in results)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_providers.py -q`
Expected: FAIL — `ImportError: cannot import name '_shape_for_prompt'` (collection error).

- [ ] **Step 3: Implement `_shape_for_prompt` and wire it in**

In `src/orionfold/providers/mock.py`, add `from math import ceil` to the imports, then add the
helper after `_tokens`:

```python
# Concise-instruction cues → a verbosity budget (fraction of words kept). The mocks are
# deterministic simulations: a prompt that asks for brevity drops trailing content (and so
# trailing keypoints), giving the keyless prompt-compare demo a real, explainable signal.
# Strong cues truncate harder than mild ones; the strongest (smallest budget) present wins.
_STRONG_CUES = ("as few words as possible", "fewest", "terse", "one sentence", "tl;dr")
_MILD_CUES = ("concise", "brief", "short", "minimal")


def _shape_for_prompt(base: str, system_prompt: str | None) -> str:
    """Shape a mock's base output by concise cues in ``system_prompt``.

    Returns ``base`` UNCHANGED (same object) when there is no system prompt or no recognized
    cue — the model-compare path stays byte-identical. A concise cue truncates to a prefix.
    """
    if system_prompt is None:
        return base
    prompt = system_prompt.lower()
    budget = 1.0
    if any(cue in prompt for cue in _STRONG_CUES):
        budget = 0.4
    elif any(cue in prompt for cue in _MILD_CUES):
        budget = 0.6
    if budget >= 1.0:
        return base
    words = base.split()
    keep = max(1, ceil(budget * len(words)))
    return " ".join(words[:keep])
```

Then in `MockGoodProvider.generate`, replace `output = example.expected_text` with:

```python
        output = _shape_for_prompt(example.expected_text, candidate.system_prompt)
```

And in `MockBadProvider.generate`, replace `output = _GENERIC_ANSWER` with:

```python
        output = _shape_for_prompt(_GENERIC_ANSWER, candidate.system_prompt)
```

(Leave the `mock_bad` failure check `if _stable_int(example.input_text) % 5 == 0: raise …`
exactly where it is — before the shaping.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_providers.py -q`
Expected: PASS (all, including the pre-existing
`test_mock_good_returns_expected_text_and_is_deterministic` — its candidate has
`system_prompt=None` → verbatim).

- [ ] **Step 5: Lint + full backend suite (regression check)**

Run: `uv run ruff check src tests && uv run pytest -q`
Expected: ruff clean; full suite passes (model-compare paths unchanged).

- [ ] **Step 6: Commit**

```bash
git add src/orionfold/providers/mock.py tests/unit/test_providers.py
git commit -m "feat(providers): cue-driven prompt-aware mock output for keyless prompt-compare"
```

---

### Task 2: Integration — prompt-compare run scores differ (Baseline > Concise)

**Files:**
- Test: `tests/integration/test_proof_api.py`

**Interfaces:**
- Consumes: the `client` fixture and the `/api/runs` prompt-variant shape already used by
  `test_prompt_variant_run_produces_one_entry_per_variant`.
- Produces: nothing consumed downstream (leaf test).

- [ ] **Step 1: Write the failing test**

Add to `tests/integration/test_proof_api.py`, immediately after
`test_prompt_variant_run_produces_one_entry_per_variant`:

```python
def test_prompt_variant_run_scores_differ_baseline_beats_concise(client):
    # Keyless signal: a concise prompt drops keypoints, so it scores below a full-output prompt.
    body = {
        "dataset_id": "investment-memo-summarization",
        "candidate_ids": ["mock_good"],
        "prompt_variants": [
            {"name": "Baseline", "system_prompt": "Complete the task. Output only the result."},
            {"name": "Concise", "system_prompt": "Answer in as few words as possible."},
        ],
        "brief": {"task_name": "t", "decision_question": "q", "success_criteria": ""},
    }
    r = client.post("/api/runs", json=body)
    assert r.status_code == 200, r.text
    by_label = {e["label"]: e for e in r.json()["leaderboard"]}
    assert by_label["Baseline"]["avg_score"] > by_label["Concise"]["avg_score"]
```

(`avg_score` is the verified score field on `LeaderboardEntry`, `src/orionfold/domain/models.py:115`.)

- [ ] **Step 2: Run test to verify it passes (Task 1 already provides the behavior)**

Run: `uv run pytest tests/integration/test_proof_api.py::test_prompt_variant_run_scores_differ_baseline_beats_concise -v`
Expected: PASS — Baseline returns full `expected_text` (keypoint coverage 100%), Concise
truncates and drops trailing keypoints (lower coverage). If it had been run against pre-Task-1
code it would FAIL on equal scores; that is the behavior Task 1 introduced.

- [ ] **Step 3: No implementation needed**

Task 1 already produces the behavior; this task locks it at the API boundary.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_proof_api.py::test_prompt_variant_run_scores_differ_baseline_beats_concise -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_proof_api.py
git commit -m "test(integration): keyless prompt-compare scores differ (Baseline > Concise)"
```

---

### Final verification (after both tasks)

- [ ] `uv run pytest -q` → all pass (was 213; now +~9 unit/integration).
- [ ] `uv run ruff check src tests` → clean.
- [ ] `pnpm --dir web test` → 83/83 (frontend untouched; sanity).
- [ ] `bash scripts/build.sh && pnpm --dir web e2e` → 6/6 (the keyless prompt-compare e2e
  asserts labels + receipt count, not scores → stays green).
- [ ] Confirm sample receipt `config_hash` is still `467ddd96c9a5`:
  `grep -o '467ddd96c9a5' samples/receipts/sample-proof-receipt.json` → one match (no
  regeneration needed; model-compare output byte-identical).
- [ ] Real browser check on a provably-free port: `orionfold up --port <free>`, switch to
  Prompts, run keyless, confirm Baseline outranks Concise on the leaderboard.
- [ ] Append `docs/worklog/` entry; overwrite `HANDOFF.md`.
