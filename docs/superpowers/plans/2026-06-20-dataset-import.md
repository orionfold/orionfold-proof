# Dataset Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user import their own dataset (JSONL / CSV / Markdown, via file or paste) through a preview → confirm → freeze flow in the Datasets view, closing the v0 charter gap (review finding #9).

**Architecture:** A new pure backend parser module produces validated `Example` pairs + warnings; a repository `save_dataset` persists a new dataset (name-unique, slug id); two additive FastAPI routes expose preview (no write) and create (parses server-side, saves). The frontend adds an inline collapsible import panel in the Datasets view that previews parsed pairs before freezing, reusing the existing TanStack-Query mutation + Zod-at-the-boundary patterns.

**Tech Stack:** Python 3.12 · FastAPI · Pydantic · stdlib `csv`/`json`/`re` · SQLite · pytest · React · TypeScript · TanStack Query · Zod · Vitest · Playwright.

## Global Constraints

- Backend parser is **pure and keyless** — no network, no secrets, deterministic.
- **At least one valid example** is required; zero valid → parse error (HTTP **422**). Duplicate dataset **name** (case-insensitive) → HTTP **409**.
- Datasets are immutable-by-convention: import **creates** only. No edit/delete, no `frozen` column, **no schema migration** (migrations are append-only per `.claude/rules/storage.md`; this feature adds none).
- Server stays **JSON-only** — the browser reads uploaded file text via `FileReader`; no multipart.
- Zod validates every API response at the frontend boundary (`web/src/lib/api.ts` convention).
- Tailwind v4: CSS vars use the **parenthesis** shorthand `bg-(--color-x)`, never `bg-[--color-x]`.
- Do **not** regress existing test-contract strings, the Proof Run default view, the 3-format receipt, `RECEIPT_VERSION` (3), or the batch/stream run endpoints. This work is purely additive.
- Commit after each task with passing checks. Backend gate: `uv run pytest` + `uv run ruff check` + `uv run pyright`. Frontend gate: `pnpm --dir web test` + `pnpm --dir web build`.

---

### Task 1: Backend parser module (`importers.py`)

**Files:**
- Create: `src/orionfold/data/importers.py`
- Test: `tests/unit/test_importers.py`

**Interfaces:**
- Consumes: `orionfold.domain.models.Example` (`{input_text: str, expected_text: str}`).
- Produces:
  - `ImportFormat = Literal["jsonl", "csv", "markdown"]`
  - `class ParseResult(BaseModel)`: `examples: list[Example]`, `warnings: list[str]`, `count: int`
  - `class DatasetParseError(ValueError)`
  - `parse_dataset(text: str, fmt: ImportFormat) -> ParseResult` — raises `DatasetParseError` when no valid example is found.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_importers.py`:

```python
import pytest

from orionfold.data.importers import DatasetParseError, parse_dataset


def test_jsonl_parses_both_key_spellings():
    text = (
        '{"input": "a", "expected": "b"}\n'
        '{"input_text": "c", "expected_text": "d"}\n'
    )
    r = parse_dataset(text, "jsonl")
    assert r.count == 2
    assert r.examples[0].input_text == "a" and r.examples[0].expected_text == "b"
    assert r.examples[1].input_text == "c" and r.examples[1].expected_text == "d"
    assert r.warnings == []


def test_jsonl_skips_malformed_and_blank_lines_with_warnings():
    text = '{"input": "a", "expected": "b"}\n\nnot json\n{"input": "x"}\n'
    r = parse_dataset(text, "jsonl")
    assert r.count == 1
    assert any("Line 3" in w for w in r.warnings)  # not json
    assert any("Line 4" in w for w in r.warnings)  # missing expected


def test_csv_case_insensitive_headers():
    text = "Input,Expected\nhello,world\n"
    r = parse_dataset(text, "csv")
    assert r.count == 1
    assert r.examples[0].input_text == "hello"
    assert r.examples[0].expected_text == "world"


def test_csv_missing_columns_yields_no_examples_and_errors():
    with pytest.raises(DatasetParseError):
        parse_dataset("foo,bar\n1,2\n", "csv")


def test_csv_skips_rows_missing_a_value():
    text = "input,expected\na,b\n,d\ne,\n"
    r = parse_dataset(text, "csv")
    assert r.count == 1
    assert len(r.warnings) == 2


def test_markdown_heading_pairs_with_multiline_prose():
    text = (
        "## Input\nline one\nline two\n\n## Expected\nsummary\n\n---\n\n"
        "## Input\nsecond\n\n## Expected\nsecond out\n"
    )
    r = parse_dataset(text, "markdown")
    assert r.count == 2
    assert r.examples[0].input_text == "line one\nline two"
    assert r.examples[0].expected_text == "summary"
    assert r.examples[1].input_text == "second"


