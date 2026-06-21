# Meaning-Aware Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace format-sensitive similarity scoring with meaning-aware scoring — a deterministic keypoint-coverage rubric (the new keyless default) and an opt-in LLM judge — while accounting for all costs including judge cost.

**Architecture:** Two additive `RubricKind`s. `keypoint` scores the fraction of authored required facts present in an output (deterministic, keyless, new default when a dataset carries keypoints). `judge` asks a provider model to grade meaning vs `expected_text` 0..1 through a small `Judge` seam that reuses the provider boundary; a keyless `MockJudge` keeps tests deterministic. Judge cost/latency are captured per-cell and rolled up into a run-level `RunCostSummary` — never mixed into the candidate's number or the leaderboard ranking. The receipt gains a "Scored by" line and a "Run cost" summary at `RECEIPT_VERSION 5`.

**Tech Stack:** Python 3.12, Pydantic, FastAPI, pytest (backend); Vite + React + TypeScript + Zod + TanStack Query + Vitest + Playwright (frontend). No new dependencies.

## Global Constraints

- **Keyless determinism:** the full test suite must run with no API keys; `MockJudge` (`judge_provider_id == "mock_judge"`) is the keyless judge. The default rubric never selects `judge`.
- **Keyless-mock default unchanged:** `mock_good`/`mock_bad` stay bare-id, `model=None`; `mock_good` returns `expected_text` verbatim and MUST remain the 5/5 sample winner → every authored keypoint MUST be a normalized substring of its example's `expected_text`.
- **Candidate cost stays clean:** `ResultRow.estimated_cost_usd` remains candidate-only and is the leaderboard cost tiebreak. Judge cost lives ONLY in `ResultRow.judge_cost_usd` + `RunCostSummary`; it never enters `leaderboard.py` ranking.
- **Provenance:** `config_hash` hashes `dataset` + `candidates` + `rubric.model_dump()`. `keypoints` (on `Example`) and `judge_provider_id`/`judge_model` (on `Rubric`) flow into it; the cost fields are run OUTPUT and do not. `config_hash` WILL change — intentional; regenerate samples, re-pin hash tests.
- **RECEIPT_VERSION lands at exactly 5** (one bump for the whole slice).
- **Secrets:** judge API key never appears in any receipt, log, response, or screenshot. `judge_provider_id`/`judge_model` are safe to display. Reuse `redact_secrets` at the provider boundary.
- **Finding-1 non-regressions:** leaderboard never recommends a 0-pass/all-errored candidate; calm NEUTRAL no-winner state; errored rows say "errored, no output". A judge error is an ERROR (`row.error` set, `score 0.0`, not-passed), not a low-scoring fail.
- **Frontend:** Tailwind v4 CSS-var parenthesis shorthand `bg-(--color-x)`, never `bg-[--color-x]`. Preserve test-contract strings (heading "Orionfold Proof", "Connected", button /Run proof/, regions "Leaderboard"/"Failure cases"/"Proof Receipt export", "Export Markdown|HTML|JSON"). Verdict vocabulary includes "No clear winner".
- After backend/catalog/recipe changes, RESTART `orionfold up` (no hot reload of `@cache`d data); REBUILD the embedded cockpit (`bash scripts/build.sh`) before any e2e/browser check.

## File Structure

**Backend**
- `src/orionfold/domain/models.py` — MODIFY: `Example.keypoints`; `RubricKind`; `Rubric.judge_*`; `ResultRow.judge_*`; new `RunCostSummary`; `ProofReport.cost_summary`.
- `src/orionfold/scoring/rubric.py` — MODIFY: `keypoint` branch in `score()`; new `default_rubric_for(dataset)`.
- `src/orionfold/scoring/judge.py` — CREATE: `JudgeOutcome`, `parse_score`, `Judge` protocol, `MockJudge`, `LLMJudge`, `build_judge`, `grading_prompt`.
- `src/orionfold/proof/engine.py` — MODIFY: judge branch in `iter_matrix`; `build_cost_summary(rows)`; `run_proof` wires cost summary + judge validation.
- `src/orionfold/receipts/export.py` — MODIFY: `RECEIPT_VERSION = 5`; `_scored_by` + run-cost in `build_receipt`/MD/HTML.
- `src/orionfold/server/routes.py` — MODIFY: stream endpoint builds `cost_summary` via the shared helper; judge-without-model → 422.
- `src/orionfold/data/datasets/investment_memo_summarization.json` — MODIFY: author `keypoints` per example.
- `scripts/gen_samples.py` — MODIFY: use `default_rubric_for(dataset)`; regenerate `samples/receipts/*`.

**Frontend** — filled in after the frontend exploration (Tasks 8+).

---

### Task 1: Domain model — keypoints, judge fields, cost fields

**Files:**
- Modify: `src/orionfold/domain/models.py`
- Test: `tests/test_models.py` (create if absent; else append)

**Interfaces:**
- Produces: `Example.keypoints: list[str]` (default `[]`); `RubricKind` literal `"exact"|"contains"|"similarity"|"keypoint"|"judge"`; `Rubric.judge_provider_id: str | None`, `Rubric.judge_model: str | None` (default `None`); `ResultRow.judge_cost_usd: float` + `judge_latency_ms: int` (default `0.0`/`0`); `RunCostSummary(candidate_cost_usd, judge_cost_usd, total_cost_usd)`; `ProofReport.cost_summary: RunCostSummary`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from orionfold.domain.models import (
    Example, Rubric, ResultRow, RunCostSummary, ProofReport,
)


def test_example_keypoints_default_empty():
    assert Example(input_text="i", expected_text="e").keypoints == []


def test_rubric_judge_fields_default_none():
    r = Rubric()
    assert r.kind == "similarity"
    assert r.judge_provider_id is None and r.judge_model is None


def test_rubric_accepts_new_kinds():
    assert Rubric(kind="keypoint").kind == "keypoint"
    assert Rubric(kind="judge", judge_provider_id="mock_judge").kind == "judge"


def test_result_row_judge_cost_defaults_zero():
    row = ResultRow(
        candidate_id="c", example_index=0, input_text="i", expected_text="e",
        output_text="o", score=1.0, passed=True, latency_ms=10,
        estimated_cost_usd=0.0, privacy="local",
    )
    assert row.judge_cost_usd == 0.0 and row.judge_latency_ms == 0


def test_run_cost_summary_shape():
    s = RunCostSummary(candidate_cost_usd=0.01, judge_cost_usd=0.002, total_cost_usd=0.012)
    assert s.total_cost_usd == 0.012
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'RunCostSummary'` / unexpected-kwarg errors.

- [ ] **Step 3: Write minimal implementation**

In `src/orionfold/domain/models.py`:
- Extend the kind literal:
```python
RubricKind = Literal["exact", "contains", "similarity", "keypoint", "judge"]
```
- Add to `Example`:
```python
    keypoints: list[str] = []           # authored required facts; [] = none
