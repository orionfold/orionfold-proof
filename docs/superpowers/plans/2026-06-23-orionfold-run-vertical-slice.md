# `orionfold run` Vertical Slice — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a headless `orionfold run` CLI command that drives the full proof workflow — load a dataset file → build candidates → resolve a rubric → run the matrix → emit a receipt — by calling a new pure core function that the FastAPI route also uses.

**Architecture:** The FastAPI `create_run` route handler (`server/routes.py:441-477`) already stitches a run together, but coupled to `RunRequest`/`HTTPException`/a live DB connection. We lift the stitch into a **pure core function** `execute_run(...)` in a new module `src/orionfold/proof/runner.py` that takes plain inputs (dataset, candidate_ids, rubric, brief) and returns a `ProofReport` — no FastAPI, no DB. The CLI and the route both call it (the route keeps owning HTTP concerns + persistence; the CLI owns file IO + stdout). This is the first concrete proof of ADR-0004's "three shells over one core."

**Tech Stack:** Python 3.12, Typer (CLI), Pydantic v2 (domain models), pytest + `typer.testing.CliRunner`. No new dependencies.

## Global Constraints

- **No new dependencies.** Everything needed (typer, pydantic, the core modules) is already installed. (CLAUDE.md stack; ADR-0004 §1 keeps the core dep set minimal.)
- **The CLI command is a thin wrapper.** `orionfold run` must call the public core function `execute_run()`, never re-implement matrix/scoring/stitch logic. (ADR-0004 §3 — "each CLI command is a thin wrapper over the public API.")
- **Keyless determinism in tests.** All automated tests use the mock candidates `mock_good` / `mock_bad` — no API keys, no network. (CLAUDE.md: provider tests skip without creds; mocks run keyless.)
- **Do NOT touch the mock matrix `config_hash` `467ddd96c9a5`.** This slice adds a new code path and a `run`/`reverse-engineer` of existing logic — it must not change `engine.config_hash`, `scoring/rubric.py` thresholds (keypoint stays `0.8`), or any provider behavior. (HANDOFF invariants.)
- **`run_id` format:** `f"run_{uuid.uuid4().hex[:12]}"`. **`created_at` format:** `datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")` → e.g. `"2026-06-23T10:30:45Z"`. Copy verbatim from `routes.py:460-465` so CLI receipts match fixtures. (engine stays clock-free; the caller injects id+timestamp — ADR-0003 discipline.)
- **Receipts are secret-free by construction** (secrets-guard hook + ADR-0005 §4). The end-to-end test asserts no key material in the output.
- **Commit after each task** (CLAUDE.md: frequent commits; solo, direct to `main` — no feature branch per the `commit-directly-to-main` memory).

---

## File Structure

| File | Responsibility | Create/Modify |
| --- | --- | --- |
| `src/orionfold/proof/runner.py` | **New core function `execute_run()`** — pure stitch (dataset + candidate_ids + rubric? + brief → `ProofReport`), id/timestamp generation, no FastAPI/DB. | Create |
| `tests/unit/test_runner.py` | Unit tests for `execute_run()` over mock candidates. | Create |
| `src/orionfold/proof/__init__.py` | Declare the public `__all__` for the `proof` package (ADR-0004 §2) — exports `execute_run`, `run_proof`, `run_matrix`, `iter_matrix`, `config_hash`, `build_cost_summary`. | Modify |
| `src/orionfold/cli.py` | Add the `run` command (thin wrapper over `execute_run` + file load + receipt emit + optional persist). | Modify |
| `tests/unit/test_cli_run.py` | CLI tests via `CliRunner` — help lists `run`; an end-to-end keyless run emits a receipt; `--out` writes a file; secret-free assertion. | Create |
| `tests/fixtures/run_slice_dataset.jsonl` | A tiny 3-example JSONL fixture for the CLI e2e test. | Create |
| `src/orionfold/server/routes.py` | Refactor `create_run` to call `execute_run()` (remove the duplicated stitch; route keeps HTTP validation + persistence). | Modify |

---

## Task 1: The pure core `execute_run()` function

Lift the route's stitch into a pure, testable core function. This is the architectural keystone — both shells will call it.