def test_markdown_input_without_expected_warns_and_skips():
    text = "## Input\nonly input\n\n---\n\n## Input\ngood\n## Expected\nok\n"
    r = parse_dataset(text, "markdown")
    assert r.count == 1
    assert any("Example 1" in w for w in r.warnings)


def test_markdown_headings_are_case_and_level_insensitive():
    text = "# input\nx\n### EXPECTED\ny\n"
    r = parse_dataset(text, "markdown")
    assert r.count == 1


def test_whitespace_only_fields_are_skipped():
    r_jsonl = parse_dataset('{"input": "  ", "expected": "ok"}\n{"input":"a","expected":"b"}\n', "jsonl")
    assert r_jsonl.count == 1


def test_zero_valid_examples_raises():
    with pytest.raises(DatasetParseError):
        parse_dataset("\n\n", "jsonl")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_importers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'orionfold.data.importers'`.

- [ ] **Step 3: Write the parser module**

Create `src/orionfold/data/importers.py`:

```python
"""Dataset importers — turn user-supplied JSONL / CSV / Markdown text into frozen example
pairs. Pure and keyless: no network, no secrets, deterministic. Each parser skips rows it
cannot read (recording a warning) and the entry point refuses input that yields no example.
"""

from __future__ import annotations

import csv
import io
import json
import re
from typing import Literal

from pydantic import BaseModel

from orionfold.domain.models import Example

ImportFormat = Literal["jsonl", "csv", "markdown"]


class ParseResult(BaseModel):
    """Parsed examples plus per-row warnings (skipped lines) and the valid count."""

    examples: list[Example]
    warnings: list[str]
    count: int


class DatasetParseError(ValueError):
    """No valid example could be parsed — surfaced to the API as HTTP 422."""


def parse_dataset(text: str, fmt: ImportFormat) -> ParseResult:
    if fmt == "jsonl":
        examples, warnings = _parse_jsonl(text)
    elif fmt == "csv":
        examples, warnings = _parse_csv(text)
    elif fmt == "markdown":
        examples, warnings = _parse_markdown(text)
    else:  # defensive — the Literal makes this unreachable for typed callers
        raise DatasetParseError(f"Unknown format: {fmt}")
    if not examples:
        raise DatasetParseError(
            "No valid examples found. Each example needs a non-empty input and expected value."
        )
    return ParseResult(examples=examples, warnings=warnings, count=len(examples))


def _pair_from_obj(obj: dict) -> tuple[str, str] | None:
    """Pull a trimmed (input, expected) from a dict, accepting both key spellings."""
    raw_in = obj.get("input", obj.get("input_text", ""))
    raw_out = obj.get("expected", obj.get("expected_text", ""))
    if not isinstance(raw_in, str) or not isinstance(raw_out, str):
        return None
    input_text, expected_text = raw_in.strip(), raw_out.strip()
    if not input_text or not expected_text:
        return None
    return input_text, expected_text


def _parse_jsonl(text: str) -> tuple[list[Example], list[str]]:
    examples: list[Example] = []
    warnings: list[str] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            warnings.append(f"Line {lineno}: not valid JSON — skipped.")
            continue
        if not isinstance(obj, dict):
            warnings.append(f"Line {lineno}: expected a JSON object — skipped.")
            continue
        pair = _pair_from_obj(obj)
        if pair is None:
            warnings.append(f"Line {lineno}: missing input/expected — skipped.")
            continue
        examples.append(Example(input_text=pair[0], expected_text=pair[1]))
    return examples, warnings


def _parse_csv(text: str) -> tuple[list[Example], list[str]]:
    examples: list[Example] = []
    warnings: list[str] = []
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return examples, warnings
    headers = {(name or "").strip().lower(): name for name in reader.fieldnames}
    input_key = headers.get("input", headers.get("input_text"))
    expected_key = headers.get("expected", headers.get("expected_text"))
    if input_key is None or expected_key is None:
        warnings.append("CSV needs 'input' and 'expected' columns — none found.")
        return examples, warnings
    for rowno, row in enumerate(reader, start=2):  # row 1 is the header
        input_text = (row.get(input_key) or "").strip()
        expected_text = (row.get(expected_key) or "").strip()
        if not input_text or not expected_text:
            warnings.append(f"Row {rowno}: missing input/expected — skipped.")
            continue
        examples.append(Example(input_text=input_text, expected_text=expected_text))
    return examples, warnings


_HEADING = re.compile(r"^#{1,6}\s+(.*\S)\s*$")
_RULE = re.compile(r"^-{3,}\s*$")