```
- Add to `Rubric` (after `case_sensitive`):
```python
    judge_provider_id: str | None = None  # only used when kind == "judge"
    judge_model: str | None = None        # recorded in provenance; shown in the receipt
```
- Add to `ResultRow` (after `estimated_cost_usd`):
```python
    judge_cost_usd: float = 0.0          # cost of the judge call for this cell (0 for non-judge)
    judge_latency_ms: int = 0            # judge latency for this cell (0 for non-judge)
```
- Add a new model + field (place `RunCostSummary` above `ProofReport`):
```python
class RunCostSummary(BaseModel):
    """The full cost picture for a run — candidate, judge, and grand total (USD)."""

    candidate_cost_usd: float
    judge_cost_usd: float
    total_cost_usd: float
```
- Add to `ProofReport`:
```python
    cost_summary: RunCostSummary
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_models.py -v`
Expected: PASS (5 tests).

> NOTE: existing tests that construct `ProofReport(...)` directly now require `cost_summary`. Leave them for Task 4 (where `build_cost_summary` + `run_proof` provide it) — if any unit test constructs `ProofReport` by hand, it will be updated in the task that owns it. Run `uv run pytest -q` and note (do not fix yet) any `ProofReport`-construction failures; Task 4 resolves them.

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/domain/models.py tests/test_models.py
git commit -m "feat(models): keypoints, judge rubric fields, per-row judge cost, RunCostSummary"
```

---

### Task 2: Keypoint scoring + default rubric selection

**Files:**
- Modify: `src/orionfold/scoring/rubric.py`
- Test: `tests/test_scoring.py` (append; create if absent)

**Interfaces:**
- Consumes: `Rubric`, `Example`, `Dataset` from `domain.models`; existing `normalize()`, `score()`, `passed()`.
- Produces: `score(expected, output, rubric)` handles `kind == "keypoint"`; new `default_rubric_for(dataset: Dataset) -> Rubric`.