**Files:**
- Create: `src/orionfold/proof/runner.py`
- Test: `tests/unit/test_runner.py`

**Interfaces:**
- Consumes (all existing, verbatim signatures):
  - `build_candidates(candidate_ids: list[str]) -> list[Candidate]` from `orionfold.providers.registry` (raises `UnknownCandidateError`)
  - `default_rubric_for(dataset: Dataset, overrides=None, *, check_hint: str | None = None) -> Rubric` from `orionfold.scoring.rubric`
  - `run_proof(*, run_id: str, created_at: str, brief: ProofBrief, dataset: Dataset, candidates: list[Candidate], rubric: Rubric) -> ProofReport` from `orionfold.proof.engine`
  - `Dataset`, `Candidate`, `Rubric`, `ProofBrief`, `ProofReport` from `orionfold.domain.models`
- Produces (later tasks rely on this exact signature):
  - `execute_run(*, dataset: Dataset, candidate_ids: list[str], brief: ProofBrief, rubric: Rubric | None = None, mode: Literal["full", "quick"] = "full") -> ProofReport`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_runner.py`:

```python
"""execute_run() — the pure core stitch shared by the route and the CLI."""

from orionfold.domain.models import Dataset, Example, ProofBrief, ProofReport
from orionfold.proof.runner import execute_run

_BRIEF = ProofBrief(task_name="Slice test", decision_question="Which mock wins?")
_DATASET = Dataset(
    id="t-runner",
    name="Runner test",
    examples=[
        Example(input_text="ping", expected_text="ping"),
        Example(input_text="hello", expected_text="hello"),
    ],
)


def test_execute_run_returns_report_over_mock_candidates() -> None:
    report = execute_run(
        dataset=_DATASET,
        candidate_ids=["mock_good", "mock_bad"],
        brief=_BRIEF,
    )

    assert isinstance(report, ProofReport)
    # One leaderboard entry per candidate.
    assert {e.candidate_id for e in report.leaderboard} == {"mock_good", "mock_bad"}
    # 2 candidates x 2 examples = 4 result rows.
    assert len(report.results) == 4
    # The run carries injected provenance.
    assert report.run.id.startswith("run_")
    assert report.run.created_at.endswith("Z")
    assert report.run.config_hash  # non-empty
    assert report.run.mode == "full"


def test_execute_run_resolves_default_rubric_when_none_given() -> None:
    # No keypoints on the examples → default_rubric_for picks "similarity".
    report = execute_run(
        dataset=_DATASET,
        candidate_ids=["mock_good"],
        brief=_BRIEF,
    )
    assert report.run.rubric.kind == "similarity"


def test_execute_run_honors_explicit_rubric() -> None:
    from orionfold.domain.models import Rubric

    report = execute_run(
        dataset=_DATASET,
        candidate_ids=["mock_good"],
        brief=_BRIEF,
        rubric=Rubric(kind="exact", threshold=1.0),
    )
    assert report.run.rubric.kind == "exact"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_runner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'orionfold.proof.runner'`

- [ ] **Step 3: Write the minimal implementation**

Create `src/orionfold/proof/runner.py`:

```python
"""The headless run stitch — shared by the FastAPI route and the CLI.

``execute_run`` is the single place that turns a resolved dataset + candidate ids + (optional)
rubric into a finished :class:`ProofReport`. It is pure: no FastAPI, no database, no file IO.
The id and timestamp are generated here (the engine stays clock-free, per ADR-0003); the format
matches ``server/routes.py`` exactly so CLI receipts are byte-compatible with the cockpit's.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from orionfold.domain.models import Dataset, ProofBrief, ProofReport, Rubric
from orionfold.proof.engine import run_proof
from orionfold.providers.registry import build_candidates
from orionfold.scoring.rubric import default_rubric_for


def _now() -> str:
    """UTC, seconds precision, trailing-Z — matches the live route and the receipt fixtures."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def execute_run(
    *,
    dataset: Dataset,
    candidate_ids: list[str],
    brief: ProofBrief,
    rubric: Rubric | None = None,
    mode: Literal["full", "quick"] = "full",
) -> ProofReport:
    """Run the full proof matrix and return the assembled report.

    ``candidate_ids`` are resolved via ``build_candidates`` (raising ``UnknownCandidateError`` on
    an unavailable/unknown id). When ``rubric`` is ``None`` the default is resolved from the
    dataset via ``default_rubric_for``. The run id and ``created_at`` are generated here.
    """
    candidates = build_candidates(candidate_ids)
    resolved_rubric = rubric or default_rubric_for(dataset)
    report = run_proof(
        run_id=f"run_{uuid.uuid4().hex[:12]}",
        created_at=_now(),
        brief=brief,
        dataset=dataset,
        candidates=candidates,
        rubric=resolved_rubric,
    )
    report.run.mode = mode
    return report
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_runner.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Type + lint check**