def _parse_markdown(text: str) -> tuple[list[Example], list[str]]:
    # First pass: split into (label, content-lines) sections on headings; a horizontal rule
    # ends the current section. Only content under an Input/Expected heading is kept.
    sections: list[tuple[str, list[str]]] = []
    label: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if label is not None:
            sections.append((label, buffer.copy()))

    for raw in text.splitlines():
        heading = _HEADING.match(raw)
        if heading:
            flush()
            label = heading.group(1).strip().lower()
            buffer = []
        elif _RULE.match(raw):
            flush()
            label = None
            buffer = []
        elif label is not None:
            buffer.append(raw)
    flush()

    # Second pass: pair each 'input' section with the immediately following 'expected'.
    examples: list[Example] = []
    warnings: list[str] = []
    idx = 0
    example_no = 0
    while idx < len(sections):
        section_label, content = sections[idx]
        if section_label == "input":
            example_no += 1
            has_expected = idx + 1 < len(sections) and sections[idx + 1][0] == "expected"
            if has_expected:
                input_text = "\n".join(content).strip()
                expected_text = "\n".join(sections[idx + 1][1]).strip()
                if input_text and expected_text:
                    examples.append(
                        Example(input_text=input_text, expected_text=expected_text)
                    )
                else:
                    warnings.append(f"Example {example_no}: empty input or expected — skipped.")
                idx += 2
                continue
            warnings.append(
                f"Example {example_no}: 'Input' without a following 'Expected' — skipped."
            )
        idx += 1
    return examples, warnings
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_importers.py -v`
Expected: PASS (all 10).

- [ ] **Step 5: Lint, type-check, commit**

Run: `uv run ruff check src/orionfold/data/importers.py tests/unit/test_importers.py && uv run pyright src/orionfold/data/importers.py`
Expected: clean.

```bash
git add src/orionfold/data/importers.py tests/unit/test_importers.py
git commit -m "feat(data): dataset importers for JSONL/CSV/Markdown"
```

---

### Task 2: Repository `save_dataset` + name-uniqueness

**Files:**
- Modify: `src/orionfold/storage/repository.py`
- Test: `tests/unit/test_storage.py` (append)

**Interfaces:**
- Consumes: `Example` (Task 1 already imports it from domain), `Dataset`, the `datasets` table.
- Produces:
  - `class DuplicateDatasetError(ValueError)`
  - `save_dataset(conn, name: str, description: str, examples: list[Example]) -> Dataset` — raises `DuplicateDatasetError` on a case-insensitive name clash; assigns a unique slug `id`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_storage.py` (add imports at the top of the file if missing: `import pytest`, and from the repository module `save_dataset`, `DuplicateDatasetError`; from domain `Example`):

```python
def test_save_dataset_persists_and_slugs_id(tmp_path):
    from orionfold.storage.db import apply_migrations, connect
    from orionfold.storage.repository import get_dataset, save_dataset
    from orionfold.domain.models import Example

    conn = connect(tmp_path / "t.db")
    apply_migrations(conn)
    saved = save_dataset(conn, "My Memo Set!", "", [Example(input_text="a", expected_text="b")])
    assert saved.id == "my-memo-set"
    assert get_dataset(conn, "my-memo-set").name == "My Memo Set!"


def test_save_dataset_rejects_duplicate_name_case_insensitively(tmp_path):
    from orionfold.storage.db import apply_migrations, connect
    from orionfold.storage.repository import DuplicateDatasetError, save_dataset
    from orionfold.domain.models import Example

    conn = connect(tmp_path / "t.db")
    apply_migrations(conn)
    save_dataset(conn, "Memos", "", [Example(input_text="a", expected_text="b")])
    with pytest.raises(DuplicateDatasetError):
        save_dataset(conn, "  memos ", "", [Example(input_text="c", expected_text="d")])


def test_save_dataset_dedups_id_for_distinct_names(tmp_path):
    from orionfold.storage.db import apply_migrations, connect
    from orionfold.storage.repository import save_dataset
    from orionfold.domain.models import Example

    conn = connect(tmp_path / "t.db")
    apply_migrations(conn)
    a = save_dataset(conn, "My Set", "", [Example(input_text="a", expected_text="b")])
    b = save_dataset(conn, "My Set!", "", [Example(input_text="c", expected_text="d")])
    assert a.id == "my-set"
    assert b.id == "my-set-2"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_storage.py -k save_dataset -v`
Expected: FAIL — `ImportError: cannot import name 'save_dataset'`.

- [ ] **Step 3: Implement `save_dataset`**

In `src/orionfold/storage/repository.py`, add `import re` near the top (after `import sqlite3`), add `Example` to the domain import (`from orionfold.domain.models import Dataset, Example, ProofReport`), and add:

```python
class DuplicateDatasetError(ValueError):
    """A dataset with the same name already exists — surfaced to the API as HTTP 409."""


def save_dataset(
    conn: sqlite3.Connection, name: str, description: str, examples: list[Example]
) -> Dataset:
    """Create a new dataset. Name must be unique (case-insensitive); id is a unique slug."""
    name = name.strip()
    if not name:
        raise ValueError("Dataset name is required.")
    clash = conn.execute(
        "SELECT 1 FROM datasets WHERE lower(name) = lower(?)", (name,)
    ).fetchone()
    if clash is not None:
        raise DuplicateDatasetError(f"A dataset named '{name}' already exists.")
    dataset = Dataset(
        id=_unique_id(conn, name),
        name=name,
        description=description.strip(),
        examples=examples,
    )
    conn.execute(
        "INSERT INTO datasets (id, name, description, examples) VALUES (?, ?, ?, ?)",
        (dataset.id, dataset.name, dataset.description, _examples_json(dataset)),
    )
    conn.commit()
    return dataset


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "dataset"


def _unique_id(conn: sqlite3.Connection, name: str) -> str:
    base = _slug(name)
    candidate, n = base, 1
    while conn.execute("SELECT 1 FROM datasets WHERE id = ?", (candidate,)).fetchone():
        n += 1
        candidate = f"{base}-{n}"
    return candidate
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_storage.py -k save_dataset -v`
Expected: PASS (3).

- [ ] **Step 5: Full backend gate + commit**

Run: `uv run pytest && uv run ruff check src/orionfold/storage/repository.py tests/unit/test_storage.py && uv run pyright src/orionfold/storage/repository.py`
Expected: all green.

```bash
git add src/orionfold/storage/repository.py tests/unit/test_storage.py
git commit -m "feat(storage): save_dataset with name-uniqueness and slug ids"
```

---

### Task 3: Preview + create endpoints

**Files:**
- Modify: `src/orionfold/server/routes.py`
- Test: `tests/integration/test_proof_api.py` (append)

**Interfaces:**
- Consumes: `parse_dataset`, `ParseResult`, `DatasetParseError`, `ImportFormat` (Task 1); `save_dataset`, `DuplicateDatasetError` (Task 2).
- Produces HTTP:
  - `POST /api/datasets/preview` body `{format, text}` → `ParseResult` (200) | 422.
  - `POST /api/datasets` body `{name, description?, format, text}` → `Dataset` (201) | 422 | 409.

- [ ] **Step 1: Write the failing tests**

Append to `tests/integration/test_proof_api.py`:

```python
def test_preview_dataset_returns_pairs_without_writing(client):
    before = len(client.get("/api/datasets").json())
    resp = client.post(
        "/api/datasets/preview",
        json={"format": "jsonl", "text": '{"input":"a","expected":"b"}\nbad\n'},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["examples"][0]["input_text"] == "a"
    assert len(body["warnings"]) == 1
    # No write happened.
    assert len(client.get("/api/datasets").json()) == before


def test_preview_zero_valid_is_422(client):
    resp = client.post("/api/datasets/preview", json={"format": "jsonl", "text": "\n\n"})
    assert resp.status_code == 422


def test_create_dataset_round_trips_and_appears_in_list(client):
    resp = client.post(
        "/api/datasets",
        json={
            "name": "Client Summaries",
            "format": "csv",
            "text": "input,expected\nhello,world\n",
        },
    )
    assert resp.status_code == 201
    created = resp.json()
    assert created["id"] == "client-summaries"
    assert created["examples"] == [{"input_text": "hello", "expected_text": "world"}]
    ids = {d["id"] for d in client.get("/api/datasets").json()}
    assert "client-summaries" in ids


def test_create_duplicate_name_is_409(client):
    body = {"name": "Dupe", "format": "jsonl", "text": '{"input":"a","expected":"b"}'}
    assert client.post("/api/datasets", json=body).status_code == 201
    assert client.post("/api/datasets", json=body).status_code == 409


def test_create_zero_valid_is_422(client):
    resp = client.post(
        "/api/datasets", json={"name": "Empty", "format": "jsonl", "text": "\n"}
    )
    assert resp.status_code == 422
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/integration/test_proof_api.py -k dataset -v`
Expected: FAIL — preview returns 404/405 (route missing) / create asserts fail.

- [ ] **Step 3: Add the routes**

In `src/orionfold/server/routes.py`:

Extend the imports:
```python
from orionfold.data.importers import DatasetParseError, ImportFormat, ParseResult, parse_dataset
from orionfold.domain.models import Candidate, Dataset, ProofBrief, ProofReport, ProofRun, Rubric
from orionfold.storage.repository import (
    DuplicateDatasetError,
    get_dataset,
    get_report,
    list_datasets,
    list_runs,
    save_dataset,
    save_report,
    seed_datasets,
)
```

Add request models near `RunRequest`:
```python
class DatasetPreviewRequest(BaseModel):
    format: ImportFormat
    text: str


class DatasetCreateRequest(BaseModel):
    name: str
    description: str = ""
    format: ImportFormat
    text: str
```

