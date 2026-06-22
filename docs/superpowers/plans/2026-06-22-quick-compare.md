# Quick-Compare → Proof Receipt Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 1-prompt × 2-candidate "Quick Compare" mode to the Proof Run page — generate two outputs on a shared prompt, show them head-to-head with objective bars (latency/cost/tokens), let the operator pick the winner, and save a clearly-labeled un-scored quick-check Proof Receipt with a promote-to-full CTA.

**Architecture:** Reuse the existing matrix engine + receipt exporter. The engine already takes a `Dataset` *object*; only the route layer forces a stored dataset, so quick runs pass an inline `examples` list and the route builds an ephemeral `Dataset(id="quick-compare")`. A new unscored rubric kind `{kind:"none"}` makes the engine skip scoring (`score=None`, `passed=None`). The receipt gains `mode` + `chosen_winner` (RECEIPT_VERSION 7→8); a quick branch renders objective columns and the human pick. The pick is recorded via `PATCH /api/runs/{id}/winner`.

**Tech Stack:** Python 3.12 · FastAPI · Pydantic · pytest · SQLite (stdlib) · React · TypeScript · Zod · TanStack Query · Vitest · Playwright.

## Global Constraints

- `config_hash` algorithm is UNCHANGED. `mode` and `chosen_winner` live on `ProofRun` but `config_hash()` only hashes dataset/candidates/rubric — never add them to the hash payload. A quick run's hash MUST be identical before and after a pick is recorded.
- Migrations stay append-only; this feature adds NO migration (`mode`/`chosen_winner` live inside the JSON `report` blob in the `runs` table).
- Receipts never contain secrets/keys (`.claude/rules/receipts.md`). Bump `RECEIPT_VERSION` on the schema change (7 → 8).
- Accent/status token split (`.claude/rules` / DS skin): objective bars use status/neutral tokens, NEVER `--color-accent`. Green `--color-ok` stays reserved for PASS — a quick check has no PASS, so it uses no green.
- Mocks are bare ids `mock_good`/`mock_bad`; they appear in the picker only when Sandbox is on. The e2e enables Sandbox and runs keyless.
- Tailwind v4 CSS-var syntax: `bg-(--color-x)`, not `bg-[--color-x]`.
- Commit after each task (solo project commits directly to `main`; no feature branch). End commit messages with the `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` trailer.
- Verify gates per task: backend `uv run pytest -q`; frontend `pnpm --dir web test --run` and `pnpm --dir web exec tsc --noEmit`.

---

## File Structure

**Backend**
- Modify `src/orionfold/domain/models.py` — add `"none"` to `RubricKind`; widen `ResultRow.score`→`float | None`, `passed`→`bool | None`; add `ResultRow.input_tokens`/`output_tokens`; add `ProofRun.mode` + `ProofRun.chosen_winner`.
- Modify `src/orionfold/proof/engine.py` — `iter_matrix` `none`-kind branch + propagate tokens.
- Modify `src/orionfold/proof/leaderboard.py` — None-safe `avg_score`.
- Modify `src/orionfold/server/routes.py` — `RunRequest.examples`/`mode`; ephemeral-dataset branch in `create_run` + `create_run_stream`; `WinnerRequest` + `PATCH /runs/{id}/winner`.
- Modify `src/orionfold/storage/repository.py` — `list_runs` filters quick runs without a pick.
- Modify `src/orionfold/receipts/export.py` — `RECEIPT_VERSION = 8`; `build_receipt` quick branch; `to_markdown` + `to_html` quick branches.

**Frontend**
- Modify `web/src/lib/api.ts` — schema/type updates + `patchWinner`.
- Create `web/src/features/proof/quickCompareFormat.ts` — pure objective-bar + label helpers.
- Modify `web/src/features/proof/RunSetup.tsx` — third "Quick" toggle + quick lane.
- Modify `web/src/features/proof/ProofCockpit.tsx` — quick state, run branch, Decide-view branch.
- Create `web/src/features/proof/QuickCompare.tsx` — head-to-head Decide view.

**Tests**
- `tests/test_engine.py`, `tests/test_leaderboard.py`, `tests/test_routes.py`, `tests/test_export.py` (extend existing files; match current naming).
- `web/src/features/proof/quickCompareFormat.test.ts`, `web/src/features/proof/RunSetup.test.tsx`, `web/src/features/proof/QuickCompare.test.tsx`.
- `e2e/playwright/proof.spec.ts` (extend).

---

## Task 1: Unscored rubric kind + ResultRow widening + token capture

**Files:**
- Modify: `src/orionfold/domain/models.py:15` (RubricKind), `:85-100` (ResultRow)
- Modify: `src/orionfold/proof/engine.py:74-114` (iter_matrix)
- Modify: `src/orionfold/proof/leaderboard.py:32` (avg_score)
- Test: `tests/test_engine.py`, `tests/test_leaderboard.py`

**Interfaces:**
- Produces: `Rubric(kind="none")` → `iter_matrix` yields `ResultRow` with `score=None`, `passed=None`, `input_tokens`/`output_tokens` set from the provider result. `ResultRow.score: float | None`, `ResultRow.passed: bool | None`, `ResultRow.input_tokens: int = 0`, `ResultRow.output_tokens: int = 0`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_engine.py` add:

```python
from orionfold.domain.models import Dataset, Example, Rubric
from orionfold.proof.engine import run_matrix
from orionfold.providers.registry import build_candidates


def test_none_rubric_skips_scoring_and_captures_tokens():
    dataset = Dataset(
        id="quick-compare",
        name="Quick Compare",
        examples=[Example(input_text="Summarize: revenue grew 22%.", expected_text="")],
    )
    candidates = build_candidates(["mock_good", "mock_bad"])
    rows = run_matrix(dataset, candidates, Rubric(kind="none"))

    assert len(rows) == 2
    for r in rows:
        assert r.score is None
        assert r.passed is None
        # mock providers report token counts; the row must carry them for the bars
        assert r.output_tokens >= 0
        assert r.input_tokens >= 0
```

In `tests/test_leaderboard.py` add:

```python
from orionfold.domain.models import Dataset, Example, Rubric
from orionfold.proof.engine import run_matrix
from orionfold.proof.leaderboard import build_leaderboard
from orionfold.providers.registry import build_candidates


def test_leaderboard_is_none_safe_for_unscored_rows():
    dataset = Dataset(
        id="quick-compare", name="Quick Compare",
        examples=[Example(input_text="x", expected_text="")],
    )
    candidates = build_candidates(["mock_good", "mock_bad"])
    rows = run_matrix(dataset, candidates, Rubric(kind="none"))
    entries = build_leaderboard(candidates, rows)
    assert len(entries) == 2
    for e in entries:
        assert e.avg_score == 0.0       # no score → treated as 0.0 aggregate
        assert e.pass_count == 0
        assert e.recommended is False   # never crown an unscored candidate
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_engine.py::test_none_rubric_skips_scoring_and_captures_tokens tests/test_leaderboard.py::test_leaderboard_is_none_safe_for_unscored_rows -v`
Expected: FAIL — `Rubric` rejects `kind="none"` (ValidationError) / `ResultRow` has no `input_tokens`.

- [ ] **Step 3: Widen the models**

In `src/orionfold/domain/models.py`, change line 15:

```python
RubricKind = Literal["exact", "contains", "similarity", "keypoint", "judge", "none"]
```

In the same file, update the `ResultRow` fields (lines ~93-94 and add two new fields after `output_text`):

```python
class ResultRow(BaseModel):
    """One cell of the run matrix: a candidate's attempt at one example.

    ``score``/``passed`` are ``None`` for an unscored (quick-compare) run — an honest
    absence, never a placeholder zero.
    """

    candidate_id: str
    example_index: int
    input_text: str
    expected_text: str
    output_text: str
    score: float | None
    passed: bool | None
    latency_ms: int
    estimated_cost_usd: float
    input_tokens: int = 0
    output_tokens: int = 0
    privacy: Privacy
    error: str | None = None
    judge_cost_usd: float = 0.0  # cost of the judge call for this cell (0 for non-judge)
    judge_latency_ms: int = 0  # judge latency for this cell (0 for non-judge)
```

- [ ] **Step 4: Add the `none` branch + token capture in `iter_matrix`**

In `src/orionfold/proof/engine.py`, replace the scoring `if/elif/else` chain and the `yield` (lines 79-114) so the `none` kind short-circuits and every row carries tokens:

```python
            judge_cost, judge_latency, judge_error = 0.0, 0, None
            score_value: float | None
            did_pass: bool | None
            if rubric.kind == "none":
                # Unscored quick-compare: capture output + metrics, never a score.
                score_value, did_pass = None, None
            elif result.error is not None:
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
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                judge_cost_usd=judge_cost,
                judge_latency_ms=judge_latency,
                privacy=result.privacy,
                error=result.error if result.error is not None else judge_error,
            )
```

- [ ] **Step 5: Make `build_leaderboard` None-safe**

In `src/orionfold/proof/leaderboard.py`, change line 32 (avg_score) so `None` scores aggregate to 0:

```python
        avg_score = sum((r.score or 0.0) for r in rows) / total if total else 0.0