Keypoint semantics: with `rubric.kind == "keypoint"`, score = (count of `example`'s keypoints whose normalized text is a substring of the normalized output) / (number of keypoints). **`score()` itself receives only `expected`/`output`/`rubric`, not the example's keypoints** — so keypoints are passed via the rubric? No: keypoints are per-example. Resolution: add a keypoints-aware overload used by the engine. Implement a dedicated `score_keypoints(keypoints, output, rubric) -> float` and have `score()` delegate ONLY for the non-keypoint kinds; the engine calls `score_keypoints` when `kind == "keypoint"` (Task 4). Empty keypoints → fall back to `similarity` against `expected` (handled in Task 4 where both are in scope).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scoring.py
from orionfold.domain.models import Dataset, Example, Rubric
from orionfold.scoring.rubric import score_keypoints, default_rubric_for


_R = Rubric(kind="keypoint")


def test_keypoints_all_present_scores_one():
    out = "Revenue grew 22% to $48.2M with 118% retention and 79% margin."
    assert score_keypoints(["22%", "$48.2M", "118%", "79%"], out, _R) == 1.0


def test_keypoints_partial_coverage():
    out = "Revenue grew 22% to $48.2M."
    assert score_keypoints(["22%", "$48.2M", "118%", "79%"], out, _R) == 0.5


def test_keypoints_none_present_scores_zero():
    assert score_keypoints(["22%", "118%"], "An unrelated generic answer.", _R) == 0.0


def test_keypoints_case_insensitive_by_default():
    assert score_keypoints(["Series B"], "raising a series b round", _R) == 1.0


def test_keypoints_empty_list_returns_zero_sentinel():
    # Empty keypoints is the engine's fallback signal; the primitive returns 0.0 for "nothing matched".
    assert score_keypoints([], "anything", _R) == 0.0


def test_default_rubric_keypoint_when_present():
    ds = Dataset(id="d", name="d", examples=[Example(input_text="i", expected_text="e", keypoints=["x"])])
    assert default_rubric_for(ds).kind == "keypoint"


def test_default_rubric_similarity_when_absent():
    ds = Dataset(id="d", name="d", examples=[Example(input_text="i", expected_text="e")])
    assert default_rubric_for(ds).kind == "similarity"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_scoring.py -k "keypoint or default_rubric" -v`
Expected: FAIL — `ImportError: cannot import name 'score_keypoints'`.

- [ ] **Step 3: Write minimal implementation**

In `src/orionfold/scoring/rubric.py` add:
```python
from orionfold.domain.models import Dataset  # add to existing imports


def score_keypoints(keypoints: list[str], output: str, rubric: Rubric) -> float:
    """Fraction of ``keypoints`` whose normalized text appears in the normalized output.

    Empty keypoints returns 0.0; the engine treats an empty list as a signal to fall back to
    similarity scoring for that row, so this primitive never has to know about the fallback.
    """
    if not keypoints:
        return 0.0
    out = normalize(output, case_sensitive=rubric.case_sensitive)
    hits = sum(
        1 for kp in keypoints if normalize(kp, case_sensitive=rubric.case_sensitive) in out
    )
    return hits / len(keypoints)


def default_rubric_for(dataset: Dataset) -> Rubric:
    """Pick the default rubric for a dataset: keypoint when any example carries keypoints."""
    if any(ex.keypoints for ex in dataset.examples):
        return Rubric(kind="keypoint")
    return Rubric(kind="similarity")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_scoring.py -k "keypoint or default_rubric" -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/scoring/rubric.py tests/test_scoring.py
git commit -m "feat(scoring): keypoint-coverage primitive + default_rubric_for"
```

---

### Task 3: Judge seam (`scoring/judge.py`)

**Files:**
- Create: `src/orionfold/scoring/judge.py`
- Test: `tests/test_judge.py`

**Interfaces:**
- Consumes: `safe_generate` + `Provider` from `providers.base`; `get_provider` from `providers.registry`; `Example`, `Candidate`, `Rubric`, `ProviderResult` from `domain.models`.
- Produces:
  - `JudgeOutcome(score: float, cost_usd: float, latency_ms: int, error: str | None)`
  - `parse_score(text: str) -> float | None` — first float in text, accepts `0..1` directly or `0..100`/`0..10` rescaled; clamps to `[0,1]`; `None` if no number.
  - `grading_prompt(expected: str, output: str) -> str`
  - `MockJudge` — keyless deterministic: `score(expected, output)` returns `JudgeOutcome` with `score = difflib ratio`, `cost_usd = 0.0001`, `latency_ms = 5`, `error=None`.
  - `LLMJudge(provider, model)` — `score(expected, output)` builds a synthetic `Example(input_text=grading_prompt(...), expected_text="")` + `Candidate(id="judge", label="judge", provider_id=provider.id, model=model)`, calls `safe_generate`, parses the number; on provider error OR unparseable score returns `JudgeOutcome(score=0.0, ..., error=<msg>)`.
  - `build_judge(rubric: Rubric) -> Judge` — `"mock_judge"` → `MockJudge()`; else `LLMJudge(get_provider(rubric.judge_provider_id), rubric.judge_model)`. Raises `ValueError("judge rubric requires judge_provider_id")` when missing.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_judge.py
import pytest
from orionfold.domain.models import Rubric
from orionfold.scoring.judge import (
    JudgeOutcome, parse_score, MockJudge, LLMJudge, build_judge,
)


def test_parse_score_unit_interval():
    assert parse_score("0.73") == 0.73


def test_parse_score_rescales_percent():
    assert parse_score("Score: 85") == 0.85


def test_parse_score_clamps_and_handles_garbage():
    assert parse_score("1.4") == 1.0
    assert parse_score("no number here") is None


def test_mock_judge_is_deterministic():
    a = MockJudge().score("the cat sat", "the cat sat")
    b = MockJudge().score("the cat sat", "the cat sat")
    assert a.score == b.score == 1.0
    assert a.cost_usd == 0.0001 and a.error is None


def test_build_judge_requires_provider_id():
    with pytest.raises(ValueError):
        build_judge(Rubric(kind="judge"))


def test_build_judge_mock():
    assert isinstance(build_judge(Rubric(kind="judge", judge_provider_id="mock_judge")), MockJudge)


class _FakeProvider:
    id = "fake"
    label = "Fake"
    privacy = "local"

    def __init__(self, text):
        self._text = text

    def generate(self, example, candidate):
        from orionfold.domain.models import ProviderResult
        return ProviderResult(output_text=self._text, latency_ms=12, estimated_cost_usd=0.003, privacy="local")


def test_llm_judge_parses_and_carries_cost():
    out = LLMJudge(_FakeProvider("0.9"), "m").score("expected", "output")
    assert out.score == 0.9 and out.cost_usd == 0.003 and out.latency_ms == 12 and out.error is None


def test_llm_judge_unparseable_is_error():
    out = LLMJudge(_FakeProvider("I think it is good"), "m").score("expected", "output")
    assert out.score == 0.0 and out.error is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_judge.py -v`
Expected: FAIL — module `orionfold.scoring.judge` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# src/orionfold/scoring/judge.py
"""LLM-as-judge seam — meaning-aware scoring for the ``judge`` rubric (deferred from v0).

The judge reuses the provider boundary: a real judge builds a grading prompt, calls the model
through ``safe_generate`` (inheriting cost estimation AND secret redaction), and parses a single
number. ``MockJudge`` is the keyless, deterministic judge that keeps the suite reproducible.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Protocol

from orionfold.domain.models import Candidate, Example, Rubric
from orionfold.providers.base import Provider, safe_generate
from orionfold.providers.registry import get_provider

_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


@dataclass
class JudgeOutcome:
    score: float
    cost_usd: float
    latency_ms: int
    error: str | None = None


def parse_score(text: str) -> float | None:
    """First number in ``text`` as a 0..1 score. The prompt asks for 0..1; this is defensive
    for malformed replies. A value in (1, 2] is read as the model overshooting the requested
    max -> clamp to 1.0; (2, 10] is a 0..10 scale -> /10; > 10 is a 0..100 scale -> /100."""
    m = _NUMBER.search(text or "")
    if m is None:
        return None
    value = float(m.group())
    if value > 10:        # 0..100 scale, e.g. "85" -> 0.85
        value /= 100.0
    elif value > 2:       # 0..10 scale, e.g. "7" -> 0.7 ((1,2] is overshoot -> clamps below)
        value /= 10.0
    return max(0.0, min(1.0, value))


def grading_prompt(expected: str, output: str) -> str:
    return (
        "You are grading how well a candidate answer captures the MEANING of a reference "
        "answer, ignoring wording and format. Reply with ONLY a number from 0 to 1.\n\n"
        f"Reference answer:\n{expected}\n\n"
        f"Candidate answer:\n{output}\n\n"
        "Score (0 to 1):"
    )


class Judge(Protocol):
    def score(self, expected: str, output: str) -> JudgeOutcome: ...


class MockJudge:
    """Deterministic keyless judge: difflib ratio with a fixed nominal cost."""

    def score(self, expected: str, output: str) -> JudgeOutcome:
        ratio = SequenceMatcher(None, expected, output).ratio()
        return JudgeOutcome(score=ratio, cost_usd=0.0001, latency_ms=5, error=None)


class LLMJudge:
    def __init__(self, provider: Provider, model: str | None) -> None:
        self._provider = provider
        self._model = model

    def score(self, expected: str, output: str) -> JudgeOutcome:
        example = Example(input_text=grading_prompt(expected, output), expected_text="")
        candidate = Candidate(
            id="judge", label="judge", provider_id=self._provider.id, model=self._model
        )
        result = safe_generate(self._provider, example, candidate)
        if result.error is not None:
            return JudgeOutcome(0.0, result.estimated_cost_usd, result.latency_ms, result.error)
        value = parse_score(result.output_text)
        if value is None:
            return JudgeOutcome(
                0.0, result.estimated_cost_usd, result.latency_ms,
                "judge returned an unparseable score",
            )
        return JudgeOutcome(value, result.estimated_cost_usd, result.latency_ms, None)


def build_judge(rubric: Rubric) -> Judge:
    """Resolve the judge for a rubric. ``mock_judge`` is keyless; others resolve via the registry."""
    if not rubric.judge_provider_id:
        raise ValueError("judge rubric requires judge_provider_id")
    if rubric.judge_provider_id == "mock_judge":
        return MockJudge()
    return LLMJudge(get_provider(rubric.judge_provider_id), rubric.judge_model)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_judge.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/scoring/judge.py tests/test_judge.py
git commit -m "feat(scoring): LLM judge seam (LLMJudge + keyless MockJudge + parse_score)"
```

---

### Task 4: Engine — judge branch, keypoint wiring, cost rollup, validation

**Files:**
- Modify: `src/orionfold/proof/engine.py`
- Test: `tests/test_engine.py` (append)

**Interfaces:**
- Consumes: `score`, `passed`, `score_keypoints` from `scoring.rubric`; `build_judge`, `Judge` from `scoring.judge`; `safe_generate`, `get_provider`; `RunCostSummary`, `ProofReport`.
- Produces: `build_cost_summary(rows: list[ResultRow]) -> RunCostSummary`; `iter_matrix`/`run_matrix` score keypoint + judge kinds and populate `judge_cost_usd`/`judge_latency_ms`; `run_proof` validates judge config up front and sets `cost_summary` on the report.

Scoring branch per row (in `iter_matrix`, replacing the current `else` score block):
- candidate provider error → `score 0.0, did_pass False` (unchanged), judge NOT consulted.
- `rubric.kind == "keypoint"` → `kp = score_keypoints(example.keypoints, output, rubric)` when `example.keypoints` else `score(expected, output, similarity_rubric)`; `did_pass = passed(value, rubric)`.
- `rubric.kind == "judge"` → `outcome = judge.score(example.expected_text, output)`; `score_value = outcome.score`; `judge_cost = outcome.cost_usd`; `judge_latency = outcome.latency_ms`; if `outcome.error` → set `row.error = outcome.error`, `did_pass = False` (error, not fail).
- else → existing `score()`.

Build `judge` ONCE before the candidate loop when `rubric.kind == "judge"` via `build_judge(rubric)` (so a missing/unknown judge provider raises before any work).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_engine.py (append)
import pytest
from orionfold.domain.models import Candidate, Dataset, Example, ProofBrief, Rubric
from orionfold.proof.engine import build_cost_summary, run_proof


def _ds():
    return Dataset(id="d", name="d", examples=[
        Example(input_text="Q3 rev $48.2M up 22%", expected_text="Revenue grew 22% to $48.2M.",
                keypoints=["22%", "$48.2M"]),
    ])


def _run(rubric):
    return run_proof(
        run_id="r1", created_at="2026-06-21T00:00:00Z",
        brief=ProofBrief(task_name="t", decision_question="q"),
        dataset=_ds(),
        candidates=[Candidate(id="mock_good", label="g", provider_id="mock_good")],
        rubric=rubric,
    )


def test_keypoint_run_passes_for_mock_good():
    report = _run(Rubric(kind="keypoint"))
    assert report.results[0].score == 1.0 and report.results[0].passed


def test_judge_run_via_mock_is_deterministic_and_costed():
    report = _run(Rubric(kind="judge", judge_provider_id="mock_judge"))
    row = report.results[0]
    assert row.judge_cost_usd == 0.0001 and row.judge_latency_ms == 5
    assert report.cost_summary.judge_cost_usd == pytest.approx(0.0001)


def test_judge_without_provider_id_raises():
    with pytest.raises(ValueError):
        _run(Rubric(kind="judge"))


def test_cost_summary_totals():
    report = _run(Rubric(kind="judge", judge_provider_id="mock_judge"))
    cs = report.cost_summary
    assert cs.total_cost_usd == pytest.approx(cs.candidate_cost_usd + cs.judge_cost_usd)


def test_non_judge_run_has_zero_judge_cost():
    report = _run(Rubric(kind="keypoint"))
    assert report.cost_summary.judge_cost_usd == 0.0
    assert report.cost_summary.total_cost_usd == report.cost_summary.candidate_cost_usd
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_engine.py -k "keypoint or judge or cost_summary" -v`
Expected: FAIL — `ImportError: cannot import name 'build_cost_summary'`.

- [ ] **Step 3: Write minimal implementation**

In `src/orionfold/proof/engine.py`:
- Add imports:
```python
from orionfold.domain.models import RunCostSummary
from orionfold.scoring.judge import Judge, build_judge
from orionfold.scoring.rubric import score_keypoints
```
- Add the rollup helper:
```python
def build_cost_summary(rows: list[ResultRow]) -> RunCostSummary:
    """Roll per-row costs up into the full run cost picture (candidate + judge + total)."""
    candidate = sum(r.estimated_cost_usd for r in rows)
    judge = sum(r.judge_cost_usd for r in rows)
    return RunCostSummary(
        candidate_cost_usd=candidate, judge_cost_usd=judge, total_cost_usd=candidate + judge
    )
```
- Refactor `iter_matrix` to build the judge once and branch per kind:
```python
def iter_matrix(
    dataset: Dataset, candidates: list[Candidate], rubric: Rubric
) -> Iterator[ResultRow]:
    judge: Judge | None = build_judge(rubric) if rubric.kind == "judge" else None
    for candidate in candidates:
        provider = get_provider(candidate.provider_id)
        for index, example in enumerate(dataset.examples):
            result = safe_generate(provider, example, candidate)
            judge_cost, judge_latency, judge_error = 0.0, 0, None
            if result.error is not None:
                score_value, did_pass = 0.0, False
            elif rubric.kind == "keypoint":
                score_value = (
                    score_keypoints(example.keypoints, result.output_text, rubric)
                    if example.keypoints
                    else score(example.expected_text, result.output_text, _SIMILARITY)
                )
                did_pass = passed(score_value, rubric)
            elif rubric.kind == "judge":
                assert judge is not None
                outcome = judge.score(example.expected_text, result.output_text)
                score_value = outcome.score
                judge_cost, judge_latency, judge_error = (
                    outcome.cost_usd, outcome.latency_ms, outcome.error
                )
                did_pass = judge_error is None and passed(score_value, rubric)
            else:
                score_value = score(example.expected_text, result.output_text, rubric)
                did_pass = passed(score_value, rubric)
            yield ResultRow(
                candidate_id=candidate.id,
                example_index=index,
                input_text=example.input_text,
                expected_text=example.expected_text,
                output_text=result.output_text,
                score=score_value,
                passed=did_pass,
                latency_ms=result.latency_ms,
                estimated_cost_usd=result.estimated_cost_usd,
                judge_cost_usd=judge_cost,
                judge_latency_ms=judge_latency,
                privacy=result.privacy,
                error=result.error if result.error is not None else judge_error,
            )
```
- Add the similarity fallback rubric constant near the top of the module:
```python
_SIMILARITY = Rubric(kind="similarity")
```
- In `run_proof`, after `results = run_matrix(...)`, build the report with the cost summary:
```python
    cost_summary = build_cost_summary(results)
    ...
    return ProofReport(run=run, leaderboard=leaderboard, results=results, cost_summary=cost_summary)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_engine.py -v`
Expected: PASS, including the new tests. Then run the whole backend suite and fix any `ProofReport(...)`-construction sites flagged in Task 1 by passing `cost_summary=build_cost_summary(rows)` (or `RunCostSummary(0,0,0)` for hand-built fixtures):

Run: `uv run pytest -q`
Expected: PASS (all). Fix construction-site failures inline here.

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/proof/engine.py tests/test_engine.py
git commit -m "feat(engine): keypoint + judge scoring branches and run-level cost rollup"
```

---

### Task 5: Receipt — RECEIPT_VERSION 5, Scored-by + Run-cost

**Files:**
- Modify: `src/orionfold/receipts/export.py`
- Test: `tests/test_receipts.py` (append)

**Interfaces:**
- Consumes: `ProofReport.cost_summary`, `run.rubric` (kind + judge_model).
- Produces: `RECEIPT_VERSION == 5`; `build_receipt` adds `"scored_by": str` and `"cost": {candidate, judge, total}`; MD + HTML render a "Scored by" line and a "Run cost" line.

`_scored_by(rubric)` text:
- `keypoint` → `"Keypoint coverage"`
- `similarity` → `"Similarity"`
- `exact` → `"Exact match"`; `contains` → `"Contains"`
- `judge` → `f"LLM judge · {rubric.judge_model or rubric.judge_provider_id}"`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_receipts.py (append)
from orionfold.receipts.export import RECEIPT_VERSION, build_receipt, to_markdown, to_html
# Reuse an existing report factory/fixture in this file; below assumes `make_report(rubric=...)`.


def test_receipt_version_is_5():
    assert RECEIPT_VERSION == 5


def test_scored_by_keypoint(make_report):
    data = build_receipt(make_report(kind="keypoint"))
    assert data["scored_by"] == "Keypoint coverage"


def test_scored_by_judge_shows_model(make_report):
    data = build_receipt(make_report(kind="judge", judge_provider_id="mock_judge", judge_model="claude-haiku-4-5"))
    assert "LLM judge" in data["scored_by"] and "claude-haiku-4-5" in data["scored_by"]


def test_cost_block_present(make_report):
    data = build_receipt(make_report(kind="keypoint"))
    assert set(data["cost"]) == {"candidate", "judge", "total"}


def test_markdown_has_scored_by_and_run_cost(make_report):
    md = to_markdown(make_report(kind="keypoint"))
    assert "Scored by" in md and "Run cost" in md


def test_html_has_scored_by_and_run_cost(make_report):
    h = to_html(make_report(kind="keypoint"))
    assert "Scored by" in h and "Run cost" in h
```

> If `tests/test_receipts.py` has no `make_report` fixture, add a small `@pytest.fixture` that calls `run_proof` with the mock candidates and a parameterizable rubric (mirror `scripts/gen_samples.py`), accepting `kind`/`judge_provider_id`/`judge_model` kwargs.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_receipts.py -k "scored_by or cost_block or run_cost or version_is_5" -v`
Expected: FAIL — `RECEIPT_VERSION == 4`; `KeyError: 'scored_by'`.

- [ ] **Step 3: Write minimal implementation**

In `src/orionfold/receipts/export.py`:
- Bump + document:
```python
# v5: meaning-aware scoring — a "Scored by" descriptor (keypoint coverage / similarity / LLM
# judge · <model>) and a run-level cost summary (candidate + judge + total).
RECEIPT_VERSION = 5
```
- Add the descriptor helper:
```python
def _scored_by(rubric) -> str:
    if rubric.kind == "keypoint":
        return "Keypoint coverage"
    if rubric.kind == "judge":
        return f"LLM judge · {rubric.judge_model or rubric.judge_provider_id}"
    return {"similarity": "Similarity", "exact": "Exact match", "contains": "Contains"}.get(
        rubric.kind, rubric.kind
    )
```
- In `build_receipt`, add to the returned dict (after `"summary"`):
```python
        "scored_by": _scored_by(run.rubric),
        "cost": {
            "candidate": report.cost_summary.candidate_cost_usd,
            "judge": report.cost_summary.judge_cost_usd,
            "total": report.cost_summary.total_cost_usd,
        },
```
- In `to_markdown`, add a `- **Scored by:** …` bullet next to the Rubric bullet, and after the leaderboard table a calm run-cost line:
```python
        f"- **Scored by:** {data['scored_by']}",
```
```python
    c = data["cost"]
    lines += [
        "",
        f"_Run cost: candidate ${c['candidate']:.4f} · judge ${c['judge']:.4f} · "
        f"total ${c['total']:.4f}_",
    ]
```
- In `to_html`, add a `<dt>Scored by</dt><dd>{…}</dd>` row in the `<dl>` and a run-cost `<p class="muted">Run cost: …</p>` after the leaderboard table. Use `html.escape(data['scored_by'])`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_receipts.py -v`
Expected: PASS. Confirm no secrets surface (judge model is safe; no key fields exist on the rubric).

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/receipts/export.py tests/test_receipts.py
git commit -m "feat(receipts): v5 — Scored-by descriptor + run cost summary (candidate+judge+total)"
```

---

### Task 6: Demo dataset keypoints + sample regeneration

**Files:**
- Modify: `src/orionfold/data/datasets/investment_memo_summarization.json`
- Modify: `scripts/gen_samples.py`
- Modify (generated): `samples/receipts/sample-proof-receipt.{json,md,html}`
- Test: `tests/test_data.py` (append; create if absent)

**Interfaces:**
- Consumes: `default_rubric_for` from `scoring.rubric`.
- Produces: every bundled example carries keypoints that are normalized substrings of its `expected_text`; `gen_samples` uses `default_rubric_for(dataset)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_data.py (append)
from orionfold.data import load_dataset
from orionfold.scoring.rubric import default_rubric_for, normalize


def test_demo_dataset_has_keypoints():
    ds = load_dataset("investment-memo-summarization")
    assert all(ex.keypoints for ex in ds.examples)


def test_demo_keypoints_are_substrings_of_expected():
    ds = load_dataset("investment-memo-summarization")
    for ex in ds.examples:
        exp = normalize(ex.expected_text)
        for kp in ex.keypoints:
            assert normalize(kp) in exp, f"{kp!r} not in expected {ex.expected_text!r}"


def test_demo_default_rubric_is_keypoint():
    assert default_rubric_for(load_dataset("investment-memo-summarization")).kind == "keypoint"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_data.py -k demo -v`
Expected: FAIL — examples have no keypoints.

- [ ] **Step 3: Write minimal implementation**

Add a `"keypoints"` array to each example in `investment_memo_summarization.json` (each token a normalized substring of that example's `expected_text`):
- Ex 1: `["22%", "$48.2M", "118%", "79%"]`
- Ex 2: `["$6.1M", "eight quarters", "engineering", "breakeven"]`
- Ex 3: `["4.2%", "under 1%", "self-serve", "larger-account"]`
- Ex 4: `["mid-market", "annual discounts", "9%", "average selling price"]`
- Ex 5: `["$15M", "Series B", "$90M", "2.1x", "board seat", "1x non-participating"]`

In `scripts/gen_samples.py`: replace `from orionfold.domain.models import Candidate, ProofBrief, Rubric` usage of `rubric=Rubric()` with the dataset default:
```python
from orionfold.scoring.rubric import default_rubric_for
...
    dataset = load_dataset("investment-memo-summarization")
    report = run_proof(
        ...
        dataset=dataset,
        candidates=[...],
        rubric=default_rubric_for(dataset),
    )
```

- [ ] **Step 4: Run test + regenerate samples**

Run: `uv run pytest tests/test_data.py -k demo -v` → PASS.
Run: `uv run python scripts/gen_samples.py`
Expected: prints a NEW `config_hash` (intentional). Inspect `samples/receipts/sample-proof-receipt.md`: `mock_good` is still 5/5 (⭐), `mock_bad` shows a non-zero error count, "Scored by: Keypoint coverage" and a "Run cost" line appear.

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/data/datasets/investment_memo_summarization.json scripts/gen_samples.py samples/receipts tests/test_data.py
git commit -m "feat(data): author demo keypoints; samples regen on keypoint default (v5)"
```

---

### Task 7: Server — optional rubric (Auto default), stream cost summary, judge 422

**Files:**
- Modify: `src/orionfold/server/routes.py`
- Test: `tests/test_api.py` (append; match the existing API-test style/fixtures)

**Interfaces:**
- Consumes: `build_cost_summary` + `build_judge`; `default_rubric_for` from `scoring.rubric`.
- Produces: `RunRequest.rubric: Rubric | None = None`; both run endpoints resolve `rubric = body.rubric or default_rubric_for(dataset)`; `/runs/stream` report frame carries `cost_summary`; a `kind == "judge"` run without a resolvable judge model returns HTTP 422 (no key echoed).

> WHY optional: the cockpit's "Auto" scoring method omits the rubric, and the server then defaults to keypoint-when-the-dataset-has-keypoints. This is what makes the keyless demo (and the e2e) show keypoint scoring without the client computing it. Existing callers that omit `rubric` now get the dataset default instead of forced similarity — intended.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api.py (append — reuse the existing TestClient fixture, here `client`)
def test_run_omitting_rubric_uses_keypoint_default(client, seeded_dataset_id):
    # The seeded demo dataset carries keypoints, so Auto resolves to keypoint.
    resp = client.post("/api/runs", json={
        "dataset_id": seeded_dataset_id,
        "candidate_ids": ["mock_good"],
        "brief": {"task_name": "t", "decision_question": "q"},
    })
    assert resp.status_code == 200
    assert resp.json()["run"]["rubric"]["kind"] == "keypoint"


def test_run_judge_without_model_is_422(client, seeded_dataset_id):
    resp = client.post("/api/runs", json={
        "dataset_id": seeded_dataset_id,
        "candidate_ids": ["mock_good"],
        "rubric": {"kind": "judge", "threshold": 0.8, "case_sensitive": False},
        "brief": {"task_name": "t", "decision_question": "q"},
    })
    assert resp.status_code == 422


def test_run_report_has_cost_summary(client, seeded_dataset_id):
    resp = client.post("/api/runs", json={
        "dataset_id": seeded_dataset_id,
        "candidate_ids": ["mock_good"],
        "rubric": {"kind": "keypoint", "threshold": 0.8, "case_sensitive": False},
        "brief": {"task_name": "t", "decision_question": "q"},
    })
    assert resp.status_code == 200
    assert "cost_summary" in resp.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_api.py -k "rubric or judge_without_model or cost_summary" -v`
Expected: FAIL — Auto still defaults to similarity; `ValueError` surfaces as 500 (not 422); stream path missing cost_summary.

- [ ] **Step 3: Write minimal implementation**

- Imports (top of `routes.py`):
```python
from orionfold.proof.engine import build_cost_summary, config_hash, iter_matrix, run_proof
from orionfold.scoring.judge import build_judge
from orionfold.scoring.rubric import default_rubric_for
```
- Make the request rubric optional:
```python
class RunRequest(BaseModel):
    dataset_id: str
    candidate_ids: list[str]
    rubric: Rubric | None = None
    brief: ProofBrief
```
- In `create_run`, after the dataset + candidates are resolved:
```python
        rubric = body.rubric or default_rubric_for(dataset)
        now = ...
        try:
            report = run_proof(
                run_id=...,
                created_at=now,
                brief=body.brief,
                dataset=dataset,
                candidates=candidates,
                rubric=rubric,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
```
- In `create_run_stream`, resolve + validate up front (before the generator), then thread `rubric` through `iter_matrix`, `ProofRun`, `config_hash`, and the report:
```python
    rubric = body.rubric or default_rubric_for(dataset)
    if rubric.kind == "judge":
        try:
            build_judge(rubric)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
```
  Replace every `body.rubric` inside `events()` with `rubric`, and build the report with the cost summary:
```python
        report = ProofReport(
            run=run,
            leaderboard=build_leaderboard(candidates, rows),
            results=rows,
            cost_summary=build_cost_summary(rows),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_api.py -k "rubric or judge_without_model or cost_summary" -v` → PASS.
Run: `uv run pytest -q` → all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/server/routes.py tests/test_api.py
git commit -m "feat(api): Auto rubric default (keypoint-aware), stream cost summary, judge -> 422"
```

---

### Task 8: Frontend schemas + optional rubric in RunRequest

**Files:**
- Modify: `web/src/lib/api.ts`
- Modify: `web/src/test/fixtures.ts`
- Test: `web/src/lib/api.test.ts` (append; create if absent)

**Interfaces:**
- Produces: `rubricSchema` accepts `keypoint`/`judge` + optional judge fields; `resultRowSchema` carries judge cost; `proofReportSchema` carries `cost_summary`; `RunRequest.rubric?` optional; a `scoredByLabel(rubric)` helper.

- [ ] **Step 1: Write the failing test**

```typescript
// web/src/lib/api.test.ts
import { describe, it, expect } from "vitest";
import { rubricSchema, proofReportSchema, scoredByLabel } from "./api";
import { SAMPLE_REPORT } from "../test/fixtures";

describe("scoring schemas", () => {
  it("rubric accepts keypoint and judge kinds", () => {
    expect(rubricSchema.parse({ kind: "keypoint", threshold: 0.8, case_sensitive: false }).kind).toBe("keypoint");
    expect(rubricSchema.parse({ kind: "judge", threshold: 0.8, case_sensitive: false, judge_provider_id: "mock_judge", judge_model: null }).judge_provider_id).toBe("mock_judge");
  });

  it("report carries a cost_summary", () => {
    const r = proofReportSchema.parse(SAMPLE_REPORT);
    expect(r.cost_summary.total_cost_usd).toBeGreaterThanOrEqual(0);
  });

  it("scoredByLabel maps kinds", () => {
    expect(scoredByLabel({ kind: "keypoint", threshold: 0.8, case_sensitive: false })).toBe("Keypoint coverage");
    expect(scoredByLabel({ kind: "judge", threshold: 0.8, case_sensitive: false, judge_model: "claude-haiku-4-5", judge_provider_id: "anthropic" })).toContain("claude-haiku-4-5");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test -- api.test` → FAIL (`scoredByLabel` undefined; `cost_summary` missing on `SAMPLE_REPORT`/schema).

- [ ] **Step 3: Write minimal implementation**

In `web/src/lib/api.ts`:
- Extend the rubric schema (lines 67–71):
```typescript
export const rubricSchema = z.object({
  kind: z.enum(["exact", "contains", "similarity", "keypoint", "judge"]),
  threshold: z.number(),
  case_sensitive: z.boolean(),
  judge_provider_id: z.string().nullable().optional(),
  judge_model: z.string().nullable().optional(),
});
```
- Add to `resultRowSchema` (after `estimated_cost_usd`):
```typescript
  judge_cost_usd: z.number().default(0),
  judge_latency_ms: z.number().default(0),
```
- Add a cost-summary schema and extend the report (near `proofReportSchema`):
```typescript
export const runCostSummarySchema = z.object({
  candidate_cost_usd: z.number(),
  judge_cost_usd: z.number(),
  total_cost_usd: z.number(),
});
export const proofReportSchema = z.object({
  run: proofRunSchema,
  leaderboard: z.array(leaderboardEntrySchema),
  results: z.array(resultRowSchema),
  cost_summary: runCostSummarySchema,
});
```
- Make the run-request rubric optional (interface lines 255–259):
```typescript
export interface RunRequest {
  dataset_id: string;
  candidate_ids: string[];
  rubric?: z.infer<typeof rubricSchema> | null;
  brief: ProofBrief;
}
```
- Add the label helper (mirrors the backend `_scored_by`):
```typescript
export function scoredByLabel(rubric: z.infer<typeof rubricSchema>): string {
  if (rubric.kind === "keypoint") return "Keypoint coverage";
  if (rubric.kind === "judge") return `LLM judge · ${rubric.judge_model ?? rubric.judge_provider_id ?? "model"}`;
  return { similarity: "Similarity", exact: "Exact match", contains: "Contains" }[rubric.kind] ?? rubric.kind;
}
```
- In `web/src/test/fixtures.ts`: add `judge_cost_usd: 0, judge_latency_ms: 0` to each result row, and `cost_summary: { candidate_cost_usd: 0, judge_cost_usd: 0, total_cost_usd: 0 }` to `SAMPLE_REPORT` and `NO_WINNER_REPORT`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --dir web test -- api.test` → PASS.
Run: `pnpm --dir web test` → all PASS (fixtures now satisfy the schema).

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/api.ts web/src/lib/api.test.ts web/src/test/fixtures.ts
git commit -m "feat(web): rubric/judge + cost_summary schemas, optional rubric, scoredByLabel"
```

---

### Task 9: ScoringMethod control + judge-model picker

**Files:**
- Create: `web/src/features/proof/ScoringMethod.tsx`
- Test: `web/src/features/proof/ScoringMethod.test.tsx`

**Interfaces:**
- Consumes: `getSelection` (existing), `KeyEntry` (existing, props `{providerId, providerLabel, keyName}`), `SelectionPanel`/`SelectionGroup` types, `CLOUD_KEY_NAMES` (lift the literal from `CandidatePicker.tsx` into a shared `selectionMeta.ts` and import in both — DRY).
- Produces: `ScoringMethod({ value, onChange })` where `value: Rubric | null` (null = Auto) and `onChange(next: Rubric | null)`. Renders a method selector (Auto · Keypoint · Similarity · LLM judge). When **LLM judge**: a judge-model list built from `getSelection()` plus a keyless **"Mock judge"** option (`judge_provider_id: "mock_judge"`); selecting a model emits `{kind:"judge", threshold:0.8, case_sensitive:false, judge_provider_id, judge_model}`; an unavailable cloud judge shows inline `KeyEntry` (reusing the `CandidatePicker` pattern at lines 100–109).

- [ ] **Step 1: Write the failing test**

```tsx
// web/src/features/proof/ScoringMethod.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ScoringMethod } from "./ScoringMethod";

vi.mock("../../lib/api", async (orig) => ({
  ...(await orig<typeof import("../../lib/api")>()),
  getSelection: vi.fn(async () => ({ groups: [], mocks: [] })),
}));

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

describe("ScoringMethod", () => {
  it("defaults to Auto and emits null", () => {
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} />));
    expect(screen.getByText(/Auto/i)).toBeInTheDocument();
  });

  it("emits a keypoint rubric when Keypoint is chosen", () => {
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} />));
    fireEvent.click(screen.getByRole("button", { name: /Keypoint/i }));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ kind: "keypoint" }));
  });

  it("offers a keyless Mock judge when LLM judge is chosen", () => {
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} />));
    fireEvent.click(screen.getByRole("button", { name: /LLM judge/i }));
    expect(screen.getByText(/Mock judge/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test -- ScoringMethod` → FAIL (module missing).

- [ ] **Step 3: Write minimal implementation**

Create `web/src/features/proof/ScoringMethod.tsx`. Sketch (follow `CandidatePicker.tsx` styling + Tailwind v4 parenthesis vars):
- A row of method buttons: `Auto | Keypoint | Similarity | LLM judge`. Auto → `onChange(null)`. Keypoint/Similarity → `onChange({ kind, threshold: 0.8, case_sensitive: false })`.
- When `LLM judge` active: `useQuery({ queryKey: ["selection"], queryFn: getSelection })`; render a list = `[{ provider_id: "mock_judge", label: "Mock judge", available: true, models: [] }, ...panel.groups]`. For each available judge option, a clickable chip that emits `{ kind: "judge", threshold: 0.8, case_sensitive: false, judge_provider_id, judge_model }` (judge_model = chosen model id or null for mock_judge). For an unavailable cloud group, render `<KeyEntry providerId={g.provider_id} providerLabel={g.label} keyName={CLOUD_KEY_NAMES[g.provider_id]} />` exactly as `CandidatePicker` does.
- Move `CLOUD_KEY_NAMES` to `web/src/features/proof/selectionMeta.ts` and import it in both `CandidatePicker.tsx` and `ScoringMethod.tsx` (no duplicated literal).

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --dir web test -- ScoringMethod` → PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/proof/ScoringMethod.tsx web/src/features/proof/ScoringMethod.test.tsx web/src/features/proof/selectionMeta.ts web/src/features/proof/CandidatePicker.tsx
git commit -m "feat(web): ScoringMethod control with keyless mock-judge + cloud judge KeyEntry"
```

---

### Task 10: Cockpit wiring + Scored-by / Run-cost display

**Files:**
- Modify: `web/src/features/proof/ProofCockpit.tsx`
- Modify: `web/src/features/proof/ReceiptsView.tsx`
- Test: `web/src/features/proof/DecisionSummary.test.tsx` (append), `web/src/features/proof/ProofCockpit.test.tsx` (append)

**Interfaces:**
- Consumes: `ScoringMethod`, `scoredByLabel`, `RunCostSummary` type.
- Produces: `ProofCockpit` holds `rubric` state (`Rubric | null`, default `null`=Auto), renders `<ScoringMethod>` in the run config, and includes `rubric` in the `RunRequest` (omit when null). `DecisionSummary` accepts optional `scoredBy?: string` and `cost?: RunCostSummary` and renders a calm "Scored by …" + "Run cost: candidate $X · judge $Y · total $Z" line. `ReceiptsView` shows "Scored by …" in the winner summary.

- [ ] **Step 1: Write the failing test**

```tsx
// web/src/features/proof/DecisionSummary.test.tsx (append)
it("shows the scoring method and run cost when provided", () => {
  render(
    <DecisionSummary
      brief={SAMPLE_REPORT.run.brief}
      leaderboard={SAMPLE_REPORT.leaderboard}
      scoredBy="Keypoint coverage"
      cost={{ candidate_cost_usd: 0.01, judge_cost_usd: 0.002, total_cost_usd: 0.012 }}
    />,
  );
  expect(screen.getByText(/Scored by/i)).toBeInTheDocument();
  expect(screen.getByText(/Keypoint coverage/i)).toBeInTheDocument();
  expect(screen.getByText(/Run cost/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test -- DecisionSummary` → FAIL (props not rendered).

- [ ] **Step 3: Write minimal implementation**

- `DecisionSummary` (in `ProofCockpit.tsx`, ~line 214): extend props to `{ brief, leaderboard, scoredBy?, cost? }`; after the winner/no-winner block, when `scoredBy` is set render:
```tsx
{scoredBy && (
  <p className="mt-1 text-sm text-(--color-ink-faint)">
    Scored by {scoredBy}
    {cost && ` · Run cost: candidate $${cost.candidate_cost_usd.toFixed(4)} · judge $${cost.judge_cost_usd.toFixed(4)} · total $${cost.total_cost_usd.toFixed(4)}`}
  </p>
)}
```
- `ProofCockpit`: add `const [rubric, setRubric] = useState<Rubric | null>(null);`; render `<ScoringMethod value={rubric} onChange={setRubric} />` near the candidate picker; include `...(rubric ? { rubric } : {})` in the `runMutation.mutate({...})` body (lines 171–177); when rendering `<DecisionSummary>` from a finished `report`, pass `scoredBy={scoredByLabel(report.run.rubric)}` and `cost={report.cost_summary}`.
- `ReceiptsView` (~lines 73–82): in the winner summary add `<span>Scored by {scoredByLabel(report.run.rubric)}</span>` (and optionally the total cost).

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --dir web test` → all PASS.
Run: `pnpm --dir web build` → clean (tsc + vite).

- [ ] **Step 5: Commit**

```bash
git add web/src/features/proof/ProofCockpit.tsx web/src/features/proof/ReceiptsView.tsx web/src/features/proof/DecisionSummary.test.tsx web/src/features/proof/ProofCockpit.test.tsx
git commit -m "feat(web): scoring-method control wired into runs; Scored-by + Run-cost display"
```

---

### Task 11: e2e — keyless keypoint run proves the fix

**Files:**
- Modify: `e2e/playwright/proof.spec.ts`

**Interfaces:**
- Consumes: the running app with the seeded keypointed demo dataset.
- Produces: an e2e assertion that a keyless run scores via keypoint coverage and shows "Scored by: Keypoint coverage"; `mock_good` still 100% (5/5).

- [ ] **Step 1: Write the failing assertion (extend the happy-path test)**

In `e2e/playwright/proof.spec.ts`, after the leaderboard assertions (~line 25), add:
```typescript
  await expect(page.getByText(/Scored by/i)).toContainText(/Keypoint coverage/i);
```

- [ ] **Step 2: Rebuild the embed + run e2e to verify**

Run: `bash scripts/build.sh && pnpm --dir web e2e`
Expected: FIRST run may FAIL if the cockpit isn't passing `scoredBy` yet — but after Task 10 it PASSES. Confirm `100% (5/5)` + "Recommended" still hold (Finding-1 + keyless default intact).

- [ ] **Step 3: Commit**

```bash
git add e2e/playwright/proof.spec.ts
git commit -m "test(e2e): keyless run scores by keypoint coverage (Finding 2 proof)"
```

---

### Task 12: Full verification, reviews, docs

**Files:**
- Modify: `CHANGELOG.md`, `HANDOFF.md`, `docs/worklog/2026-06-21-meaning-aware-scoring.md` (create)

- [ ] **Step 1: Full gate**

Run each; all must pass:
```bash
uv run pytest -q
uv run ruff check src tests
pnpm --dir web test
pnpm --dir web build
bash scripts/build.sh && pnpm --dir web e2e
```

- [ ] **Step 2: Receipt + security reviews**

Invoke the `receipt-quality-review` skill (generate a keypoint receipt AND a `mock_judge` receipt; confirm "Scored by" + "Run cost" render in MD/HTML/JSON, no secrets). Invoke the `security-secrets-review` skill (judge key never in receipt/log/response; `.env.local` path unchanged; `/api/credentials` still the only key-write path).

- [ ] **Step 3: Live browser check**

Rebuild embed; `orionfold up` on a PROVABLY-FREE port (assert listener PID is yours). Verify: keyless run shows "Scored by: Keypoint coverage" + a Run cost line; switching ScoringMethod → LLM judge → "Mock judge" runs keylessly and the receipt shows "LLM judge · mock_judge" + a non-zero judge cost; a reformatted-but-correct output passes under keypoint where it failed under similarity.

- [ ] **Step 4: Docs + worklog + handoff**

Update `CHANGELOG.md [Unreleased]` (meaning-aware scoring: keypoint default + LLM judge + run cost; RECEIPT_VERSION 5). Write `docs/worklog/2026-06-21-meaning-aware-scoring.md` (Summary · Verification · Product impact · Risks · Next: #6 prompt-variant candidates). Overwrite `HANDOFF.md` (Finding 2 SHIPPED; next = #6 prompt-variant candidates + catalog price/source pass; note RECEIPT_VERSION 5, config_hash intentionally changed, judge cost tracked at run level).

- [ ] **Step 5: Commit**

```bash
git add CHANGELOG.md HANDOFF.md docs/worklog/2026-06-21-meaning-aware-scoring.md
git commit -m "docs: meaning-aware scoring worklog + changelog + handoff (Finding 2 shipped)"
```