Run: `uv run ruff check src/orionfold/proof/runner.py tests/unit/test_runner.py && uv run pyright src/orionfold/proof/runner.py`
Expected: no errors on these files.

- [ ] **Step 6: Commit**

```bash
git add src/orionfold/proof/runner.py tests/unit/test_runner.py
git commit -m "feat(proof): execute_run() — pure core run stitch for CLI + route

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Curate the `proof` package public surface

Declare what the `proof` package exposes publicly (ADR-0004 §2) so the CLI imports a curated surface, not internals.

**Files:**
- Modify: `src/orionfold/proof/__init__.py`
- Test: `tests/unit/test_runner.py` (add one import-surface test)

**Interfaces:**
- Produces: `from orionfold.proof import execute_run` (and the engine primitives) as the public surface.

- [ ] **Step 1: Inspect the current `__init__.py`**

Run: `cat src/orionfold/proof/__init__.py`
Expected: it is empty or only a docstring (note its current contents before editing).

- [ ] **Step 2: Write the failing test**

Append to `tests/unit/test_runner.py`:

```python
def test_proof_package_public_surface() -> None:
    import orionfold.proof as proof

    assert "execute_run" in proof.__all__
    # The engine primitives are part of the curated public surface too.
    for name in ("run_proof", "run_matrix", "iter_matrix", "config_hash", "build_cost_summary"):
        assert name in proof.__all__, name
        assert hasattr(proof, name), name
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_runner.py::test_proof_package_public_surface -v`
Expected: FAIL — `AttributeError: module 'orionfold.proof' has no attribute '__all__'`

- [ ] **Step 4: Write the implementation**

Replace the contents of `src/orionfold/proof/__init__.py` with (preserve any existing module docstring at the top if present):

```python
"""Proof core — the run engine, the run stitch, and the cross-run primitives.

This package's ``__all__`` is the curated public surface (ADR-0004 §2). Consumers import from
here (``from orionfold.proof import execute_run``); names not listed are internal.
"""

from orionfold.proof.engine import (
    build_cost_summary,
    config_hash,
    iter_matrix,
    run_matrix,
    run_proof,
)
from orionfold.proof.runner import execute_run

__all__ = [
    "execute_run",
    "run_proof",
    "run_matrix",
    "iter_matrix",
    "config_hash",
    "build_cost_summary",
]
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/unit/test_runner.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Full suite — confirm no import cycle / regression**

Run: `uv run pytest tests/unit -q`
Expected: PASS (all unit tests; the new `__init__` must not break existing imports).

- [ ] **Step 7: Commit**