```

(`pass_count = sum(1 for r in rows if r.passed)` already treats `None` as falsy, so no change there.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_engine.py tests/test_leaderboard.py -q`
Expected: PASS (including the two new tests; pre-existing engine/leaderboard tests still green).

- [ ] **Step 7: Full backend run to catch ripple from the type widening**

Run: `uv run pytest -q`
Expected: PASS. If any pre-existing test asserts `row.score`/`row.passed` are non-None for *scored* runs, those still hold (only `kind="none"` yields None). Fix any spot that does `f"{row.score:.2f}"` on a possibly-None value only if a test surfaces it — none should in scored paths.

- [ ] **Step 8: Commit**

```bash
git add src/orionfold/domain/models.py src/orionfold/proof/engine.py src/orionfold/proof/leaderboard.py tests/test_engine.py tests/test_leaderboard.py
git commit -m "feat(engine): unscored 'none' rubric + token capture on ResultRow

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `mode` + `chosen_winner` on ProofRun (config_hash unaffected)

**Files:**
- Modify: `src/orionfold/domain/models.py:132-143` (ProofRun)
- Test: `tests/test_engine.py` (config_hash invariance)

**Interfaces:**
- Produces: `ProofRun.mode: Literal["full","quick"] = "full"`, `ProofRun.chosen_winner: str | None = None`. `config_hash()` is unchanged and does not read either field.

- [ ] **Step 1: Write the failing test**

In `tests/test_engine.py` add:

```python
from orionfold.domain.models import Candidate
from orionfold.proof.engine import config_hash


def test_config_hash_excludes_mode_and_chosen_winner():
    dataset = Dataset(id="quick-compare", name="Quick Compare",
                      examples=[Example(input_text="x", expected_text="")])
    candidates = build_candidates(["mock_good", "mock_bad"])
    rubric = Rubric(kind="none")
    # The hash is computed purely from dataset/candidates/rubric; the new ProofRun
    # provenance fields must not be part of it.
    h = config_hash(dataset, candidates, rubric)
    assert isinstance(h, str) and len(h) == 12
    # Building a ProofRun with a pick set must not change the run's config_hash value.
    from orionfold.domain.models import ProofBrief, ProofRun
    run = ProofRun(
        id="run_x", brief=ProofBrief(task_name="t", decision_question="q"),
        dataset_id=dataset.id, dataset_name=dataset.name, rubric=rubric,
        candidates=candidates, config_hash=h, created_at="2026-06-22T00:00:00Z",
        mode="quick", chosen_winner="mock_good",
    )
    assert run.config_hash == h
    assert run.mode == "quick"
    assert run.chosen_winner == "mock_good"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_engine.py::test_config_hash_excludes_mode_and_chosen_winner -v`
Expected: FAIL — `ProofRun` has no `mode`/`chosen_winner`.

- [ ] **Step 3: Add the fields**

In `src/orionfold/domain/models.py`, extend `ProofRun` (after `status`):

```python
class ProofRun(BaseModel):
    """A single matrix run: the brief, dataset, rubric, candidates, and provenance."""

    id: str
    brief: ProofBrief
    dataset_id: str
    dataset_name: str
    rubric: Rubric
    candidates: list[Candidate]
    config_hash: str
    created_at: str
    status: Literal["complete"] = "complete"
    # Quick-compare provenance. Presentation only — EXCLUDED from config_hash so a quick run's
    # hash is identical before and after a pick is recorded.
    mode: Literal["full", "quick"] = "full"
    chosen_winner: str | None = None  # a candidate_id, the literal "tie", or None (no pick yet)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_engine.py::test_config_hash_excludes_mode_and_chosen_winner -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/domain/models.py tests/test_engine.py
git commit -m "feat(model): ProofRun.mode + chosen_winner (excluded from config_hash)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Inline-examples run path (ephemeral dataset, quick mode)

**Files:**
- Modify: `src/orionfold/server/routes.py:90-96` (RunRequest), `:377-411` (create_run), `:419-497` (create_run_stream)
- Test: `tests/test_routes.py`

**Interfaces:**
- Consumes: `Rubric(kind="none")` (Task 1), `ProofRun.mode` (Task 2).
- Produces: `POST /api/runs` and `POST /api/runs/stream` accept `examples: list[Example] | None` and `mode: Literal["full","quick"]`. When `examples` is set, the run uses `Dataset(id="quick-compare", name="Quick Compare", examples=...)`, is persisted, and `report.run.mode` reflects `body.mode`. No dataset row is written.

- [ ] **Step 1: Write the failing test**

In `tests/test_routes.py` add (use the existing app/client fixture in that file — match the established fixture name, e.g. `client`):

```python
def test_quick_run_uses_inline_examples_without_a_dataset_row(client):
    body = {
        "examples": [{"input_text": "Summarize: revenue grew 22%.", "expected_text": ""}],
        "candidate_ids": ["mock_good", "mock_bad"],
        "rubric": {"kind": "none", "threshold": 0, "case_sensitive": False},
        "mode": "quick",
        "brief": {"task_name": "Quick check", "decision_question": "Which reads better?"},
    }
    res = client.post("/api/runs", json=body)
    assert res.status_code == 200, res.text
    report = res.json()
    assert report["run"]["mode"] == "quick"
    assert report["run"]["dataset_id"] == "quick-compare"
    assert report["run"]["chosen_winner"] is None
    assert len(report["results"]) == 2
    assert all(r["score"] is None for r in report["results"])
    # No dataset row was created for the ad-hoc prompt.
    ds = client.get("/api/datasets").json()
    assert all(d["id"] != "quick-compare" for d in ds)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_routes.py::test_quick_run_uses_inline_examples_without_a_dataset_row -v`
Expected: FAIL — `RunRequest` rejects `examples`/`mode`; the run 404s on the missing dataset.

- [ ] **Step 3: Extend `RunRequest`**

In `src/orionfold/server/routes.py`, update the model (line 90-96). `Example` is already imported on line 34:

```python
class RunRequest(BaseModel):
    dataset_id: str = ""  # ignored when `examples` is provided (quick-compare)
    candidate_ids: list[str]
    rubric: Rubric | None = None
    brief: ProofBrief
    prompt_variants: list[PromptVariant] | None = None
    examples: list[Example] | None = None  # inline ad-hoc examples (quick-compare); no dataset row
    mode: Literal["full", "quick"] = "full"
```

Add `Literal` to the typing import at the top of the file:

```python
from typing import Literal
```

- [ ] **Step 4: Add a shared resolver + branch both handlers**

In `src/orionfold/server/routes.py`, add a helper above `create_run` (after `_resolve_candidates`):

```python
def _resolve_dataset(conn: sqlite3.Connection, body: RunRequest) -> Dataset:
    """The dataset under test: an ephemeral one for quick-compare, else the stored row."""
    if body.examples:
        return Dataset(id="quick-compare", name="Quick Compare", examples=body.examples)
    dataset = get_dataset(conn, body.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Unknown dataset")
    return dataset
```

In `create_run`, replace lines 381-383 (the `get_dataset` + None check) with:

```python
        dataset = _resolve_dataset(conn, body)
```

and pass `mode` into `run_proof` — but `run_proof` builds the `ProofRun`, so instead set the mode on the returned report's run before saving (keeps `run_proof` signature stable):

```python
            report.run.mode = body.mode
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        save_report(conn, report)
        return report
```

(Place `report.run.mode = body.mode` immediately after the `report = run_proof(...)` assignment, inside the `try`, before the `except`.)

In `create_run_stream`, replace the dataset lookup (lines 432-437) with:

```python
    conn = _conn(request)
    try:
        dataset = _resolve_dataset(conn, body)
    finally:
        conn.close()
```

and set the mode when the `ProofRun` is constructed inside `events()` (line 476-485):

```python
        run = ProofRun(
            id=f"run_{uuid.uuid4().hex[:12]}",
            brief=body.brief,
            dataset_id=dataset.id,
            dataset_name=dataset.name,
            rubric=rubric,
            candidates=candidates,
            config_hash=config_hash(dataset, candidates, rubric),
            created_at=now,
            mode=body.mode,
        )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_routes.py::test_quick_run_uses_inline_examples_without_a_dataset_row -q`
Expected: PASS.

- [ ] **Step 6: Run the full routes suite (no regression on stored-dataset runs)**

Run: `uv run pytest tests/test_routes.py -q`
Expected: PASS — `dataset_id` still works for full runs (the empty-string default only applies when `examples` is set).

- [ ] **Step 7: Commit**