Add the routes after `get_datasets`:
```python
@router.post("/datasets/preview")
def preview_dataset(body: DatasetPreviewRequest) -> ParseResult:
    """Parse the supplied text and return the pairs + warnings. Never writes."""
    try:
        return parse_dataset(body.text, body.format)
    except DatasetParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/datasets", status_code=201)
def create_dataset(request: Request, body: DatasetCreateRequest) -> Dataset:
    """Re-parse server-side (source of truth), then freeze into a new dataset."""
    try:
        result = parse_dataset(body.text, body.format)
    except DatasetParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    conn = _conn(request)
    try:
        return save_dataset(conn, body.name, body.description, result.examples)
    except DuplicateDatasetError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    finally:
        conn.close()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/integration/test_proof_api.py -k dataset -v`
Expected: PASS (5).

- [ ] **Step 5: Full backend gate + commit**

Run: `uv run pytest && uv run ruff check src/orionfold/server/routes.py && uv run pyright src/orionfold/server/routes.py`
Expected: all green (full suite, no regressions).

```bash
git add src/orionfold/server/routes.py tests/integration/test_proof_api.py
git commit -m "feat(api): dataset preview + create endpoints (422 empty, 409 dup)"
```

---

### Task 4: Frontend API client (`previewDataset`, `createDataset`)

**Files:**
- Modify: `web/src/lib/api.ts`
- Test: Create `web/src/lib/api.test.ts`

**Interfaces:**
- Consumes: the Task 3 endpoints; existing `exampleSchema`, `datasetSchema`.
- Produces:
  - `ImportFormat` (zod enum + type), `parseResultSchema`, `ParseResult` type.
  - `previewDataset({ format, text }) -> Promise<ParseResult>`
  - `createDataset({ name, description?, format, text }) -> Promise<Dataset>`

- [ ] **Step 1: Write the failing tests**

Create `web/src/lib/api.test.ts`:

```typescript
import { afterEach, expect, test, vi } from "vitest";

import { createDataset, previewDataset } from "./api";

afterEach(() => vi.restoreAllMocks());

function mockResponse(body: unknown, ok = true, status = 200) {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(body), { status: ok ? status : status }),
  );
}

test("previewDataset returns the validated ParseResult", async () => {
  mockResponse({ examples: [{ input_text: "a", expected_text: "b" }], warnings: ["w"], count: 1 });
  const r = await previewDataset({ format: "jsonl", text: '{"input":"a","expected":"b"}' });
  expect(r.count).toBe(1);
  expect(r.warnings).toEqual(["w"]);
});

test("createDataset surfaces the server detail on error", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "A dataset named 'X' already exists." }), { status: 409 }),
  );
  await expect(
    createDataset({ name: "X", format: "jsonl", text: '{"input":"a","expected":"b"}' }),
  ).rejects.toThrow(/already exists/);
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pnpm --dir web test -- api.test`
Expected: FAIL — `previewDataset`/`createDataset` are not exported.

- [ ] **Step 3: Add the client functions**

In `web/src/lib/api.ts`, after the `datasetSchema`/`Dataset` block add:

```typescript
export const importFormatSchema = z.enum(["jsonl", "csv", "markdown"]);
export type ImportFormat = z.infer<typeof importFormatSchema>;

export const parseResultSchema = z.object({
  examples: z.array(exampleSchema),
  warnings: z.array(z.string()),
  count: z.number(),
});
export type ParseResult = z.infer<typeof parseResultSchema>;
```

And after `getDatasets` add:

```typescript
export async function previewDataset(body: {
  format: ImportFormat;
  text: string;
}): Promise<ParseResult> {
  const res = await fetch("/api/datasets/preview", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Preview failed (HTTP ${res.status})`);
  }
  return parseResultSchema.parse(await res.json());
}