```bash
git add src/orionfold/proof/__init__.py tests/unit/test_runner.py
git commit -m "feat(proof): curate the proof package public surface (__all__)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: The `orionfold run` CLI command

Add the thin Typer wrapper: load a dataset file → `execute_run()` → emit a receipt (and optionally persist).

**Files:**
- Modify: `src/orionfold/cli.py`
- Create: `tests/fixtures/run_slice_dataset.jsonl`
- Create: `tests/unit/test_cli_run.py`

**Interfaces:**
- Consumes:
  - `execute_run(*, dataset, candidate_ids, brief, rubric=None, mode="full") -> ProofReport` from `orionfold.proof`
  - `parse_dataset(text: str, fmt: ImportFormat) -> ParseResult` from `orionfold.data.importers` (`ParseResult.examples: list[Example]`)
  - `Dataset`, `ProofBrief`, `Rubric` from `orionfold.domain.models`
  - `to_json(report) -> str`, `to_markdown(report) -> str`, `to_html(report, theme=None) -> str` from `orionfold.receipts.export`
  - `connect(path) -> sqlite3.Connection`, `default_db_path() -> Path` from `orionfold.storage.db`; `save_report(conn, report) -> None` from `orionfold.storage.repository`
- Produces: the `run` CLI command (a Typer command on the existing `app`).

- [ ] **Step 1: Create the fixture**

Create `tests/fixtures/run_slice_dataset.jsonl`:

```jsonl
{"input": "ping", "expected": "ping"}
{"input": "hello world", "expected": "hello world"}
{"input": "orionfold", "expected": "orionfold"}
```

> Note: confirm the JSONL key names the importer expects by checking `tests/unit/test_importers.py` and `src/orionfold/data/importers.py::_parse_jsonl`. If the importer expects `input_text`/`expected_text` (or other keys), update this fixture to match before running — the importer's keys are authoritative.

- [ ] **Step 2: Write the failing CLI tests**

Create `tests/unit/test_cli_run.py`:

```python
"""`orionfold run` — headless end-to-end over keyless mock candidates."""

import json
from pathlib import Path

from typer.testing import CliRunner

from orionfold.cli import app

runner = CliRunner()
FIXTURE = Path(__file__).parent.parent / "fixtures" / "run_slice_dataset.jsonl"


def test_help_lists_run() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.stdout


def test_run_emits_json_receipt(tmp_path, monkeypatch) -> None:
    # Isolate the DB so the test never writes the real ~/.orionfold/proof.db.
    monkeypatch.setenv("ORIONFOLD_DB", str(tmp_path / "test.db"))
    result = runner.invoke(
        app,
        [
            "run",
            "--dataset", str(FIXTURE),
            "--candidates", "mock_good,mock_bad",
            "--format", "json",
        ],
    )
    assert result.exit_code == 0, result.stdout
    # stdout is a valid receipt JSON with both candidates.
    payload = json.loads(result.stdout)
    labels = json.dumps(payload)
    assert "mock_good" in labels and "mock_bad" in labels