```bash
git add src/orionfold/server/routes.py tests/test_routes.py
git commit -m "feat(api): inline-examples quick run path (ephemeral dataset, mode flag)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: `PATCH /api/runs/{id}/winner` records the human pick

**Files:**
- Modify: `src/orionfold/server/routes.py` (new model + route, near `get_single_run` ~516)
- Test: `tests/test_routes.py`

**Interfaces:**
- Consumes: `get_report`/`save_report` (repository), quick run from Task 3.
- Produces: `PATCH /api/runs/{run_id}/winner` body `{"chosen_winner": str}` → sets `report.run.chosen_winner`, re-saves, returns the updated `ProofReport`. 400 on unknown winner / non-quick run; 404 on unknown run.

- [ ] **Step 1: Write the failing test**

In `tests/test_routes.py` add:

```python
def _make_quick_run(client) -> str:
    body = {
        "examples": [{"input_text": "x", "expected_text": ""}],
        "candidate_ids": ["mock_good", "mock_bad"],
        "rubric": {"kind": "none", "threshold": 0, "case_sensitive": False},
        "mode": "quick",
        "brief": {"task_name": "Quick check", "decision_question": "q"},
    }
    return client.post("/api/runs", json=body).json()["run"]["id"]


def test_patch_winner_records_pick_and_keeps_config_hash(client):
    run_id = _make_quick_run(client)
    before = client.get(f"/api/runs/{run_id}").json()
    res = client.patch(f"/api/runs/{run_id}/winner", json={"chosen_winner": "mock_good"})
    assert res.status_code == 200, res.text
    after = res.json()
    assert after["run"]["chosen_winner"] == "mock_good"
    assert after["run"]["config_hash"] == before["run"]["config_hash"]  # invariant
    # "tie" is a legitimate pick.
    assert client.patch(f"/api/runs/{run_id}/winner", json={"chosen_winner": "tie"}).status_code == 200


def test_patch_winner_rejects_unknown_candidate(client):
    run_id = _make_quick_run(client)
    res = client.patch(f"/api/runs/{run_id}/winner", json={"chosen_winner": "nope"})
    assert res.status_code == 400


def test_patch_winner_404_for_unknown_run(client):
    res = client.patch("/api/runs/run_missing/winner", json={"chosen_winner": "tie"})
    assert res.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_routes.py -k patch_winner -v`
Expected: FAIL — route does not exist (404/405).

- [ ] **Step 3: Add the model + route**

In `src/orionfold/server/routes.py`, add a request model near the other `BaseModel`s (after `RunRequest`):

```python
class WinnerRequest(BaseModel):
    chosen_winner: str  # a candidate_id from the run, or the literal "tie"