export async function createDataset(body: {
  name: string;
  description?: string;
  format: ImportFormat;
  text: string;
}): Promise<Dataset> {
  const res = await fetch("/api/datasets", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Import failed (HTTP ${res.status})`);
  }
  return datasetSchema.parse(await res.json());
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pnpm --dir web test -- api.test`
Expected: PASS (2).

- [ ] **Step 5: Build + commit**

Run: `pnpm --dir web build`
Expected: tsc + vite clean.

```bash
git add web/src/lib/api.ts web/src/lib/api.test.ts
git commit -m "feat(web): previewDataset + createDataset API client"
```

---

### Task 5: Import panel UI + Datasets view wiring

**Files:**
- Modify: `web/src/features/proof/ViewShell.tsx` (add optional `action` slot)
- Create: `web/src/features/proof/DatasetImportPanel.tsx`
- Modify: `web/src/features/proof/DatasetsView.tsx` (toggle + mount panel)
- Test: Create `web/src/features/proof/DatasetImportPanel.test.tsx`

**Interfaces:**
- Consumes: `previewDataset`, `createDataset`, `ImportFormat`, `ParseResult` (Task 4); `ViewShell` `action` slot.
- Produces: `DatasetImportPanel({ onClose }: { onClose: () => void })`.

- [ ] **Step 1: Write the failing component test**

Create `web/src/features/proof/DatasetImportPanel.test.tsx`:

```tsx
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { DatasetImportPanel } from "./DatasetImportPanel";
import { renderWithQuery } from "../../test/renderWithQuery";
import * as api from "../../lib/api";

afterEach(() => vi.restoreAllMocks());

test("paste → preview → freeze calls createDataset and closes", async () => {
  vi.spyOn(api, "previewDataset").mockResolvedValue({
    examples: [{ input_text: "a", expected_text: "b" }],
    warnings: ["Line 2: not valid JSON — skipped."],
    count: 1,
  });
  vi.spyOn(api, "createDataset").mockResolvedValue({
    id: "my-set",
    name: "My Set",
    description: "",
    examples: [{ input_text: "a", expected_text: "b" }],
  });
  const onClose = vi.fn();
  renderWithQuery(<DatasetImportPanel onClose={onClose} />);

  fireEvent.change(screen.getByLabelText(/Paste or upload/i), {
    target: { value: '{"input":"a","expected":"b"}' },
  });
  fireEvent.click(screen.getByRole("button", { name: /Preview/i }));

  await waitFor(() => expect(screen.getByText(/1 example/i)).toBeVisible());
  expect(screen.getByText(/not valid JSON/)).toBeVisible();

  fireEvent.change(screen.getByLabelText(/Dataset name/i), { target: { value: "My Set" } });
  fireEvent.click(screen.getByRole("button", { name: /Freeze dataset/i }));

  await waitFor(() => expect(api.createDataset).toHaveBeenCalled());
  await waitFor(() => expect(onClose).toHaveBeenCalled());
});

test("shows the server error when preview fails", async () => {
  vi.spyOn(api, "previewDataset").mockRejectedValue(new Error("No valid examples found."));
  renderWithQuery(<DatasetImportPanel onClose={vi.fn()} />);
  fireEvent.change(screen.getByLabelText(/Paste or upload/i), { target: { value: "junk" } });
  fireEvent.click(screen.getByRole("button", { name: /Preview/i }));
  await waitFor(() => expect(screen.getByText(/No valid examples found/)).toBeVisible());
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pnpm --dir web test -- DatasetImportPanel`
Expected: FAIL — cannot find `./DatasetImportPanel`.

- [ ] **Step 3: Add the `action` slot to `ViewShell`**

Replace the `ViewShell` function body in `web/src/features/proof/ViewShell.tsx`:

```tsx
export function ViewShell({
  title,
  subtitle,
  action,
  children,
}: {
  title: string;
  subtitle: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <main className="flex flex-col gap-8 px-6 py-8 lg:px-10">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h2 className="text-xl font-semibold tracking-tight text-(--color-ink)">{title}</h2>
          <p className="max-w-prose text-sm text-(--color-ink-muted)">{subtitle}</p>
        </div>
        {action}
      </header>
      {children}
    </main>
  );
}
```

- [ ] **Step 4: Create the import panel**

Create `web/src/features/proof/DatasetImportPanel.tsx`:

```tsx
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  createDataset,
  previewDataset,
  type ImportFormat,
  type ParseResult,
} from "../../lib/api";

const FORMATS: { value: ImportFormat; label: string; hint: string }[] = [
  { value: "jsonl", label: "JSONL", hint: '{"input": "...", "expected": "..."} per line' },
  { value: "csv", label: "CSV", hint: "input,expected header + one row per example" },
  { value: "markdown", label: "Markdown", hint: "## Input / ## Expected pairs, split by ---" },
];

// Inline import: pick a format, paste or upload text, preview the parsed pairs (+ warnings),
// then freeze into a new dataset. The server re-parses on freeze, so this preview is advisory.
export function DatasetImportPanel({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [format, setFormat] = useState<ImportFormat>("jsonl");
  const [text, setText] = useState("");
  const [name, setName] = useState("");
  const [preview, setPreview] = useState<ParseResult | null>(null);

  const previewMutation = useMutation({
    mutationFn: () => previewDataset({ format, text }),
    onSuccess: setPreview,
  });
  const createMutation = useMutation({
    mutationFn: () => createDataset({ name, format, text }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["datasets"] });
      onClose();
    },
  });

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setText(await file.text());
    setPreview(null);
  }

  const hint = FORMATS.find((f) => f.value === format)?.hint ?? "";

  return (
    <section className="grid gap-4 rounded-xl border border-(--color-panel-line) bg-(--color-panel-card) p-5">
      <div className="flex flex-wrap items-center gap-2">
        {FORMATS.map((f) => (
          <button
            key={f.value}
            type="button"
            onClick={() => {
              setFormat(f.value);
              setPreview(null);
            }}
            aria-pressed={format === f.value}
            className={
              "rounded-lg border px-3 py-1.5 text-sm " +
              (format === f.value
                ? "border-(--color-accent) text-(--color-ink)"
                : "border-(--color-panel-line) text-(--color-ink-muted) hover:text-(--color-ink)")
            }
          >
            {f.label}
          </button>
        ))}
        <span className="text-xs text-(--color-ink-faint)">{hint}</span>
      </div>

      <label className="grid gap-1 text-sm">
        <span className="text-(--color-ink-muted)">Paste or upload your examples</span>
        <textarea
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setPreview(null);
          }}
          rows={6}
          className="w-full rounded-lg border border-(--color-panel-line) bg-(--color-panel) p-3 font-mono text-xs text-(--color-ink)"
          placeholder={hint}
        />
      </label>

      <div className="flex flex-wrap items-center gap-3">
        <input
          type="file"
          accept=".jsonl,.json,.csv,.md,.markdown,.txt"
          onChange={onFile}
          className="text-xs text-(--color-ink-muted)"
        />
        <button
          type="button"
          onClick={() => previewMutation.mutate()}
          disabled={!text.trim() || previewMutation.isPending}
          className="rounded-lg border border-(--color-panel-line) px-3 py-1.5 text-sm text-(--color-ink) disabled:opacity-50"
        >
          {previewMutation.isPending ? "Parsing…" : "Preview"}
        </button>
      </div>

      {previewMutation.isError && (
        <p className="text-sm text-rose-300">{(previewMutation.error as Error).message}</p>
      )}

      {preview && (
        <div className="grid gap-3">
          <p className="text-sm text-(--color-ink-muted)">
            {preview.count} example{preview.count === 1 ? "" : "s"} parsed.
          </p>
          {preview.warnings.length > 0 && (
            <ul className="grid gap-1 rounded-lg border border-dashed border-(--color-panel-line) p-3 text-xs text-(--color-ink-faint)">
              {preview.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
          <ol className="grid gap-3">
            {preview.examples.map((ex, i) => (
              <li key={i} className="grid gap-1 border-t border-(--color-panel-line) pt-3 text-sm">
                <span className="text-xs text-(--color-ink-faint)">Input</span>
                <span className="whitespace-pre-wrap text-(--color-ink)">{ex.input_text}</span>
                <span className="text-xs text-(--color-ink-faint)">Expected</span>
                <span className="whitespace-pre-wrap text-(--color-ink)">{ex.expected_text}</span>
              </li>
            ))}
          </ol>

          <label className="grid gap-1 text-sm">
            <span className="text-(--color-ink-muted)">Dataset name</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-(--color-panel-line) bg-(--color-panel) p-2 text-sm text-(--color-ink)"
              placeholder="e.g. Client summaries v1"
            />
          </label>
          {createMutation.isError && (
            <p className="text-sm text-rose-300">{(createMutation.error as Error).message}</p>
          )}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => createMutation.mutate()}
              disabled={!name.trim() || createMutation.isPending}
              className="rounded-lg bg-(--color-accent) px-3 py-1.5 text-sm font-medium text-(--color-accent-ink) disabled:opacity-50"
            >
              {createMutation.isPending ? "Freezing…" : "Freeze dataset"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-(--color-panel-line) px-3 py-1.5 text-sm text-(--color-ink-muted)"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
```

Note: confirm the accent token names (`--color-accent`, `--color-accent-ink`, `--color-panel`) against `web/src/index.css` `@theme`; if a name differs, use the actual token. If no accent-ink token exists, use `text-(--color-ink)` and a subtler `border` button instead of a filled one.

- [ ] **Step 5: Wire the toggle into `DatasetsView`**

In `web/src/features/proof/DatasetsView.tsx`: add `import { useState } from "react";` and `import { DatasetImportPanel } from "./DatasetImportPanel";`. Add panel state and pass the `action` + mount the panel:

```tsx
export function DatasetsView() {
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: getDatasets });
  const [importing, setImporting] = useState(false);

  return (
    <ViewShell
      title="Datasets"
      subtitle="The frozen example sets your candidates are proved against. Every candidate runs on the same inputs, so the comparison is fair and repeatable."
      action={
        <button
          type="button"
          onClick={() => setImporting((v) => !v)}
          className="rounded-lg border border-(--color-panel-line) px-3 py-1.5 text-sm text-(--color-ink) hover:bg-(--color-panel-line)/40"
        >
          {importing ? "Close import" : "Import dataset"}
        </button>
      }
    >
      {importing && <DatasetImportPanel onClose={() => setImporting(false)} />}
      {/* existing loading / error / empty / list block unchanged */}
```

Leave the rest of the existing render (the `datasets.isLoading ? … : …` block) exactly as-is, now sitting below the optional panel.

- [ ] **Step 6: Run the test to verify it passes**

Run: `pnpm --dir web test -- DatasetImportPanel`
Expected: PASS (2).

- [ ] **Step 7: Full frontend gate + commit**

Run: `pnpm --dir web test && pnpm --dir web build`
Expected: all units pass (App/ReceiptsView flows unaffected), tsc + vite clean.

```bash
git add web/src/features/proof/ViewShell.tsx web/src/features/proof/DatasetImportPanel.tsx web/src/features/proof/DatasetImportPanel.test.tsx web/src/features/proof/DatasetsView.tsx
git commit -m "feat(cockpit): inline dataset import panel in the Datasets view"
```

---

### Task 6: e2e — import a dataset and see it listed

**Files:**
- Create: `e2e/playwright/dataset-import.spec.ts`

**Interfaces:**
- Consumes: the running embedded app (the Playwright `webServer` boots `orionfold up` on port 8799 with a temp DB). A unique name per run avoids the 409 path on a reused server/DB.

- [ ] **Step 1: Rebuild the embedded cockpit**

The e2e runs against the embedded build, not the dev server. Rebuild so the new panel is embedded:

Run: `bash scripts/build.sh`
Expected: rebuilds `web/dist` and copies it into `src/orionfold/server/static`.

- [ ] **Step 2: Write the e2e spec**

Create `e2e/playwright/dataset-import.spec.ts`:

```typescript
import { expect, test } from "@playwright/test";

// Charter must-have: a user imports their own dataset. Graded in the embedded build —
// open Datasets, paste a 2-line JSONL, preview, name, freeze, and see the card appear.
test("dataset import: paste JSONL → preview → freeze → listed", async ({ page }) => {
  const name = `Import smoke ${Date.now()}`;
  await page.goto("/");

  await page.getByRole("button", { name: "Datasets" }).click();
  await page.getByRole("button", { name: "Import dataset" }).click();

  await page
    .getByLabel(/Paste or upload/i)
    .fill('{"input":"two plus two","expected":"4"}\n{"input":"capital of France","expected":"Paris"}');
  await page.getByRole("button", { name: /^Preview$/ }).click();

  await expect(page.getByText(/2 examples parsed/i)).toBeVisible();

  await page.getByLabel(/Dataset name/i).fill(name);
  await page.getByRole("button", { name: /Freeze dataset/i }).click();

  // The panel closes and the new dataset appears in the list.
  await expect(page.getByRole("heading", { name })).toBeVisible();
  await expect(page.getByText("2 examples")).toBeVisible();
});
```

- [ ] **Step 3: Run the e2e**

Run: `pnpm --dir web e2e`
Expected: both specs pass (the existing proof loop + the new import flow). If `Datasets` rail control is not a `button` role, adjust the selector to match the rail nav (check `web/src/app/App.tsx` rail markup) — but the receipt e2e already uses `getByRole("button", { name: "Receipts" })`, so `"Datasets"` should match the same way.

- [ ] **Step 4: Commit**

```bash
git add e2e/playwright/dataset-import.spec.ts
git commit -m "test(e2e): import a dataset and see it listed"
```

---

## Final verification (after all tasks)

- [ ] `uv run pytest` — full backend suite green (no regressions; new parser + storage + API tests included).
- [ ] `uv run ruff check` and `uv run pyright` — clean.
- [ ] `pnpm --dir web test` — all units green.
- [ ] `pnpm --dir web build` — tsc + vite clean.
- [ ] `bash scripts/build.sh` then `pnpm --dir web e2e` — both Playwright specs green against the embedded build.
- [ ] Manual browser check on a **provably-free** port (assert the listener PID is yours): import a JSONL via paste and via file, a CSV, and a Markdown set; confirm preview, warnings, 409 on a duplicate name, and the new dataset is then selectable in a Proof Run.
- [ ] Append a `docs/worklog/2026-06-20-dataset-import.md` entry (Summary · Verification · Product impact · Risks · Next step) and overwrite `HANDOFF.md`.

## Self-review notes

- **Spec coverage:** all-four formats → Task 1 (JSONL/CSV/Markdown) + paste/file channel → Task 5 textarea+FileReader; preview→confirm→freeze → Tasks 3+5; heading-delimited Markdown → Task 1 `_parse_markdown`; inline panel → Task 5; name-uniqueness 409 → Task 2/3; zero-valid 422 → Tasks 1/3; JSON-only (no multipart) → Task 5 `onFile` reads text client-side; no migration → confirmed (uses existing `datasets` table). ✓
- **Type consistency:** `ImportFormat`/`ParseResult` names match across Python (Task 1) and TS (`importFormatSchema`/`parseResultSchema`, Task 4); `save_dataset(conn, name, description, examples)` signature is identical in Tasks 2 and 3; `DatasetImportPanel({ onClose })` matches in Tasks 5's component and test. ✓
- **Open confirm at execution time:** verify the accent/panel CSS token names against `web/src/index.css` (Task 5 Step 4 note) and the rail nav role for "Datasets" (Task 6 Step 3 note).