def test_run_writes_to_out_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ORIONFOLD_DB", str(tmp_path / "test.db"))
    out = tmp_path / "receipt.md"
    result = runner.invoke(
        app,
        [
            "run",
            "--dataset", str(FIXTURE),
            "--candidates", "mock_good,mock_bad",
            "--format", "markdown",
            "--out", str(out),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert out.exists()
    text = out.read_text()
    # A Markdown receipt has a heading and names a winner section.
    assert text.lstrip().startswith("#")


def test_run_unknown_candidate_errors_cleanly(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ORIONFOLD_DB", str(tmp_path / "test.db"))
    result = runner.invoke(
        app,
        ["run", "--dataset", str(FIXTURE), "--candidates", "no_such_provider"],
    )
    assert result.exit_code != 0
    # The error is a clean message, not a traceback.
    assert "Traceback" not in result.stdout


def test_run_receipt_is_secret_free(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ORIONFOLD_DB", str(tmp_path / "test.db"))
    result = runner.invoke(
        app,
        ["run", "--dataset", str(FIXTURE), "--candidates", "mock_good", "--format", "json"],
    )
    assert result.exit_code == 0, result.stdout
    # No API-key-shaped material in the output (mocks carry none, but assert the invariant).
    for needle in ("sk-", "api_key", "API_KEY", "Bearer "):
        assert needle not in result.stdout
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_cli_run.py -v`
Expected: FAIL — `test_help_lists_run` fails (no `run` command) and the run tests error (no such command).

- [ ] **Step 4: Implement the `run` command**

Add to `src/orionfold/cli.py` (after the `dev` command, before `if __name__`). Add the imports at the top of the file with the other imports:

```python
# --- add to the top-of-file imports ---
from pathlib import Path

from orionfold.data.importers import DatasetParseError, parse_dataset
from orionfold.domain.models import Dataset, ProofBrief, Rubric
from orionfold.proof import execute_run
from orionfold.providers.registry import UnknownCandidateError
from orionfold.receipts import export
from orionfold.storage.db import connect, default_db_path
from orionfold.storage.repository import save_report
```

```python
# --- add as a new command ---
_FORMAT_RENDERERS = {
    "json": export.to_json,
    "markdown": export.to_markdown,
    "html": export.to_html,
}


@app.command()
def run(
    dataset: Path = typer.Option(..., "--dataset", help="Path to a dataset file (.jsonl/.csv/.md)."),
    candidates: str = typer.Option(
        ..., "--candidates", help="Comma-separated candidate ids, e.g. 'mock_good,mock_bad'."
    ),
    rubric_kind: str | None = typer.Option(
        None, "--rubric", help="Scoring kind (exact/contains/similarity/keypoint). Default: auto."
    ),
    output_format: str = typer.Option(
        "markdown", "--format", help="Receipt format: markdown | json | html."
    ),
    out: Path | None = typer.Option(None, "--out", help="Write the receipt here (default: stdout)."),
    no_save: bool = typer.Option(False, "--no-save", help="Do not persist the run to the local DB."),
) -> None:
    """Run a proof headlessly and emit a receipt (the engineer/researcher path)."""
    if output_format not in _FORMAT_RENDERERS:
        typer.echo(f"Unknown --format '{output_format}' (use markdown|json|html).", err=True)
        raise typer.Exit(code=2)

    # Load + parse the dataset by file extension.
    fmt_by_ext = {".jsonl": "jsonl", ".csv": "csv", ".md": "markdown", ".markdown": "markdown"}
    fmt = fmt_by_ext.get(dataset.suffix.lower())
    if fmt is None:
        typer.echo(f"Unsupported dataset extension '{dataset.suffix}'.", err=True)
        raise typer.Exit(code=2)
    try:
        parsed = parse_dataset(dataset.read_text(encoding="utf-8"), fmt)  # type: ignore[arg-type]
    except (OSError, DatasetParseError) as exc:
        typer.echo(f"Could not read dataset: {exc}", err=True)
        raise typer.Exit(code=1)

    ds = Dataset(id=dataset.stem, name=dataset.stem, examples=parsed.examples)
    candidate_ids = [c.strip() for c in candidates.split(",") if c.strip()]
    brief = ProofBrief(
        task_name=dataset.stem,
        decision_question=f"Which candidate is worth trusting on {dataset.stem}?",
    )
    rubric = Rubric(kind=rubric_kind) if rubric_kind else None  # type: ignore[arg-type]

    try:
        report = execute_run(dataset=ds, candidate_ids=candidate_ids, brief=brief, rubric=rubric)
    except UnknownCandidateError as exc:
        typer.echo(f"Candidate error: {exc}", err=True)
        raise typer.Exit(code=1)

    if not no_save:
        conn = connect(default_db_path())
        try:
            save_report(conn, report)
        finally:
            conn.close()

    rendered = _FORMAT_RENDERERS[output_format](report)
    if out is not None:
        out.write_text(rendered, encoding="utf-8")
        typer.echo(f"Receipt written to {out}", err=True)
    else:
        typer.echo(rendered)
```

> Implementation notes for the engineer:
> - `parse_dataset`'s `fmt` is a `Literal["jsonl","csv","markdown"]`; the `# type: ignore[arg-type]` covers the `str`→`Literal` narrowing from the dict lookup (or use `typing.cast(ImportFormat, fmt)` importing `ImportFormat` from `orionfold.data.importers`).
> - `Rubric(kind=...)` similarly narrows `str`→`RubricKind`; prefer `cast` if you want to avoid the ignore. An invalid kind raises a Pydantic `ValidationError` — acceptable for v1 (surfaces as a non-zero exit). If you want a friendly message, wrap the `Rubric(...)` build in try/except `ValidationError` → `typer.Exit(2)`; not required for this slice.
> - Receipt text goes to **stdout** (so it pipes); status lines (`Receipt written to …`) go to **stderr** so they never pollute a piped receipt — this is why the JSON test parses `result.stdout` directly.

- [ ] **Step 5: Run the CLI tests to verify they pass**

Run: `uv run pytest tests/unit/test_cli_run.py -v`
Expected: PASS (5 tests). If `test_run_writes_to_out_file` fails on the leading-`#` assertion, inspect a rendered receipt (`uv run pytest -s` and print) and adjust the assertion to a stable substring from `to_markdown`'s output.

- [ ] **Step 6: Type + lint**

Run: `uv run ruff check src/orionfold/cli.py tests/unit/test_cli_run.py && uv run pyright src/orionfold/cli.py`
Expected: no new errors (pre-existing baseline errors elsewhere are out of scope — check only these files).

- [ ] **Step 7: Commit**

```bash
git add src/orionfold/cli.py tests/unit/test_cli_run.py tests/fixtures/run_slice_dataset.jsonl
git commit -m "feat(cli): orionfold run — headless proof workflow to a receipt

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Route uses the shared core (remove the duplicated stitch)

Prove the "one core, two shells" claim: refactor `create_run` to call `execute_run()` so the route and CLI share the stitch. The route keeps HTTP validation, the judge pre-check, persistence, and the `mode` set.

**Files:**
- Modify: `src/orionfold/server/routes.py` (the `create_run` handler, ~lines 441-477)

**Interfaces:**
- Consumes: `execute_run(*, dataset, candidate_ids, brief, rubric=None, mode="full") -> ProofReport`.
- Note: the route currently calls `_resolve_candidates(body)` (which fans out **prompt variants** and applies a task `system_prompt`) and resolves the rubric with **threshold overrides + check_hint**. `execute_run` does the simpler resolution. **To avoid regressing prompt-variant/threshold-override behavior, keep the route's existing resolution and pass the already-resolved objects into the engine — i.e. do NOT route prompt-variant runs through `execute_run`'s candidate-id resolution.** See the two options below.

- [ ] **Step 1: Run the existing route tests to capture the green baseline**

Run: `uv run pytest tests/unit/test_proof_api.py tests/integration -q`
Expected: PASS — record the count. This is the regression guard for this task.

- [ ] **Step 2: Choose the minimal-risk refactor**

The route resolves candidates and rubric in ways `execute_run` does not (prompt variants, task instruction, threshold overrides, check_hint, judge pre-check). The honest minimal change that still shares the *stitch* without regressing those:

**Option A (recommended for this slice): add an overload path in `execute_run` that accepts pre-resolved candidates+rubric.** Extend `runner.py` with a sibling that the route calls:

```python
# add to src/orionfold/proof/runner.py
from orionfold.domain.models import Candidate


def execute_resolved(
    *,
    dataset: Dataset,
    candidates: list[Candidate],
    rubric: Rubric,
    brief: ProofBrief,
    mode: Literal["full", "quick"] = "full",
) -> ProofReport:
    """Run the matrix from already-resolved candidates + rubric (the route's path).

    The route does its own candidate fan-out (prompt variants), threshold-override + check-hint
    rubric resolution, and judge pre-check; it then hands the resolved objects here so the
    id/timestamp generation + ``run_proof`` call live in ONE place. ``execute_run`` (the CLI path)
    resolves ids/rubric itself and delegates here.
    """
    report = run_proof(
        run_id=f"run_{uuid.uuid4().hex[:12]}",
        created_at=_now(),
        brief=brief,
        dataset=dataset,
        candidates=candidates,
        rubric=rubric,
    )
    report.run.mode = mode
    return report
```

Then refactor `execute_run` to delegate:

```python
def execute_run(*, dataset, candidate_ids, brief, rubric=None, mode="full"):
    candidates = build_candidates(candidate_ids)
    resolved_rubric = rubric or default_rubric_for(dataset)
    return execute_resolved(
        dataset=dataset, candidates=candidates, rubric=resolved_rubric, brief=brief, mode=mode
    )
```

Add `"execute_resolved"` to `proof/__init__.py`'s `__all__`.

- [ ] **Step 3: Write the failing test for `execute_resolved`**

Append to `tests/unit/test_runner.py`:

```python
def test_execute_resolved_runs_from_prebuilt_objects() -> None:
    from orionfold.domain.models import Rubric
    from orionfold.providers.registry import build_candidates
    from orionfold.proof.runner import execute_resolved

    cands = build_candidates(["mock_good"])
    report = execute_resolved(
        dataset=_DATASET,
        candidates=cands,
        rubric=Rubric(kind="exact", threshold=1.0),
        brief=_BRIEF,
    )
    assert report.run.rubric.kind == "exact"
    assert report.run.id.startswith("run_")
```

Run: `uv run pytest tests/unit/test_runner.py::test_execute_resolved_runs_from_prebuilt_objects -v`
Expected: FAIL (function not defined), then implement Step 2's code, then PASS.

- [ ] **Step 4: Refactor `create_run` to call `execute_resolved`**

In `src/orionfold/server/routes.py::create_run`, replace the inline id/timestamp + `run_proof(...)` block with a call to `execute_resolved`, **keeping** the surrounding validation, the judge pre-check, and `save_report`. The resulting handler body:

```python
@router.post("/runs")
def create_run(request: Request, body: RunRequest) -> ProofReport:
    conn = _conn(request)
    try:
        dataset = _resolve_dataset(conn, body)
        if not body.candidate_ids:
            raise HTTPException(status_code=400, detail="Select at least one candidate")
        candidates = _resolve_candidates(body)
        _meta = get_dataset_meta(conn, dataset.id)
        rubric = body.rubric or default_rubric_for(
            dataset, get_threshold_defaults(conn), check_hint=_meta.check_hint if _meta else None
        )
        if rubric.kind == "judge":
            try:
                build_judge(rubric)
            except (ValueError, KeyError) as exc:
                raise HTTPException(status_code=422, detail=f"Judge not available: {exc}")
        try:
            report = execute_resolved(
                dataset=dataset,
                candidates=candidates,
                rubric=rubric,
                brief=body.brief,
                mode=body.mode,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        save_report(conn, report)
        return report
    finally:
        conn.close()
```

Add the import at the top of `routes.py`: `from orionfold.proof import execute_resolved` (and remove the now-unused `run_proof` import **only if** nothing else in the file uses it — grep first; `config_hash`/`iter_matrix`/`build_cost_summary` are used by the streaming endpoint, leave those).

- [ ] **Step 5: Run the route + integration tests — confirm no regression**

Run: `uv run pytest tests/unit/test_proof_api.py tests/integration -q`
Expected: PASS — the **same count** as Step 1's baseline. The mock matrix `config_hash 467ddd96c9a5` must be unchanged (any test asserting it stays green).

- [ ] **Step 6: Full backend suite**

Run: `uv run pytest -q`
Expected: PASS (full suite green; record the new total — it should be the old total + the tests added in Tasks 1–3).

- [ ] **Step 7: Type + lint**

Run: `uv run ruff check src/orionfold/server/routes.py src/orionfold/proof/runner.py && uv run pyright src/orionfold/proof/runner.py`
Expected: no new errors on changed files.

- [ ] **Step 8: Commit**

```bash
git add src/orionfold/proof/runner.py src/orionfold/proof/__init__.py src/orionfold/server/routes.py tests/unit/test_runner.py
git commit -m "refactor(proof): route + CLI share execute_resolved() (one core, two shells)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: End-to-end verification + a `docs/api` stub

Prove the whole slice works as a real user would run it, and seed the public-API docs (ADR-0004 §2: "documented in `docs/api/` cards").

**Files:**
- Create: `docs/api/proof.md`

- [ ] **Step 1: Real end-to-end run from the shell (keyless)**

Run:
```bash
uv run orionfold run --dataset tests/fixtures/run_slice_dataset.jsonl --candidates mock_good,mock_bad --format markdown
```
Expected: a Markdown receipt prints to stdout naming a recommended winner; `mock_good` passes its examples (echoes expected), `mock_bad` shows at least one failure. No traceback, exit code 0.

- [ ] **Step 2: Confirm JSON receipt + persistence**

Run:
```bash
ORIONFOLD_DB=/tmp/orionfold-slice.db uv run orionfold run --dataset tests/fixtures/run_slice_dataset.jsonl --candidates mock_good,mock_bad --format json --out /tmp/slice-receipt.json
uv run python -c "import json; d=json.load(open('/tmp/slice-receipt.json')); print('OK', len(d))"
```
Expected: writes the file, the python check prints `OK <n>`; no secrets in the file.

- [ ] **Step 3: Secret-free spot check**

Run: `grep -iE 'sk-|api[_-]?key|bearer ' /tmp/slice-receipt.json || echo "secret-free ✓"`
Expected: `secret-free ✓`

- [ ] **Step 4: Write the `docs/api/proof.md` card**

Create `docs/api/proof.md`:

```markdown
# `orionfold.proof` — public API

The proof core. Import from the package root; names not in `__all__` are internal.

## Run a proof headlessly

```python
from orionfold.proof import execute_run
from orionfold.domain.models import Dataset, Example, ProofBrief

dataset = Dataset(id="my-task", name="My task", examples=[
    Example(input_text="ping", expected_text="ping"),
])
report = execute_run(
    dataset=dataset,
    candidate_ids=["mock_good", "mock_bad"],   # or "anthropic:claude-haiku-4-5", etc.
    brief=ProofBrief(task_name="My task", decision_question="Which is worth trusting?"),
)
```

`report` is a `ProofReport` (leaderboard + result rows + cost summary). Render it with
`orionfold.receipts.export.to_markdown(report)` / `to_json` / `to_html`.

## Public surface

| Name | Purpose |
| --- | --- |
| `execute_run(*, dataset, candidate_ids, brief, rubric=None, mode="full")` | Resolve ids+rubric, run the matrix, return the report (the CLI path). |
| `execute_resolved(*, dataset, candidates, rubric, brief, mode="full")` | Run from pre-resolved candidates+rubric (the web route's path). |
| `run_proof`, `run_matrix`, `iter_matrix`, `config_hash`, `build_cost_summary` | Engine primitives. |

The `orionfold run` CLI command is a thin wrapper over `execute_run`.
```

- [ ] **Step 5: Commit**

```bash
git add docs/api/proof.md
git commit -m "docs(api): proof package public-API card

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 6: Re-embed guard (only if a build is needed)**

This slice touches no frontend; the embedded cockpit static dir is unaffected. No re-embed needed. (If `pyright`/`ruff`/the full `pytest` from Task 4 Step 6 are green, the slice is complete.)

---

## Self-Review

**Spec coverage (against ADR-0004 §8 — the vertical slice):**
- "one end-to-end CLI path `orionfold run … → receipt` calling the curated public core" → Tasks 1+3+5. ✓
- "verified headlessly with tests" → Task 3 (CliRunner) + Task 5 (real shell run). ✓
- B4 rollup / `dataset import|list` / `runs list|show` / `track-record` / threshold single-source / packaging → **explicitly out of scope** for this slice (ADR-0004 §8 "then widen"). ✓ (Not gaps — deferred by design.)
- "curated public API surface" (ADR-0004 §2) → Task 2 (`proof/__init__.py` `__all__`) + Task 5 (`docs/api/proof.md`). ✓
- "each CLI command is a thin wrapper over the public API" (ADR-0004 §3) → Task 3 (the command body just loads a file, calls `execute_run`, renders) + Task 4 (route shares the same core). ✓

**Placeholder scan:** No "TBD"/"handle edge cases"/"write tests for the above" — every code step shows complete code; every test step shows the assertions. The two `# type: ignore` notes are explained inline with a `cast` alternative. ✓

**Type consistency:** `execute_run(*, dataset, candidate_ids, brief, rubric=None, mode="full")` and `execute_resolved(*, dataset, candidates, rubric, brief, mode="full")` are used identically in Tasks 1, 3, 4, 5. `parse_dataset(text, fmt) -> ParseResult` with `.examples` used in Task 3. `to_json/to_markdown/to_html(report)` used in Task 3+5. `connect`/`default_db_path`/`save_report` signatures match the extracted verbatim sources. ✓

**Two flagged verify-at-implementation items (not placeholders — they're "confirm the existing contract"):**
1. Task 3 Step 1 — confirm the JSONL importer's expected key names (`input`/`expected` vs `input_text`/`expected_text`) against `data/importers.py::_parse_jsonl` + `test_importers.py`, and align the fixture. (The plan says exactly how to check.)
2. Task 3 Step 5 — if the Markdown receipt's leading-character assertion is brittle, swap to a stable substring from `to_markdown`'s real output (the plan says how).