```

Add the route after `get_single_run` (~525):

```python
@router.patch("/runs/{run_id}/winner")
def set_winner(request: Request, run_id: str, body: WinnerRequest) -> ProofReport:
    """Record the operator's head-to-head pick on a quick-compare run."""
    conn = _conn(request)
    try:
        report = get_report(conn, run_id)
        if report is None:
            raise HTTPException(status_code=404, detail="Unknown run")
        if report.run.mode != "quick":
            raise HTTPException(status_code=400, detail="Only quick-compare runs take a pick.")
        valid = {c.id for c in report.run.candidates} | {"tie"}
        if body.chosen_winner not in valid:
            raise HTTPException(status_code=400, detail="Pick must be one of the run's candidates.")
        report.run.chosen_winner = body.chosen_winner
        save_report(conn, report)
        return report
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_routes.py -k patch_winner -q`
Expected: PASS (all three).

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/server/routes.py tests/test_routes.py
git commit -m "feat(api): PATCH /runs/{id}/winner records the quick-compare pick

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Hide un-picked quick runs from the Receipts list

**Files:**
- Modify: `src/orionfold/storage/repository.py:204-207` (list_runs)
- Test: `tests/test_routes.py` (via `GET /api/runs`)

**Interfaces:**
- Produces: `list_runs` omits reports where `run.mode == "quick" and run.chosen_winner is None`. Full runs and picked quick runs are unaffected.

- [ ] **Step 1: Write the failing test**

In `tests/test_routes.py` add:

```python
def test_unpicked_quick_runs_are_hidden_from_the_list(client):
    run_id = _make_quick_run(client)
    listed = client.get("/api/runs").json()
    assert all(r["run"]["id"] != run_id for r in listed)  # no pick yet → hidden
    client.patch(f"/api/runs/{run_id}/winner", json={"chosen_winner": "tie"})
    listed = client.get("/api/runs").json()
    assert any(r["run"]["id"] == run_id for r in listed)   # picked → visible
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_routes.py::test_unpicked_quick_runs_are_hidden_from_the_list -v`
Expected: FAIL — the un-picked run is listed.

- [ ] **Step 3: Filter in `list_runs`**

In `src/orionfold/storage/repository.py`, replace `list_runs` (lines 204-207):

```python
def list_runs(conn: sqlite3.Connection) -> list[ProofReport]:
    """Most recent first. Un-picked quick-compare runs are hidden — the pick is the proof, so a
    quick run without one is an abandoned draft, not a receipt."""
    rows = conn.execute("SELECT report FROM runs ORDER BY created_at DESC").fetchall()
    reports = [ProofReport.model_validate_json(r["report"]) for r in rows]
    return [
        rep for rep in reports
        if not (rep.run.mode == "quick" and rep.run.chosen_winner is None)
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_routes.py::test_unpicked_quick_runs_are_hidden_from_the_list -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/storage/repository.py tests/test_routes.py
git commit -m "feat(storage): hide un-picked quick runs from the receipts list

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: `build_receipt` quick branch + RECEIPT_VERSION 8

**Files:**
- Modify: `src/orionfold/receipts/export.py:27` (version), `:49-51` (failures), `:105-156` (build_receipt)
- Test: `tests/test_export.py`

**Interfaces:**
- Consumes: `ProofRun.mode`/`chosen_winner`, unscored `ResultRow`.
- Produces: `build_receipt(report)` returns a dict with `receipt_version == 8` always; for quick runs it additionally carries `mode == "quick"`, `chosen_winner`, a pick-based `verdict`/`recommendation`, `failure_cases == []`, and a `quick_note`. Objective data is read from `leaderboard` entries (latency/cost) + `results` (tokens).

- [ ] **Step 1: Write the failing test**

In `tests/test_export.py` add:

```python
from orionfold.domain.models import Dataset, Example, ProofBrief, Rubric
from orionfold.proof.engine import run_proof
from orionfold.providers.registry import build_candidates
from orionfold.receipts.export import RECEIPT_VERSION, build_receipt


def _quick_report(chosen="mock_good"):
    dataset = Dataset(id="quick-compare", name="Quick Compare",
                      examples=[Example(input_text="Summarize: revenue grew 22%.", expected_text="")])
    candidates = build_candidates(["mock_good", "mock_bad"])
    report = run_proof(
        run_id="run_q", created_at="2026-06-22T00:00:00Z",
        brief=ProofBrief(task_name="Quick check", decision_question="Which reads better?"),
        dataset=dataset, candidates=candidates, rubric=Rubric(kind="none"),
    )
    report.run.mode = "quick"
    report.run.chosen_winner = chosen
    return report


def test_receipt_version_is_8():
    assert RECEIPT_VERSION == 8


def test_quick_receipt_is_pick_based_and_unscored():
    data = build_receipt(_quick_report(chosen="mock_good"))
    assert data["mode"] == "quick"
    assert data["chosen_winner"] == "mock_good"
    assert data["failure_cases"] == []           # no scoring → no failures section
    assert "Picked" in data["verdict"]
    assert "mock_good" in data["recommendation"]
    assert "quick" in data["quick_note"].lower()


def test_quick_receipt_tie():
    data = build_receipt(_quick_report(chosen="tie"))
    assert "Tie" in data["verdict"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_export.py -k "version_is_8 or quick_receipt" -v`
Expected: FAIL — `RECEIPT_VERSION` is 7; `build_receipt` has no quick branch / `mode` key.

- [ ] **Step 3: Bump the version and document it**

In `src/orionfold/receipts/export.py`, add a comment line above line 27 and bump:

```python
# v8: quick-compare runs — the receipt carries `mode` ("full"|"quick") and `chosen_winner`. A quick
# receipt is a single-example, un-scored, human-picked check: objective columns only (latency / cost
# / tokens), no failure cases, a "quick check — not scored proof" note, and a promote-to-full CTA.
RECEIPT_VERSION = 8
```

- [ ] **Step 4: Make `_failure_cases` quick-aware**

In `src/orionfold/receipts/export.py`, replace `_failure_cases` (lines 49-51):

```python
def _failure_cases(report: ProofReport) -> list[ResultRow]:
    # A quick check is unscored (passed is None), so there is no notion of a failure case.
    if report.run.mode == "quick":
        return []
    return [r for r in report.results if not r.passed]
```

- [ ] **Step 5: Add the quick verdict helper + branch `build_receipt`**

In `src/orionfold/receipts/export.py`, add a helper after `_recommendation_line` (~46):

```python
def _quick_pick_lines(report: ProofReport) -> tuple[str, str]:
    """(verdict, recommendation) for a quick-compare run, driven by the human pick."""
    pick = report.run.chosen_winner
    if pick == "tie" or pick is None:
        return "Tie", "No clear winner — the two outputs were judged a tie."
    by_id = {c.id: c for c in report.run.candidates}
    cand = by_id.get(pick)
    label = cand.label if cand else pick
    provider = cand.provider_id if cand else "?"
    return f"Picked {label}", f"{label} ({provider}) — your pick on a single-example quick check."
```

In `build_receipt`, after `top = ...` / `has_winner = ...` (lines 108-109), add the quick-mode short-circuit values, then thread them into the returned dict. Replace the `summary`, `verdict`, `recommendation` computations so quick mode overrides them, and add the three new keys (`mode`, `chosen_winner`, `quick_note`). Concretely, change the block:

```python
    run = report.run
    top = report.leaderboard[0] if report.leaderboard else None
    has_winner = top is not None and top.pass_count > 0
    is_quick = run.mode == "quick"
    candidate_ids = [c.id for c in run.candidates]
    n_examples = len(report.results) // max(len(run.candidates), 1)
    if is_quick:
        summary = f"{len(run.candidates)} candidate(s) × {n_examples} example(s) · quick check (unscored)"
        quick_verdict, quick_reco = _quick_pick_lines(report)
    else:
        summary = (
            f"{len(run.candidates)} candidate(s) × {n_examples} "
            f"example(s) · rubric {run.rubric.kind} ≥ {run.rubric.threshold}"
        )
```

and in the returned dict, set these keys:

```python
        "mode": run.mode,
        "chosen_winner": run.chosen_winner,
        "quick_note": (
            "Single-example quick check — not scored proof. Promote to a full scored run for "
            "repeatable proof."
            if is_quick else ""
        ),
        "verdict": quick_verdict if is_quick else (_verdict(top) if has_winner else ("No clear winner" if top else "No run")),
        "recommendation": (
            quick_reco if is_quick
            else (
                _recommendation_line(top) if has_winner
                else (
                    f"No candidate passed the rubric (threshold {run.rubric.threshold:.2f})."
                    if top else "No candidates were run."
                )
            )
        ),
```

(Keep the existing `scored_by`, `cost`, `leaderboard`, `prompt_variants`, `failure_cases`, `repro` keys. `failure_cases` already returns `[]` for quick via Task 6 Step 4. For `repro.rerun`, a quick run's `dataset_id` is the ephemeral `quick-compare`; that is acceptable provenance — leave `_rerun_command` as-is.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_export.py -q`
Expected: PASS — new quick tests green; existing full-receipt tests still green (they don't set `mode`, so default `"full"` keeps the old output, except the version number — update any existing assertion of `receipt_version == 7` to `8`).

- [ ] **Step 7: Commit**

```bash
git add src/orionfold/receipts/export.py tests/test_export.py
git commit -m "feat(receipt): quick-compare branch in build_receipt + RECEIPT_VERSION 8

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Markdown receipt — quick branch

**Files:**
- Modify: `src/orionfold/receipts/export.py:164-238` (to_markdown)
- Test: `tests/test_export.py`

**Interfaces:**
- Consumes: the `build_receipt` dict from Task 6 (`mode`, `chosen_winner`, `quick_note`, `leaderboard`, `results`).
- Produces: `to_markdown(report)` renders an objective table (Candidate · Provider · Privacy · Latency · Cost · Tokens) with a ★ on the picked row, the quick-check note, and no failure-cases section, when `mode == "quick"`.

- [ ] **Step 1: Write the failing test**

In `tests/test_export.py` add:

```python
from orionfold.receipts.export import to_markdown


def test_quick_markdown_has_objective_columns_and_no_score():
    md = to_markdown(_quick_report(chosen="mock_good"))
    assert "QUICK CHECK" in md
    assert "Tokens" in md and "Latency" in md
    assert "Pass rate" not in md and "$ / quality" not in md
    assert "Failure cases" not in md
    assert "Promote to a full scored run" in md
    assert "⭐" in md  # the picked candidate is starred
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export.py::test_quick_markdown_has_objective_columns_and_no_score -v`
Expected: FAIL — `to_markdown` renders the scored table + "Failure cases" unconditionally.

- [ ] **Step 3: Branch `to_markdown`**

In `src/orionfold/receipts/export.py`, at the top of `to_markdown` after `data = build_receipt(report)` (line 166), insert a quick-mode early return. Add a per-candidate token lookup from `report.results` (one row per candidate for a 1-example quick run):

```python
def to_markdown(report: ProofReport) -> str:
    """Human, client-shareable receipt in Markdown."""
    data = build_receipt(report)
    if data["mode"] == "quick":
        return _quick_markdown(report, data)
    brief = data["brief"]
    # ... existing full-receipt body unchanged ...
```

Add the helper above `to_markdown`:

```python
def _tokens_by_candidate(report: ProofReport) -> dict[str, int]:
    """Total tokens (input+output) per candidate across the quick run's single example."""
    totals: dict[str, int] = {}
    for r in report.results:
        totals[r.candidate_id] = totals.get(r.candidate_id, 0) + r.input_tokens + r.output_tokens
    return totals


def _quick_markdown(report: ProofReport, data: dict) -> str:
    brief = data["brief"]
    repro = data["repro"]
    tokens = _tokens_by_candidate(report)
    pick = data["chosen_winner"]
    lines: list[str] = [
        "# Proof Receipt",
        "",
        "> **QUICK CHECK** · 1 example · not scored proof",
        "",
        f"**Verdict: {data['verdict']}** — {data['recommendation']}",
        "",
        f"_{data['summary']}_",
        "",
        f"- **Decision:** {brief['decision_question']}",
        f"- **Task:** {brief['task_name']}",
        f"- **Run id:** `{data['run_id']}`",
        f"- **Config hash:** `{data['config_hash']}`",
        f"- **Generated:** {data['created_at']}",
        f"- **Receipt schema:** v{data['receipt_version']}",
        "",
        "## Head-to-head",
        "",
        "| Candidate | Provider | Privacy | Latency | Cost | Tokens |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for e in data["leaderboard"]:
        marker = " ⭐" if e["candidate_id"] == pick else ""
        lines.append(
            f"| {_md_cell(e['label'])}{marker} | {_md_cell(e['provider_id'])} | "
            f"{_md_cell(e['privacy'])} | {e['avg_latency_ms']}ms | "
            f"${e['total_estimated_cost_usd']:.4f} | {tokens.get(e['candidate_id'], 0)} |"
        )
    lines += ["", "## Outputs", ""]
    by_id = {c.id: c for c in report.run.candidates}
    for r in report.results:
        cand = by_id.get(r.candidate_id)
        label = cand.label if cand else r.candidate_id
        star = " ⭐" if r.candidate_id == pick else ""
        body = f"error: {r.error}" if r.error else (_md_inline(r.output_text) or "—")
        lines += [f"- **{_md_cell(label)}{star}** — {body}"]
    lines += [
        "",
        f"_{data['quick_note']}_",
        "",
        "## Repro",
        "",
        f"- **Run id:** `{repro['run_id']}`",
        f"- **Config hash:** `{repro['config_hash']}` (identical inputs reproduce this hash)",
        f"- **Generated:** {repro['created_at']}",
        "",
    ]
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_export.py::test_quick_markdown_has_objective_columns_and_no_score -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/receipts/export.py tests/test_export.py
git commit -m "feat(receipt): quick-compare Markdown (objective table + outputs, no score)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: HTML receipt — quick branch + secret scan

**Files:**
- Modify: `src/orionfold/receipts/export.py:241-380` (to_html)
- Test: `tests/test_export.py`

**Interfaces:**
- Consumes: the `build_receipt` dict + `report.results`.
- Produces: `to_html(report, theme)` renders the quick objective table + outputs + note when `mode == "quick"`, reusing the existing `<style>` block. No score/pass-rate cells, no failure list.

- [ ] **Step 1: Write the failing test**

In `tests/test_export.py` add:

```python
from orionfold.receipts.export import to_html


def test_quick_html_is_objective_and_secret_free():
    html_out = to_html(_quick_report(chosen="mock_good"))
    assert "QUICK CHECK" in html_out
    assert "Tokens" in html_out and "Latency" in html_out
    assert "Pass rate" not in html_out
    assert "Promote to a full scored run" in html_out
    # never leak secrets/keys into a receipt
    low = html_out.lower()
    assert "api_key" not in low and "sk-" not in low
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export.py::test_quick_html_is_objective_and_secret_free -v`
Expected: FAIL — HTML renders the scored leaderboard + "Pass rate" header.

- [ ] **Step 3: Branch `to_html`**

In `src/orionfold/receipts/export.py`, at the top of `to_html` after `data = build_receipt(report)` (line 243), add:

```python
    if data["mode"] == "quick":
        return _quick_html(report, data, theme)
```

Add the helper above `to_html` (it reuses the same `<style>` by sharing the document skeleton — to stay DRY, factor the `<style>...</style>` string into a module-level constant `_RECEIPT_STYLE` and reference it in both `to_html` and `_quick_html`). First extract the existing style:

```python
_RECEIPT_STYLE = """<style>
  /* ... move the entire existing <style> body here verbatim ... */
</style>"""
```

Then `_quick_html`:

```python
def _quick_html(report: ProofReport, data: dict, theme: str | None) -> str:
    brief = data["brief"]
    tokens = _tokens_by_candidate(report)
    pick = data["chosen_winner"]
    by_id = {c.id: c for c in report.run.candidates}
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(e['label'])}{' ⭐' if e['candidate_id'] == pick else ''}</td>"
        f"<td>{html.escape(e['provider_id'])}</td>"
        f"<td>{html.escape(e['privacy'])}</td>"
        f"<td>{e['avg_latency_ms']}ms</td>"
        f"<td>${e['total_estimated_cost_usd']:.4f}</td>"
        f"<td>{tokens.get(e['candidate_id'], 0)}</td>"
        "</tr>"
        for e in data["leaderboard"]
    )
    outputs = "".join(
        "<li><strong>{label}{star}</strong>"
        "<div class='case'><span>output</span> {body}</div></li>".format(
            label=html.escape(by_id[r.candidate_id].label if r.candidate_id in by_id else r.candidate_id),
            star=" ⭐" if r.candidate_id == pick else "",
            body=html.escape(f"error: {r.error}" if r.error else (r.output_text or "—")),
        )
        for r in report.results
    )
    theme_attr = f' data-theme="{theme}"' if theme in ("light", "dark") else ""
    return f"""<!doctype html>
<html lang="en"{theme_attr}>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Proof Receipt · Quick Check</title>
{_RECEIPT_STYLE}
</head>
<body>
<main>
  <h1>Proof Receipt</h1>
  <p class="muted">QUICK CHECK · 1 example · not scored proof</p>
  <div class="rec"><strong>Verdict: {html.escape(data['verdict'])}</strong> — {html.escape(data['recommendation'])}</div>
  <p class="muted">{html.escape(data['summary'])}</p>
  <dl>
    <dt>Decision</dt><dd>{html.escape(brief['decision_question'])}</dd>
    <dt>Task</dt><dd>{html.escape(brief['task_name'])}</dd>
    <dt>Run id</dt><dd><code>{html.escape(data['run_id'])}</code></dd>
    <dt>Config hash</dt><dd><code>{html.escape(data['config_hash'])}</code></dd>
    <dt>Generated</dt><dd>{html.escape(data['created_at'])}</dd>
    <dt>Receipt schema</dt><dd>v{data['receipt_version']}</dd>
  </dl>
  <h2>Head-to-head</h2>
  <table>
    <thead><tr><th>Candidate</th><th>Provider</th><th>Privacy</th><th>Latency</th><th>Cost</th><th>Tokens</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <h2>Outputs</h2>
  <ul class="failures">{outputs}</ul>
  <p class="muted">{html.escape(data['quick_note'])}</p>
</main>
</body>
</html>
"""
```

- [ ] **Step 4: Run tests to verify they pass + full export suite**

Run: `uv run pytest tests/test_export.py -q`
Expected: PASS — quick HTML test green; existing full HTML tests still green (the extracted `_RECEIPT_STYLE` is byte-identical to the inline style, so full receipts are unchanged).

- [ ] **Step 5: Receipt-quality + secrets gate**

Run: `uv run pytest -q`
Expected: PASS. Then sanity-check no secret patterns across all formats for a quick run (covered by the test in Step 1).

- [ ] **Step 6: Commit**

```bash
git add src/orionfold/receipts/export.py tests/test_export.py
git commit -m "feat(receipt): quick-compare HTML (objective table + outputs); share style const

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Frontend API schema + `patchWinner`

**Files:**
- Modify: `web/src/lib/api.ts:87-93` (rubric), `:115-130` (resultRow), `:139-150` (proofRun), `:324-330` (RunRequest), add `patchWinner`
- Test: covered by `tsc` + downstream Vitest (no standalone unit test for the thin client)

**Interfaces:**
- Produces: `rubricSchema.kind` includes `"none"`; `resultRowSchema.score`/`passed` nullable + `input_tokens`/`output_tokens`; `proofRunSchema` adds `mode`/`chosen_winner`; `RunRequest` adds `examples?`/`mode?`; `patchWinner(runId: string, chosen_winner: string): Promise<ProofReport>`.

- [ ] **Step 1: Update the Zod schemas**

In `web/src/lib/api.ts`:

Rubric (line 88):
```typescript
  kind: z.enum(["exact", "contains", "similarity", "keypoint", "judge", "none"]),
```

resultRow (lines 121-122 and add two fields after `estimated_cost_usd`):
```typescript
  score: z.number().nullable(),
  passed: z.boolean().nullable(),
  latency_ms: z.number(),
  estimated_cost_usd: z.number(),
  input_tokens: z.number().default(0),
  output_tokens: z.number().default(0),
```

proofRun (after `status`, line 149):
```typescript
  status: z.literal("complete"),
  mode: z.enum(["full", "quick"]).default("full"),
  chosen_winner: z.string().nullable().optional(),
```

- [ ] **Step 2: Extend `RunRequest` + the example shape**

In `web/src/lib/api.ts`, update the interface (lines 324-330):

```typescript
export interface QuickExample {
  input_text: string;
  expected_text: string;
}

export interface RunRequest {
  dataset_id?: string;
  candidate_ids: string[];
  rubric?: z.infer<typeof rubricSchema> | null;
  brief: ProofBrief;
  prompt_variants?: PromptVariant[];
  examples?: QuickExample[];
  mode?: "full" | "quick";
}
```

- [ ] **Step 3: Add `patchWinner`**

In `web/src/lib/api.ts`, after `createRunStream` (or near `getRuns`), add:

```typescript
export function patchWinner(runId: string, chosen_winner: string): Promise<ProofReport> {
  return mutate(`/api/runs/${runId}/winner`, "PATCH", proofReportSchema, { chosen_winner });
}
```

- [ ] **Step 4: Type-check**

Run: `pnpm --dir web exec tsc --noEmit`
Expected: exit 0. (Existing call sites that read `row.score`/`row.passed` may now see `number | null`/`boolean | null` — fix any that assume non-null with a `?? 0` / `=== true` guard. The scored-run UI in `FailureCases`/`Leaderboard` reads `LeaderboardEntry` (unchanged), not `ResultRow.score`, so the surface should be small; resolve whatever `tsc` flags.)

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/api.ts
git commit -m "feat(web): api schema for quick-compare (none rubric, mode, pick) + patchWinner

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Pure quick-compare formatters

**Files:**
- Create: `web/src/features/proof/quickCompareFormat.ts`
- Test: `web/src/features/proof/quickCompareFormat.test.ts`

**Interfaces:**
- Produces:
  - `objectiveBar(value: number, max: number): number` → width fraction in `[0,1]` (`0` when `max <= 0`).
  - `totalTokens(row: { input_tokens: number; output_tokens: number }): number`.
  - `pickLabel(chosen: string | null, a: string, b: string): string` → human label for the recorded pick.

- [ ] **Step 1: Write the failing test**

Create `web/src/features/proof/quickCompareFormat.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { objectiveBar, totalTokens, pickLabel } from "./quickCompareFormat";

describe("objectiveBar", () => {
  it("scales value against max", () => {
    expect(objectiveBar(420, 980)).toBeCloseTo(420 / 980);
    expect(objectiveBar(980, 980)).toBe(1);
  });
  it("is zero-safe", () => {
    expect(objectiveBar(0, 0)).toBe(0);
    expect(objectiveBar(5, 0)).toBe(0);
  });
});

describe("totalTokens", () => {
  it("sums input + output", () => {
    expect(totalTokens({ input_tokens: 12, output_tokens: 30 })).toBe(42);
  });
});

describe("pickLabel", () => {
  it("names the chosen side, a tie, or no pick", () => {
    expect(pickLabel("cand_a", "A", "B")).toContain("A");
    expect(pickLabel("tie", "A", "B")).toMatch(/tie/i);
    expect(pickLabel(null, "A", "B")).toMatch(/no pick/i);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test --run quickCompareFormat`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the helpers**

Create `web/src/features/proof/quickCompareFormat.ts`:

```typescript
// Pure presentation helpers for the quick-compare head-to-head. No score logic — a quick
// check is unscored; these only normalize objective metrics (latency / cost / tokens) and
// describe the recorded human pick.

/** Width fraction (0..1) of an objective bar; zero-safe so a 0 max never divides. */
export function objectiveBar(value: number, max: number): number {
  if (max <= 0) return 0;
  return Math.min(1, Math.max(0, value / max));
}

/** Total tokens for a result row — input + output. */
export function totalTokens(row: { input_tokens: number; output_tokens: number }): number {
  return row.input_tokens + row.output_tokens;
}

/** Human label for the recorded pick: a named side, a tie, or no pick yet. */
export function pickLabel(chosen: string | null, idA: string, idB: string): string {
  if (chosen === null) return "No pick yet";
  if (chosen === "tie") return "Tie — no clear winner";
  if (chosen === idA) return `Picked ${idA}`;
  if (chosen === idB) return `Picked ${idB}`;
  return `Picked ${chosen}`;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --dir web test --run quickCompareFormat`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/proof/quickCompareFormat.ts web/src/features/proof/quickCompareFormat.test.ts
git commit -m "feat(web): pure quick-compare formatters (objective bars, pick label)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: RunSetup third "Quick" mode + ProofCockpit wiring

**Files:**
- Modify: `web/src/features/proof/RunSetup.tsx` (props, toggle, quick lane, canRun)
- Modify: `web/src/features/proof/ProofCockpit.tsx` (compareBy type, quickPrompt state, run branch)
- Test: `web/src/features/proof/RunSetup.test.tsx`

**Interfaces:**
- Consumes: `RunRequest` (Task 9), `CandidatePicker` (existing).
- Produces: `RunSetup` accepts `compareBy: "models" | "prompts" | "quick"`, `quickPrompt: string`, `onQuickPromptChange: (s: string) => void`. In quick mode, `canRun` requires a non-empty prompt + exactly 2 candidates. `ProofCockpit` builds the quick `RunRequest` and fires `createRunStream`.

- [ ] **Step 1: Write the failing test**

Create `web/src/features/proof/RunSetup.test.tsx` (mirror the existing test setup in this folder for providing `panel`/`datasets` props; if a shared test helper/fixture exists, reuse it):

```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RunSetup } from "./RunSetup";

const panel = { providers: [{ provider_id: "mock", label: "Mock", available: true, models: [
  { candidate_id: "mock_good", label: "Mock · good", privacy: "local", available: true },
  { candidate_id: "mock_bad", label: "Mock · bad", privacy: "local", available: true },
] }] } as any;
const datasets = [{ id: "d1", name: "Demo", description: "", examples: [{ input_text: "x", expected_text: "y", keypoints: [] }] }] as any;

function baseProps(over: Partial<React.ComponentProps<typeof RunSetup>> = {}) {
  return {
    datasets, panel, datasetId: "d1", onDatasetChange: vi.fn(),
    selectedCandidates: [], onToggleCandidate: vi.fn(),
    brief: { task_name: "T", decision_question: "Q", success_criteria: "" },
    onBriefChange: vi.fn(), onRun: vi.fn(), isRunning: false, hasRun: false, error: null,
    rubric: null, onRubricChange: vi.fn(),
    compareBy: "quick" as const, onCompareByChange: vi.fn(),
    promptVariants: [], onPromptVariantsChange: vi.fn(), promptModel: "", onPromptModelChange: vi.fn(),
    quickPrompt: "", onQuickPromptChange: vi.fn(),
    ...over,
  };
}

describe("RunSetup quick mode", () => {
  it("disables Run until a prompt + exactly 2 candidates are set", () => {
    const { rerender } = render(<RunSetup {...baseProps()} />);
    expect(screen.getByRole("button", { name: /run proof/i })).toBeDisabled();
    rerender(<RunSetup {...baseProps({ quickPrompt: "Summarize this", selectedCandidates: ["mock_good", "mock_bad"] })} />);
    expect(screen.getByRole("button", { name: /run proof/i })).toBeEnabled();
  });

  it("shows a hint when not exactly 2 candidates", () => {
    render(<RunSetup {...baseProps({ quickPrompt: "x", selectedCandidates: ["mock_good"] })} />);
    expect(screen.getByText(/exactly 2/i)).toBeInTheDocument();
  });

  it("edits the prompt via the textarea", () => {
    const onQuickPromptChange = vi.fn();
    render(<RunSetup {...baseProps({ onQuickPromptChange })} />);
    fireEvent.change(screen.getByLabelText(/prompt/i), { target: { value: "hello" } });
    expect(onQuickPromptChange).toHaveBeenCalledWith("hello");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test --run RunSetup`
Expected: FAIL — `RunSetup` has no quick mode / `quickPrompt` prop.

- [ ] **Step 3: Widen the props + canRun in RunSetup**

In `web/src/features/proof/RunSetup.tsx`, update the interface (lines 28-29) and add quick props:

```typescript
  compareBy: "models" | "prompts" | "quick";
  onCompareByChange: (mode: "models" | "prompts" | "quick") => void;
  promptVariants: PromptVariant[];
  onPromptVariantsChange: (next: PromptVariant[]) => void;
  promptModel: string;
  onPromptModelChange: (id: string) => void;
  quickPrompt: string;
  onQuickPromptChange: (s: string) => void;
```

Destructure `quickPrompt, onQuickPromptChange` in the body. Update `canRun` (lines 64-68):

```typescript
  const canRun =
    brief.task_name.trim().length > 0 &&
    (compareBy === "prompts"
      ? Boolean(promptModel) && validPromptVariants(promptVariants)
      : compareBy === "quick"
        ? quickPrompt.trim().length > 0 && selectedCandidates.length === 2
        : selectedCandidates.length > 0);
```

- [ ] **Step 4: Add the third toggle button**

In the Compare-by group (lines 104-121), change the mode list and capitalization to include `quick`:

```tsx
                {(["models", "prompts", "quick"] as const).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    aria-pressed={compareBy === mode}
                    onClick={() => onCompareByChange(mode)}
                    className={
                      "rounded-md px-3 py-1.5 capitalize transition-colors " +
                      (compareBy === mode
                        ? "bg-(--color-accent-strong) text-(--color-accent-ink)"
                        : "text-(--color-ink-muted) hover:text-(--color-ink)")
                    }
                  >
                    {mode === "quick" ? "Quick ⚡" : mode}
                  </button>
                ))}
```

- [ ] **Step 5: Render the quick lane**

In the body region (lines 130-147), add a quick branch. When quick: show only the prompt textarea + a 2-candidate picker + an exactly-2 hint; hide dataset Step 1 and the ScoringMethod/decision-question (wrap those so they don't render in quick mode):

Replace the body `<div>` block (130-147) with:

```tsx
        <div>
          {compareBy === "prompts" ? (
            <PromptVariants
              variants={promptVariants}
              modelId={promptModel}
              panel={panel}
              onChangeVariants={onPromptVariantsChange}
              onChangeModel={onPromptModelChange}
            />
          ) : compareBy === "quick" ? (
            <div className="grid gap-4">
              <label className="grid gap-1.5 text-sm">
                <span className="text-(--color-ink-muted)">Prompt</span>
                <textarea
                  aria-label="Prompt"
                  value={quickPrompt}
                  onChange={(e) => onQuickPromptChange(e.target.value)}
                  rows={4}
                  placeholder="Paste one prompt — both candidates answer it."
                  className={inputCls + " resize-y"}
                />
              </label>
              <CandidatePicker panel={panel} selected={selectedCandidates} onToggle={onToggleCandidate} />
              {selectedCandidates.length !== 2 && (
                <p className="text-xs text-(--color-ink-faint)">Pick exactly 2 candidates to compare.</p>
              )}
            </div>
          ) : (
            <div className="grid gap-6">
              {recipes}
              <CandidatePicker panel={panel} selected={selectedCandidates} onToggle={onToggleCandidate} />
            </div>
          )}
        </div>
```

Wrap the dataset Step 1 (lines 86-99) and the ScoringMethod block (lines 170-174) and the Decision-question label (158-168) so they are hidden in quick mode — wrap each in `{compareBy !== "quick" && ( ... )}`. (The Task name label stays; it headlines the receipt.)

- [ ] **Step 6: Run test to verify it passes**

Run: `pnpm --dir web test --run RunSetup`
Expected: PASS.

- [ ] **Step 7: Wire ProofCockpit**

In `web/src/features/proof/ProofCockpit.tsx`:

Change the compareBy state type (line 58):
```typescript
  const [compareBy, setCompareBy] = useState<"models" | "prompts" | "quick">("models");
  const [quickPrompt, setQuickPrompt] = useState("");
```

Cap quick selection to 2 in `toggleCandidate` (lines 116-120):
```typescript
  const toggleCandidate = (id: string) => {
    setActiveRecipeId(null);
    const base = resolvedSelected;
    if (base.includes(id)) {
      setSelected(base.filter((c) => c !== id));
      return;
    }
    // Quick-compare is strictly head-to-head: a third pick replaces the oldest.
    const next = compareBy === "quick" && base.length >= 2 ? [base[1], id] : [...base, id];
    setSelected(next);
  };
```

Pass the new props to `RunSetup` (in the JSX, alongside `promptModel`):
```tsx
          quickPrompt={quickPrompt}
          onQuickPromptChange={setQuickPrompt}
```

Extend the `onRun` branch (lines 191-208) to handle quick:
```tsx
          onRun={() =>
            runMutation.mutate(
              compareBy === "prompts"
                ? {
                    dataset_id: resolvedDatasetId,
                    candidate_ids: [resolvedPromptModel],
                    prompt_variants: cleanVariants(promptVariants),
                    brief: effectiveBrief,
                    ...(rubric ? { rubric } : {}),
                  }
                : compareBy === "quick"
                  ? {
                      candidate_ids: resolvedSelected,
                      examples: [{ input_text: quickPrompt, expected_text: "" }],
                      rubric: { kind: "none", threshold: 0, case_sensitive: false },
                      mode: "quick",
                      brief: effectiveBrief,
                    }
                  : {
                      dataset_id: resolvedDatasetId,
                      candidate_ids: resolvedSelected,
                      brief: effectiveBrief,
                      ...(rubric ? { rubric } : {}),
                    },
            )
          }
```

- [ ] **Step 8: Type-check + full web suite**

Run: `pnpm --dir web exec tsc --noEmit && pnpm --dir web test --run`
Expected: exit 0 / all pass.

- [ ] **Step 9: Commit**

```bash
git add web/src/features/proof/RunSetup.tsx web/src/features/proof/ProofCockpit.tsx web/src/features/proof/RunSetup.test.tsx
git commit -m "feat(web): Quick ⚡ third compare mode (prompt + 2 candidates)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: QuickCompare Decide view (head-to-head + pick + save + promote)

**Files:**
- Create: `web/src/features/proof/QuickCompare.tsx`
- Modify: `web/src/features/proof/ProofCockpit.tsx` (Decide-view branch on `report.run.mode`)
- Test: `web/src/features/proof/QuickCompare.test.tsx`

**Interfaces:**
- Consumes: `ProofReport`, `patchWinner` (Task 9), `objectiveBar`/`totalTokens` (Task 10).
- Produces: `QuickCompare({ report, onReport, onPromote })` — two output cards with objective bars, an `A wins / B wins / tie` control, a "Save as Proof Receipt" button enabled once a pick is chosen (fires `patchWinner` → `onReport(updated)`), and a "Promote to a full scored run" button (calls `onPromote`).

- [ ] **Step 1: Write the failing test**

Create `web/src/features/proof/QuickCompare.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QuickCompare } from "./QuickCompare";
import * as api from "../../lib/api";

function quickReport(): api.ProofReport {
  const cand = (id: string, label: string) => ({ id, label, provider_id: "mock_good", privacy: "local", model: null, system_prompt: null });
  const row = (id: string, out: string, latency: number) => ({
    candidate_id: id, example_index: 0, input_text: "p", expected_text: "", output_text: out,
    score: null, passed: null, latency_ms: latency, estimated_cost_usd: 0, input_tokens: 5, output_tokens: 7,
    judge_cost_usd: 0, judge_latency_ms: 0, privacy: "local", error: null,
  });
  const entry = (id: string, label: string, latency: number) => ({
    candidate_id: id, label, provider_id: "mock_good", privacy: "local", model: null, system_prompt: null,
    total: 1, pass_count: 0, pass_rate: 0, avg_score: 0, avg_latency_ms: latency,
    total_estimated_cost_usd: 0, failure_count: 0, error_count: 0, recommended: false, cost_per_quality: null,
  });
  return {
    run: { id: "run_q", brief: { task_name: "T", decision_question: "Q", success_criteria: "" },
      dataset_id: "quick-compare", dataset_name: "Quick Compare",
      rubric: { kind: "none", threshold: 0, case_sensitive: false }, candidates: [cand("a", "Alpha"), cand("b", "Beta")],
      config_hash: "abc", created_at: "2026-06-22T00:00:00Z", status: "complete", mode: "quick", chosen_winner: null },
    leaderboard: [entry("a", "Alpha", 420), entry("b", "Beta", 980)],
    results: [row("a", "alpha output", 420), row("b", "beta output", 980)],
    cost_summary: { candidate_cost_usd: 0, judge_cost_usd: 0, total_cost_usd: 0 },
  } as api.ProofReport;
}

describe("QuickCompare", () => {
  it("renders both outputs and gates Save until a pick", () => {
    render(<QuickCompare report={quickReport()} onReport={vi.fn()} onPromote={vi.fn()} />);
    expect(screen.getByText("alpha output")).toBeInTheDocument();
    expect(screen.getByText("beta output")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save as proof receipt/i })).toBeDisabled();
  });

  it("saves the pick via patchWinner", async () => {
    const onReport = vi.fn();
    const picked = { ...quickReport(), run: { ...quickReport().run, chosen_winner: "a" } };
    const spy = vi.spyOn(api, "patchWinner").mockResolvedValue(picked as api.ProofReport);
    render(<QuickCompare report={quickReport()} onReport={onReport} onPromote={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /alpha wins/i }));
    fireEvent.click(screen.getByRole("button", { name: /save as proof receipt/i }));
    await waitFor(() => expect(spy).toHaveBeenCalledWith("run_q", "a"));
    await waitFor(() => expect(onReport).toHaveBeenCalledWith(picked));
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test --run QuickCompare`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `QuickCompare.tsx`**

Create `web/src/features/proof/QuickCompare.tsx`:

```tsx
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { patchWinner, type ProofReport, type ResultRow } from "../../lib/api";
import { ProviderTag } from "./badges";
import { objectiveBar, totalTokens } from "./quickCompareFormat";

// The unscored head-to-head: two outputs, objective bars (latency / cost / tokens), and the
// operator's pick. Bars use neutral ink — never the accent (interactive) or green (PASS).
export function QuickCompare({
  report,
  onReport,
  onPromote,
}: {
  report: ProofReport;
  onReport: (r: ProofReport) => void;
  onPromote: () => void;
}) {
  const [pick, setPick] = useState<string | null>(report.run.chosen_winner ?? null);
  const save = useMutation({
    mutationFn: (winner: string) => patchWinner(report.run.id, winner),
    onSuccess: (r) => onReport(r),
  });

  const byId = new Map(report.run.candidates.map((c) => [c.id, c]));
  const rows = report.results;
  const maxLatency = Math.max(...rows.map((r) => r.latency_ms), 0);
  const maxCost = Math.max(...rows.map((r) => r.estimated_cost_usd), 0);
  const maxTokens = Math.max(...rows.map((r) => totalTokens(r)), 0);

  return (
    <section aria-label="Quick compare" className="grid gap-5">
      <p className="text-sm text-(--color-ink-muted)">
        {report.run.brief.decision_question || report.run.brief.task_name}
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        {rows.map((r) => {
          const cand = byId.get(r.candidate_id);
          const picked = pick === r.candidate_id;
          return (
            <article
              key={r.candidate_id}
              className={
                "rounded-xl border p-4 " +
                (picked ? "border-(--color-accent)/50 bg-(--color-accent)/[0.06]" : "border-(--color-panel-line)")
              }
            >
              <div className="flex items-center gap-2">
                <span className="font-semibold text-(--color-ink)">{cand?.label ?? r.candidate_id}</span>
                {cand && <ProviderTag candidate={cand} />}
              </div>
              <p className="mt-2 whitespace-pre-wrap text-sm text-(--color-ink-muted)">
                {r.error ? `error: ${r.error}` : r.output_text || "—"}
              </p>
              <QuickBars row={r} maxLatency={maxLatency} maxCost={maxCost} maxTokens={maxTokens} />
              <button
                type="button"
                aria-pressed={picked}
                onClick={() => setPick(r.candidate_id)}
                className={
                  "mt-3 w-full rounded-lg px-3 py-2 text-sm font-medium transition-colors " +
                  (picked
                    ? "bg-(--color-accent-strong) text-(--color-accent-ink)"
                    : "border border-(--color-panel-line) text-(--color-ink-muted) hover:text-(--color-ink)")
                }
              >
                {cand?.label ?? r.candidate_id} wins
              </button>
            </article>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          aria-pressed={pick === "tie"}
          onClick={() => setPick("tie")}
          className={
            "rounded-lg px-4 py-2 text-sm transition-colors " +
            (pick === "tie"
              ? "bg-(--color-accent-strong) text-(--color-accent-ink)"
              : "border border-(--color-panel-line) text-(--color-ink-muted) hover:text-(--color-ink)")
          }
        >
          Tie
        </button>
        <button
          type="button"
          disabled={pick === null || save.isPending}
          onClick={() => pick && save.mutate(pick)}
          className="rounded-lg bg-(--color-accent-strong) px-5 py-2.5 font-medium text-(--color-accent-ink) transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          {save.isPending ? "Saving…" : "Save as Proof Receipt"}
        </button>
        <button
          type="button"
          onClick={onPromote}
          className="text-sm text-(--color-accent) hover:underline"
        >
          Promote to a full scored run →
        </button>
      </div>
      <p className="text-xs text-(--color-ink-faint)">
        Single-example quick check — not scored proof. Promote to a full scored run for repeatable proof.
      </p>
      {save.isError && (
        <p role="alert" className="text-sm text-(--color-danger)">
          Could not save the pick. Try again.
        </p>
      )}
    </section>
  );
}

function QuickBars({
  row,
  maxLatency,
  maxCost,
  maxTokens,
}: {
  row: ResultRow;
  maxLatency: number;
  maxCost: number;
  maxTokens: number;
}) {
  const bar = (label: string, value: string, frac: number) => (
    <div className="grid grid-cols-[4rem_1fr_auto] items-center gap-2 text-xs tabular-nums text-(--color-ink-faint)">
      <span>{label}</span>
      <span className="h-1.5 rounded-full bg-(--color-panel-line)">
        <span className="block h-full rounded-full bg-(--color-ink-faint)" style={{ width: `${Math.round(frac * 100)}%` }} />
      </span>
      <span>{value}</span>
    </div>
  );
  return (
    <div className="mt-3 grid gap-1.5">
      {bar("latency", `${row.latency_ms}ms`, objectiveBar(row.latency_ms, maxLatency))}
      {bar("cost", `$${row.estimated_cost_usd.toFixed(4)}`, objectiveBar(row.estimated_cost_usd, maxCost))}
      {bar("tokens", String(totalTokens(row)), objectiveBar(totalTokens(row), maxTokens))}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --dir web test --run QuickCompare`
Expected: PASS.

- [ ] **Step 5: Branch the Decide view in ProofCockpit**

In `web/src/features/proof/ProofCockpit.tsx`, import `QuickCompare` (top with the other feature imports):

```typescript
import { QuickCompare } from "./QuickCompare";
```

Replace the report-branch of the Decide view (lines 217-227) so quick reports render `QuickCompare`:

```tsx
        ) : report ? (
          report.run.mode === "quick" ? (
            <div className="motion-safe:animate-reveal">
              <QuickCompare
                report={report}
                onReport={(r) => {
                  onReport(r);
                  void queryClient.invalidateQueries({ queryKey: ["runs"] });
                }}
                onPromote={() => {
                  setCompareBy("models");
                  setSelected(report.run.candidates.map((c) => c.id));
                }}
              />
            </div>
          ) : (
            <div className="flex flex-col gap-8 motion-safe:animate-reveal">
              <DecisionSummary
                brief={report.run.brief}
                leaderboard={report.leaderboard}
                scoredBy={scoredByLabel(report.run.rubric)}
                cost={report.cost_summary}
              />
              <Leaderboard entries={report.leaderboard} />
              <FailureCases report={report} selected={openFailure} onSelect={setOpenFailure} />
            </div>
          )
        ) : (
```

(`onPromote` pre-fills a Models run with the same 2 candidates; the operator then sets a dataset + runs a full scored proof. The prompt itself isn't carried into a stored dataset — promotion is a fresh full run, by design.)

- [ ] **Step 6: Type-check + full web suite**

Run: `pnpm --dir web exec tsc --noEmit && pnpm --dir web test --run`
Expected: exit 0 / all pass.

- [ ] **Step 7: Commit**

```bash
git add web/src/features/proof/QuickCompare.tsx web/src/features/proof/QuickCompare.test.tsx web/src/features/proof/ProofCockpit.tsx
git commit -m "feat(web): QuickCompare head-to-head Decide view (pick, save, promote)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 13: e2e — quick compare flow (keyless)

**Files:**
- Modify: `e2e/playwright/proof.spec.ts`
- Test: the spec itself

**Interfaces:**
- Consumes: the full stack via the embedded build (the Playwright `webServer` serves the built cockpit). Mock candidates require Sandbox on — enable it the way the existing specs do.

- [ ] **Step 1: Write the failing e2e test**

In `e2e/playwright/proof.spec.ts` add a test (match the file's existing helpers for enabling Sandbox + seeding; reuse them rather than re-implementing):

```typescript
test("quick compare → pick → save receipt", async ({ page }) => {
  await page.goto("/");
  // (reuse the existing helper that enables Sandbox so the mock candidates appear)
  await enableSandbox(page);
  await page.goto("/");

  // Enter quick mode, type a prompt, pick the two mock candidates.
  await page.getByRole("button", { name: /quick/i }).click();
  await page.getByLabel(/prompt/i).fill("Summarize: revenue grew 22% to $48.2M.");
  await page.getByRole("button", { name: /mock · good/i }).click();
  await page.getByRole("button", { name: /mock · bad/i }).click();
  await page.getByRole("button", { name: /run proof/i }).click();

  // Head-to-head appears; pick a winner; save.
  await expect(page.getByRole("button", { name: /save as proof receipt/i })).toBeVisible();
  await page.getByRole("button", { name: /mock · good wins/i }).click();
  await page.getByRole("button", { name: /save as proof receipt/i }).click();

  // The picked quick check now appears in Receipts.
  await page.getByRole("link", { name: /receipts/i }).click();
  await expect(page.getByText(/quick check/i).first()).toBeVisible();
});
```

(If the existing spec has no `enableSandbox`/seed helper, set Sandbox via the Settings UI as the other tests do. e2e runs serial against a shared webServer DB — scope any list assertion to the new card, don't assert exact counts.)

- [ ] **Step 2: Build the cockpit + run the spec to verify it fails (then passes)**

Run: `bash scripts/build.sh && pnpm --dir e2e exec playwright test proof -g "quick compare"`
Expected: first run may FAIL if selectors need adjusting to the rendered DOM; iterate selectors against `playwright` trace until PASS. Final: PASS.

- [ ] **Step 3: Run the full e2e suite (no regression)**

Run: `pnpm --dir e2e exec playwright test proof`
Expected: the quick test passes alongside the existing suite. (Note: `proof.spec.ts:89` "Different providers" recipe assertion is a pre-existing failure tracked in HANDOFF backlog item 0 — out of scope here; don't fix it in this task unless it blocks, and if so, only the one-line rename.)

- [ ] **Step 4: Commit**

```bash
git add e2e/playwright/proof.spec.ts
git commit -m "test(e2e): quick compare → pick → save receipt (keyless mocks)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 14: Browser verification + receipt-quality + worklog

**Files:**
- Modify: `docs/worklog/2026-06-22-quick-compare.md` (create), `HANDOFF.md` (update)

- [ ] **Step 1: Build + open the app, run the quick flow by hand**

Run: `bash scripts/build.sh` then open the embedded app (or live source per HANDOFF's port notes). Use the `browser-visual-verification` skill: enter `Compare by Quick ⚡`, run two mock candidates on a prompt, confirm the two output cards + objective bars (neutral ink, not accent/green), pick a winner, Save, then open the saved receipt — confirm the **QUICK CHECK** banner, objective columns, picked ★, promote note, and **Receipt schema v8**. Screenshot each state.

- [ ] **Step 2: Receipt-quality + secrets review**

Use the `receipt-quality-review` and `security-secrets-review` skills on a generated quick receipt (MD/HTML/JSON): no secrets, the verdict names the pick, the promote CTA is present, `receipt_version: 8`.

- [ ] **Step 3: Full verification sweep**

Run: `uv run pytest -q && pnpm --dir web test --run && pnpm --dir web exec tsc --noEmit && uv run ruff check src tests`
Expected: all green / exit 0.

- [ ] **Step 4: Worklog + HANDOFF**

Write `docs/worklog/2026-06-22-quick-compare.md` (Summary · Verification · Product impact · Risks · Next step) and overwrite `HANDOFF.md` to mark sub-project 3 of 3 DONE and surface the remaining backlog (pre-existing e2e recipe rename; stored recommended-on-0/5 backfill; packaging; git remote LAST). Commit.

```bash
git add docs/worklog/2026-06-22-quick-compare.md HANDOFF.md
git commit -m "docs: quick-compare worklog + handoff (sub-project 3 of 3 done)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- Judging = human pick + objective bars → Tasks 1 (unscored), 10 (bars), 12 (pick UI). ✓
- Entry = third mode on Proof Run → Task 11. ✓
- Same schema + quick flag, v8 → Tasks 2, 6, 7, 8. ✓
- Fork A unscored `kind:"none"` → Task 1. ✓
- Fork B pick persistence (auto-persist + PATCH winner) → Tasks 3, 4. ✓
- Receipts list filter → Task 5. ✓
- Tie kept → Tasks 4 (validation), 12 (UI). ✓
- Error handling (per-candidate error card, disabled save) → Task 12 (renders `r.error`), pick still allowed. ✓
- Promote CTA → Task 12. ✓
- Testing (backend/frontend/e2e) → every task + Task 13. ✓
- Invariants (config_hash, no migration, status tokens, keyless mocks) → Global Constraints + Task 2 (hash test), Task 12 (token bars). ✓

**Placeholder scan:** No TBD/TODO; every code step shows real code; e2e selectors flagged as needing iteration against the live DOM (legitimate for browser tests), with the helper-reuse instruction explicit.

**Type consistency:** `score`/`passed` nullable consistent across models.py (Task 1), api.ts (Task 9), and test fixtures (Task 12). `ProofRun.mode`/`chosen_winner` consistent across models.py (Task 2), routes (Tasks 3,4), repository (Task 5), export (Task 6), api.ts (Task 9). `objectiveBar`/`totalTokens`/`pickLabel` defined in Task 10 and consumed in Task 12. `patchWinner` defined in Task 9, used in Task 12. `_RECEIPT_STYLE`/`_tokens_by_candidate`/`_quick_markdown`/`_quick_html`/`_quick_pick_lines` all defined in Tasks 6-8 before use.

**Note on `pickLabel` (Task 10):** implemented and unit-tested for completeness/symmetry with the formatter module; the QuickCompare UI derives its label inline, so `pickLabel` may be unused by the component. If `tsc`/lint flags it as unused at the end, either wire it into the receipt-confirmation copy or drop it — a minor cleanup, not a blocker.
