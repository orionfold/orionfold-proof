# Datasets Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Datasets feature with PDF/Word/Excel import (via extract-to-text reuse), free-form auto-colored domain tags, card metadata, and a display-only "check hint" — without touching the scoring engine, `config_hash`, or `RECEIPT_VERSION`.

**Architecture:** Documents are "smart paste" — the server extracts a binary doc into the normalized text of an existing format (xlsx→CSV-text, docx/pdf→Markdown-text) behind one new `/extract` endpoint; the proven preview→freeze pipeline is unchanged. Tags/metadata/check-hint live on the DB row + API `DatasetRow` only (never the domain `Dataset` model), so `config_hash` stays frozen. A new `PATCH` endpoint allows retroactive tagging.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, SQLite, pytest; React 19, TypeScript, Tailwind v4, TanStack Query, Zod, Vitest, Playwright. New backend deps: `openpyxl`, `python-docx`, `pypdf`, `python-multipart`.

## Global Constraints

- Migrations are **append-only**; the next migration index is **5**. Never edit indices 0–4. (`.claude/rules/storage.md`, `src/orionfold/storage/db.py`)
- `config_hash` MUST stay `467ddd96c9a5` and `RECEIPT_VERSION` MUST stay `6` — this cycle touches neither the engine nor the receipt. New fields live on the **DB row + API `DatasetRow` only**, never on the domain `Dataset`/`Example` models.
- Tailwind v4 CSS-var syntax: `bg-(--color-x)`, NOT `bg-[--color-x]`.
- Categorical tags stay **squared** (not pill); cyan `--color-accent` is the ONLY interactive color; the `t1/t2/t3/t5/t7` value hues are categorical and **never interactive**.
- Importers/extractors are **pure and keyless**: no network, no secrets, never log file contents (the store may hold confidential client text).
- No new prod dependency may be added to `pyproject.toml` until the operator explicitly approves (Task 3 is a hard gate).
- Brand copy: no emoji, no hedge/filler words, intentional not templated.
- Run backend tests with `uv run pytest`; frontend with `pnpm --dir web test`; typecheck with `pnpm --dir web exec tsc --noEmit` and `uv run pyright`.

---

### Task 1: Migration 5 + repository metadata read/write

**Files:**
- Modify: `src/orionfold/storage/db.py:16-45` (append migration index 5)
- Modify: `src/orionfold/storage/repository.py` (add `DatasetMeta`, evolve `list_dataset_rows`, add `get_dataset_meta` / `update_dataset_meta`, extend `save_dataset`)
- Test: `tests/unit/test_storage.py`

**Interfaces:**
- Produces:
  - `class DatasetMeta(BaseModel): is_sample: bool; tags: list[str]; created_at: str; source: str; check_hint: str | None`
  - `list_dataset_rows(conn) -> list[tuple[Dataset, DatasetMeta]]`
  - `get_dataset_meta(conn, dataset_id: str) -> DatasetMeta | None`
  - `update_dataset_meta(conn, dataset_id, *, tags: list[str] | None = None, description: str | None = None, check_hint: str | None = None) -> bool` (returns False if id unknown)
  - `save_dataset(conn, name, description, examples, *, tags: list[str] | None = None, source: str = "", check_hint: str | None = None, created_at: str = "") -> Dataset`

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_storage.py`:

```python
from orionfold.storage.repository import (
    DatasetMeta,
    get_dataset_meta,
    list_dataset_rows,
    save_dataset,
    update_dataset_meta,
)


def test_save_dataset_persists_tags_source_created_and_check_hint(conn):
    ds = save_dataset(
        conn, "Tagged set", "", [Example(input_text="a", expected_text="b")],
        tags=["Legal", "Finance"], source="file:cases.xlsx", check_hint="substring",
        created_at="2026-06-22T10:00:00Z",
    )
    rows = {d.id: m for d, m in list_dataset_rows(conn)}
    meta = rows[ds.id]
    assert meta.tags == ["Legal", "Finance"]
    assert meta.source == "file:cases.xlsx"
    assert meta.created_at == "2026-06-22T10:00:00Z"
    assert meta.check_hint == "substring"
    assert meta.is_sample is False


def test_legacy_dataset_reads_empty_meta_defaults(conn):
    # A dataset created without meta gets safe defaults, check_hint normalizes '' -> None.
    ds = save_dataset(conn, "Bare", "", [Example(input_text="a", expected_text="b")])
    meta = get_dataset_meta(conn, ds.id)
    assert meta is not None
    assert meta.tags == []
    assert meta.check_hint is None
    assert meta.source == ""


def test_update_dataset_meta_changes_only_provided_fields(conn):
    ds = save_dataset(conn, "Editable", "old desc", [Example(input_text="a", expected_text="b")])
    assert update_dataset_meta(conn, ds.id, tags=["Support"], check_hint="numeric") is True
    meta = get_dataset_meta(conn, ds.id)
    assert meta.tags == ["Support"]
    assert meta.check_hint == "numeric"
    # description untouched because not provided
    after = {d.id: d for d, _ in list_dataset_rows(conn)}[ds.id]
    assert after.description == "old desc"


def test_update_dataset_meta_unknown_id_returns_false(conn):
    assert update_dataset_meta(conn, "nope", tags=["x"]) is False
```

(If a `conn` fixture is not already present in this file, reuse the existing one used by the other `save_dataset` tests — they already take `conn`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_storage.py -k "meta or check_hint or legacy" -v`
Expected: FAIL with `ImportError`/`AttributeError` (symbols not defined).

- [ ] **Step 3: Append migration index 5**

In `src/orionfold/storage/db.py`, append to the `MIGRATIONS` list (after the `settings` table entry):

```python
    """
    ALTER TABLE datasets ADD COLUMN tags       TEXT NOT NULL DEFAULT '[]';
    ALTER TABLE datasets ADD COLUMN created_at TEXT NOT NULL DEFAULT '';
    ALTER TABLE datasets ADD COLUMN source     TEXT NOT NULL DEFAULT '';
    ALTER TABLE datasets ADD COLUMN check_hint TEXT NOT NULL DEFAULT '';
    """,
```

- [ ] **Step 4: Implement repository changes**

In `src/orionfold/storage/repository.py`, add the `BaseModel` import and the `DatasetMeta` model near the top:

```python
from pydantic import BaseModel
```

```python
class DatasetMeta(BaseModel):
    """Display/management metadata for a dataset — lives on the DB row + API only, never on
    the domain Dataset model, so config_hash stays untouched."""

    is_sample: bool
    tags: list[str]
    created_at: str
    source: str
    check_hint: str | None


def _load_meta(r: sqlite3.Row) -> DatasetMeta:
    import json

    raw_tags = r["tags"] if "tags" in r.keys() else "[]"
    tags = json.loads(raw_tags) if raw_tags else []
    if not isinstance(tags, list):
        tags = []
    hint = (r["check_hint"] or "") if "check_hint" in r.keys() else ""
    return DatasetMeta(
        is_sample=bool(r["is_sample"]),
        tags=[str(t) for t in tags],
        created_at=r["created_at"] if "created_at" in r.keys() else "",
        source=r["source"] if "source" in r.keys() else "",
        check_hint=hint or None,
    )
```

Replace `list_dataset_rows` with:

```python
def list_dataset_rows(conn: sqlite3.Connection) -> list[tuple[Dataset, DatasetMeta]]:
    """Datasets plus display metadata — for the API; the domain model stays flag-free."""
    rows = conn.execute(
        "SELECT id, name, description, examples, is_sample, tags, created_at, source, check_hint "
        "FROM datasets ORDER BY name"
    ).fetchall()
    out: list[tuple[Dataset, DatasetMeta]] = []
    for r in rows:
        dataset = Dataset.model_validate(
            {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "examples": _load_examples(r["examples"]),
            }
        )
        out.append((dataset, _load_meta(r)))
    return out


def get_dataset_meta(conn: sqlite3.Connection, dataset_id: str) -> DatasetMeta | None:
    r = conn.execute(
        "SELECT is_sample, tags, created_at, source, check_hint FROM datasets WHERE id = ?",
        (dataset_id,),
    ).fetchone()
    return None if r is None else _load_meta(r)


def update_dataset_meta(
    conn: sqlite3.Connection,
    dataset_id: str,
    *,
    tags: list[str] | None = None,
    description: str | None = None,
    check_hint: str | None = None,
) -> bool:
    """Update only the provided metadata fields. Never touches examples. False if id unknown."""
    import json

    if conn.execute("SELECT 1 FROM datasets WHERE id = ?", (dataset_id,)).fetchone() is None:
        return False
    sets: list[str] = []
    params: list[object] = []
    if tags is not None:
        sets.append("tags = ?")
        params.append(json.dumps([str(t).strip() for t in tags if str(t).strip()]))
    if description is not None:
        sets.append("description = ?")
        params.append(description.strip())
    if check_hint is not None:
        sets.append("check_hint = ?")
        params.append(check_hint.strip())
    if sets:
        params.append(dataset_id)
        conn.execute(f"UPDATE datasets SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()
    return True
```

Replace the `save_dataset` signature + INSERT to carry the new columns:

```python
def save_dataset(
    conn: sqlite3.Connection,
    name: str,
    description: str,
    examples: list[Example],
    *,
    tags: list[str] | None = None,
    source: str = "",
    check_hint: str | None = None,
    created_at: str = "",
) -> Dataset:
    """Create a new dataset. Name must be unique (case-insensitive); id is a unique slug."""
    import json

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
    clean_tags = [str(t).strip() for t in (tags or []) if str(t).strip()]
    conn.execute(
        "INSERT INTO datasets (id, name, description, examples, tags, created_at, source, check_hint) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            dataset.id,
            dataset.name,
            dataset.description,
            _examples_json(dataset),
            json.dumps(clean_tags),
            created_at,
            source,
            (check_hint or "").strip(),
        ),
    )
    conn.commit()
    return dataset
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_storage.py -v`
Expected: PASS (including the pre-existing `save_dataset` tests — the INSERT change is backward-compatible).

- [ ] **Step 6: Commit**

```bash
git add src/orionfold/storage/db.py src/orionfold/storage/repository.py tests/unit/test_storage.py
git commit -m "feat(datasets): migration 5 + dataset metadata (tags/created_at/source/check_hint)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: API — DatasetRow fields, GET wiring, PATCH endpoint

**Files:**
- Modify: `src/orionfold/server/routes.py` (`DatasetRow` model, `get_datasets`, new `DatasetPatchRequest` + `patch_dataset`, import + `created_at` stamp in `create_dataset`)
- Test: `tests/integration/test_proof_api.py`

**Interfaces:**
- Consumes: `DatasetMeta`, `list_dataset_rows`, `get_dataset`, `get_dataset_meta`, `update_dataset_meta`, `save_dataset` (Task 1).
- Produces: `DatasetRow` with `tags`, `created_at`, `source`, `check_hint`; `PATCH /api/datasets/{id}`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/integration/test_proof_api.py` (reuse the existing `client` fixture pattern in that file):

```python
def test_create_with_tags_and_check_hint_round_trips(client):
    body = {
        "name": "Tagged via API",
        "format": "jsonl",
        "text": '{"input": "x", "expected": "y"}',
        "tags": ["Legal", "Finance"],
        "check_hint": "substring",
    }
    assert client.post("/api/datasets", json=body).status_code == 201
    rows = {d["name"]: d for d in client.get("/api/datasets").json()}
    row = rows["Tagged via API"]
    assert row["tags"] == ["Legal", "Finance"]
    assert row["check_hint"] == "substring"
    assert row["created_at"]  # stamped, non-empty
    assert row["source"] == "pasted"


def test_patch_dataset_updates_tags_and_404s_for_unknown(client):
    client.post("/api/datasets", json={"name": "Patchable", "format": "jsonl",
                                       "text": '{"input": "a", "expected": "b"}'})
    ds_id = {d["name"]: d for d in client.get("/api/datasets").json()}["Patchable"]["id"]
    res = client.patch(f"/api/datasets/{ds_id}", json={"tags": ["Support"], "check_hint": "exact"})
    assert res.status_code == 200
    assert res.json()["tags"] == ["Support"]
    assert res.json()["check_hint"] == "exact"
    assert client.patch("/api/datasets/does-not-exist", json={"tags": ["x"]}).status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_proof_api.py -k "tags or patch" -v`
Expected: FAIL (DatasetRow has no `tags`; no PATCH route → 405/404 shape mismatch).

- [ ] **Step 3: Update DatasetRow and create_dataset**

In `src/orionfold/server/routes.py`, replace the `DatasetRow` model:

```python
class DatasetRow(BaseModel):
    id: str
    name: str
    description: str
    examples: list[Example]
    is_sample: bool
    tags: list[str] = []
    created_at: str = ""
    source: str = ""
    check_hint: str | None = None
```

Extend `DatasetCreateRequest`:

```python
class DatasetCreateRequest(BaseModel):
    name: str
    description: str = ""
    format: ImportFormat
    text: str
    tags: list[str] = []
    source: str = ""
    check_hint: str | None = None
```

Add the patch request model near the other request models:

```python
class DatasetPatchRequest(BaseModel):
    tags: list[str] | None = None
    description: str | None = None
    check_hint: str | None = None
```

Update the repository import block to add the new symbols:

```python
from orionfold.storage.repository import (
    DatasetMeta,
    DuplicateDatasetError,
    clear_all_data,
    get_dataset,
    get_dataset_meta,
    get_report,
    list_dataset_rows,
    list_runs,
    remove_sample_data,
    save_dataset,
    save_report,
    seed_datasets,
    update_dataset_meta,
)
```

Replace `get_datasets` to project the metadata:

```python
@router.get("/datasets")
def get_datasets(request: Request) -> list[DatasetRow]:
    conn = _conn(request)
    try:
        return [
            DatasetRow(
                id=d.id,
                name=d.name,
                description=d.description,
                examples=d.examples,
                is_sample=m.is_sample,
                tags=m.tags,
                created_at=m.created_at,
                source=m.source,
                check_hint=m.check_hint,
            )
            for d, m in list_dataset_rows(conn)
        ]
    finally:
        conn.close()
```

Replace `create_dataset` to stamp `created_at`, default the source, and pass meta through:

```python
@router.post("/datasets", status_code=201)
def create_dataset(request: Request, body: DatasetCreateRequest) -> DatasetRow:
    """Re-parse server-side (source of truth), then freeze into a new dataset."""
    try:
        result = parse_dataset(body.text, body.format)
    except DatasetParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    conn = _conn(request)
    try:
        created = save_dataset(
            conn,
            body.name,
            body.description,
            result.examples,
            tags=body.tags,
            source=body.source or "pasted",
            check_hint=body.check_hint,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        meta = get_dataset_meta(conn, created.id)
        assert meta is not None
        return DatasetRow(
            id=created.id, name=created.name, description=created.description,
            examples=created.examples, is_sample=meta.is_sample, tags=meta.tags,
            created_at=meta.created_at, source=meta.source, check_hint=meta.check_hint,
        )
    except DuplicateDatasetError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    finally:
        conn.close()
```

Add the PATCH route directly after `create_dataset`:

```python
@router.patch("/datasets/{dataset_id}")
def patch_dataset(request: Request, dataset_id: str, body: DatasetPatchRequest) -> DatasetRow:
    """Edit display metadata (tags/description/check_hint) only — never the frozen examples."""
    provided = body.model_dump(exclude_unset=True)
    conn = _conn(request)
    try:
        ok = update_dataset_meta(
            conn,
            dataset_id,
            tags=provided.get("tags"),
            description=provided.get("description"),
            check_hint=provided.get("check_hint"),
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Dataset not found.")
        ds = get_dataset(conn, dataset_id)
        meta = get_dataset_meta(conn, dataset_id)
        assert ds is not None and meta is not None
        return DatasetRow(
            id=ds.id, name=ds.name, description=ds.description, examples=ds.examples,
            is_sample=meta.is_sample, tags=meta.tags, created_at=meta.created_at,
            source=meta.source, check_hint=meta.check_hint,
        )
    finally:
        conn.close()
```

Note: `create_dataset` now returns `DatasetRow` instead of `Dataset`. The frontend reads it back through the loose Zod schema (Task 6), so this is compatible.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_proof_api.py -v`
Expected: PASS (existing dataset API tests still green; new tags/patch tests pass).

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/server/routes.py tests/integration/test_proof_api.py
git commit -m "feat(datasets): expose tags/metadata on DatasetRow + PATCH endpoint

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Dependency approval gate + install

**Files:**
- Modify: `pyproject.toml` (dependencies)

**This is a HARD GATE.** Do not proceed until the operator has explicitly approved adding the four packages. The implementer (or driving agent) must surface this and wait.

- [ ] **Step 1: Confirm operator approval**

Ask the operator to approve adding, to `[project.dependencies]`:
- `openpyxl>=3.1` (MIT) — read `.xlsx`
- `python-docx>=1.1` (MIT) — read `.docx` paragraphs + tables
- `pypdf>=4.0` (BSD) — extract `.pdf` text
- `python-multipart>=0.0.9` (Apache-2.0) — required by FastAPI for `UploadFile`

All are pure-Python, permissively licensed, single-purpose, backend-only (not in the browser bundle), no network.

- [ ] **Step 2: Add dependencies**

Add the four entries to the `dependencies` array in `pyproject.toml` (alongside `fastapi`, `httpx`, etc.), keeping the array alphabetized if it already is.

- [ ] **Step 3: Sync the environment**

Run: `uv sync`
Expected: resolves and installs the four packages with no conflicts.

- [ ] **Step 4: Verify importability**

Run: `uv run python -c "import openpyxl, docx, pypdf, multipart; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build(datasets): add openpyxl, python-docx, pypdf, python-multipart (approved)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Document extractors

**Files:**
- Create: `src/orionfold/data/extractors.py`
- Test: `tests/unit/test_extractors.py`

**Interfaces:**
- Consumes: `ImportFormat` from `orionfold.data.importers`.
- Produces:
  - `DocFormat = Literal["xlsx", "docx", "pdf"]`
  - `class ExtractResult(BaseModel): format: ImportFormat; text: str; warnings: list[str]`
  - `class DocExtractError(ValueError)`
  - `extract_document(data: bytes, doc_format: DocFormat) -> ExtractResult`
  - `doc_format_for(filename: str) -> DocFormat | None`
  - internal pure helper `normalize_pairs_to_markdown(text: str) -> tuple[str, list[str]]` and `_pdf_text(data: bytes) -> str` (monkeypatch seam for tests)

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_extractors.py`:

```python
import io

import pytest
from openpyxl import Workbook

from orionfold.data.extractors import (
    DocExtractError,
    doc_format_for,
    extract_document,
    normalize_pairs_to_markdown,
)
from orionfold.data.importers import parse_dataset


def _xlsx_bytes(rows: list[tuple[str, str]], header=("input", "expected")) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(list(header))
    for a, b in rows:
        ws.append([a, b])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_doc_format_for_maps_extensions():
    assert doc_format_for("cases.xlsx") == "xlsx"
    assert doc_format_for("memo.DOCX") == "docx"
    assert doc_format_for("report.pdf") == "pdf"
    assert doc_format_for("notes.txt") is None


def test_extract_xlsx_yields_csv_text_that_parses():
    data = _xlsx_bytes([("What is 2+2?", "4"), ("Capital of France?", "Paris")])
    result = extract_document(data, "xlsx")
    assert result.format == "csv"
    parsed = parse_dataset(result.text, result.format)
    assert parsed.count == 2
    assert parsed.examples[0].input_text == "What is 2+2?"
    assert parsed.examples[1].expected_text == "Paris"


def test_extract_xlsx_missing_columns_warns():
    data = _xlsx_bytes([("a", "b")], header=("question", "answer"))
    result = extract_document(data, "xlsx")
    assert result.warnings  # surfaced, not raised
    assert "input" in result.warnings[0].lower() or "expected" in result.warnings[0].lower()


def test_extract_docx_table_yields_markdown_pairs():
    import docx

    doc = docx.Document()
    table = doc.add_table(rows=0, cols=2)
    table.add_row().cells  # header
    table.rows[0].cells[0].text = "input"
    table.rows[0].cells[1].text = "expected"
    r = table.add_row().cells
    r[0].text = "Define proof."
    r[1].text = "Evidence you can rerun."
    buf = io.BytesIO()
    doc.save(buf)
    result = extract_document(buf.getvalue(), "docx")
    assert result.format == "markdown"
    parsed = parse_dataset(result.text, result.format)
    assert parsed.count == 1
    assert parsed.examples[0].input_text == "Define proof."


def test_extract_pdf_uses_text_seam_and_warns_lossy(monkeypatch):
    monkeypatch.setattr(
        "orionfold.data.extractors._pdf_text",
        lambda data: "Input\nWhat is proof?\nExpected\nA repeatable receipt.\n",
    )
    result = extract_document(b"%PDF-fake", "pdf")
    assert result.format == "markdown"
    assert any("lossy" in w.lower() or "review" in w.lower() for w in result.warnings)
    parsed = parse_dataset(result.text, result.format)
    assert parsed.count == 1


def test_normalize_pairs_to_markdown_promotes_bare_labels():
    text, warnings = normalize_pairs_to_markdown("Input\nQ1\nExpected\nA1\n")
    assert "## Input" in text and "## Expected" in text


def test_extract_unknown_format_raises():
    with pytest.raises(DocExtractError):
        extract_document(b"not a workbook", "xlsx")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_extractors.py -v`
Expected: FAIL with `ModuleNotFoundError: orionfold.data.extractors`.

- [ ] **Step 3: Implement the extractors**

Create `src/orionfold/data/extractors.py`:

```python
"""Document extractors — turn binary .xlsx/.docx/.pdf uploads into the *normalized text* of an
existing import format (CSV-text or Markdown-text), so the proven importers stay the single
source of truth. Pure and keyless: no network, no secrets, never log file contents. Extraction
is intentionally fixable — the caller shows the returned text for review before freezing.
"""

from __future__ import annotations

import csv
import io
import re
from typing import Literal

from pydantic import BaseModel

from orionfold.data.importers import ImportFormat

DocFormat = Literal["xlsx", "docx", "pdf"]

_EXT_TO_FORMAT: dict[str, DocFormat] = {".xlsx": "xlsx", ".docx": "docx", ".pdf": "pdf"}


class ExtractResult(BaseModel):
    """Normalized text in an existing import format, plus extraction-level warnings."""

    format: ImportFormat
    text: str
    warnings: list[str]


class DocExtractError(ValueError):
    """A document could not be opened or read — surfaced to the API as HTTP 422."""


def doc_format_for(filename: str) -> DocFormat | None:
    for ext, fmt in _EXT_TO_FORMAT.items():
        if filename.lower().endswith(ext):
            return fmt
    return None


def extract_document(data: bytes, doc_format: DocFormat) -> ExtractResult:
    if doc_format == "xlsx":
        return _extract_xlsx(data)
    if doc_format == "docx":
        return _extract_docx(data)
    if doc_format == "pdf":
        return _extract_pdf(data)
    raise DocExtractError(f"Unsupported document format: {doc_format}")


def _extract_xlsx(data: bytes) -> ExtractResult:
    try:
        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:  # openpyxl raises various errors on bad input
        raise DocExtractError(f"Could not read the Excel file: {exc}") from exc
    ws = wb.active
    rows = ws.iter_rows(values_only=True) if ws is not None else iter(())
    header = next(rows, None)
    warnings: list[str] = []
    if not header:
        return ExtractResult(format="csv", text="", warnings=["The spreadsheet was empty."])
    cols = {str(c).strip().lower(): i for i, c in enumerate(header) if c is not None}
    in_i = cols.get("input", cols.get("input_text"))
    out_i = cols.get("expected", cols.get("expected_text"))
    if in_i is None or out_i is None:
        warnings.append(
            "Spreadsheet needs an 'input' and an 'expected' column header. "
            "Rename your columns, or edit the text below into input,expected rows."
        )
        return ExtractResult(format="csv", text="", warnings=warnings)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["input", "expected"])
    for row in rows:
        a = "" if in_i >= len(row) or row[in_i] is None else str(row[in_i]).strip()
        b = "" if out_i >= len(row) or row[out_i] is None else str(row[out_i]).strip()
        if a or b:
            writer.writerow([a, b])
    return ExtractResult(format="csv", text=buf.getvalue(), warnings=warnings)


def _extract_docx(data: bytes) -> ExtractResult:
    try:
        import docx

        doc = docx.Document(io.BytesIO(data))
    except Exception as exc:
        raise DocExtractError(f"Could not read the Word file: {exc}") from exc
    # Prefer two-column tables (input | expected); fall back to paragraph headings.
    blocks: list[str] = []
    for table in doc.tables:
        for ri, row in enumerate(table.rows):
            cells = [c.text.strip() for c in row.cells]
            if len(cells) < 2:
                continue
            if ri == 0 and cells[0].lower() in {"input", "input_text"}:
                continue  # skip header row
            if cells[0] or cells[1]:
                blocks.append(f"## Input\n{cells[0]}\n\n## Expected\n{cells[1]}\n\n---")
    if blocks:
        return ExtractResult(format="markdown", text="\n".join(blocks), warnings=[])
    paras = "\n".join(p.text for p in doc.paragraphs)
    text, warnings = normalize_pairs_to_markdown(paras)
    return ExtractResult(format="markdown", text=text, warnings=warnings)


def _pdf_text(data: bytes) -> str:
    """Isolated so tests can monkeypatch it without a binary fixture."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_pdf(data: bytes) -> ExtractResult:
    try:
        raw = _pdf_text(data)
    except Exception as exc:
        raise DocExtractError(f"Could not read the PDF file: {exc}") from exc
    text, warnings = normalize_pairs_to_markdown(raw)
    warnings.insert(
        0,
        "PDF text extraction is lossy — review the pairs below and fix any split text "
        "before freezing.",
    )
    return ExtractResult(format="markdown", text=text, warnings=warnings)


_BARE_LABEL = re.compile(r"^(input|expected)\s*:?\s*$", re.IGNORECASE)


def normalize_pairs_to_markdown(text: str) -> tuple[str, list[str]]:
    """Promote bare 'Input'/'Expected' lines to Markdown headings the importer understands.
    Lines already starting with '#' are left as-is. Returns (markdown_text, warnings)."""
    out: list[str] = []
    saw_label = False
    for raw in text.splitlines():
        line = raw.rstrip()
        m = _BARE_LABEL.match(line.strip())
        if m:
            saw_label = True
            out.append(f"## {m.group(1).capitalize()}")
        else:
            out.append(line)
    warnings: list[str] = []
    if not saw_label and "#" not in text:
        warnings.append(
            "No 'Input'/'Expected' structure found. Add '## Input' / '## Expected' headings "
            "(separated by '---') so the pairs can be parsed."
        )
    return "\n".join(out), warnings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_extractors.py -v`
Expected: PASS (all 7 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/data/extractors.py tests/unit/test_extractors.py
git commit -m "feat(datasets): xlsx/docx/pdf extractors -> normalized import text

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: `/extract` endpoint

**Files:**
- Modify: `src/orionfold/server/routes.py` (import extractors, `MAX_UPLOAD_BYTES`, `extract_dataset` route)
- Test: `tests/integration/test_proof_api.py`

**Interfaces:**
- Consumes: `extract_document`, `doc_format_for`, `DocExtractError`, `ExtractResult` (Task 4).
- Produces: `POST /api/datasets/extract` (multipart `file`) → `ExtractResult`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/integration/test_proof_api.py`:

```python
import io

from openpyxl import Workbook


def _xlsx_upload_bytes() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["input", "expected"])
    ws.append(["Ping?", "Pong."])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_extract_xlsx_returns_csv_text_without_writing(client):
    before = len(client.get("/api/datasets").json())
    files = {"file": ("cases.xlsx", _xlsx_upload_bytes(),
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    res = client.post("/api/datasets/extract", files=files)
    assert res.status_code == 200
    body = res.json()
    assert body["format"] == "csv"
    assert "Ping?" in body["text"]
    assert len(client.get("/api/datasets").json()) == before  # no write


def test_extract_rejects_unknown_extension(client):
    files = {"file": ("notes.txt", b"hello", "text/plain")}
    assert client.post("/api/datasets/extract", files=files).status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_proof_api.py -k extract -v`
Expected: FAIL (route not found / 404).

- [ ] **Step 3: Implement the endpoint**

In `src/orionfold/server/routes.py`, add to the imports:

```python
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from orionfold.data.extractors import DocExtractError, ExtractResult, doc_format_for, extract_document
```

(Adjust the existing `from fastapi import ...` line to include `File` and `UploadFile`.)

Add a constant near the top of the module (after `router = APIRouter(...)`):

```python
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB — datasets are small; this guards memory + abuse.
```

Add the route after `patch_dataset`:

```python
@router.post("/datasets/extract")
async def extract_dataset(file: UploadFile = File(...)) -> ExtractResult:
    """Extract an uploaded .xlsx/.docx/.pdf into normalized import text. Never writes."""
    doc_format = doc_format_for(file.filename or "")
    if doc_format is None:
        raise HTTPException(
            status_code=422,
            detail="Unsupported file type. Upload .xlsx, .docx, or .pdf (or paste text directly).",
        )
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (5 MB max).")
    try:
        return extract_document(data, doc_format)
    except DocExtractError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_proof_api.py -k extract -v`
Expected: PASS.

- [ ] **Step 5: Run the full backend suite + typecheck**

Run: `uv run pytest && uv run pyright src/orionfold`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add src/orionfold/server/routes.py tests/integration/test_proof_api.py
git commit -m "feat(datasets): POST /api/datasets/extract for doc uploads

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Frontend API client — schema, extract, update, create

**Files:**
- Modify: `web/src/lib/api.ts`
- Test: `web/src/lib/api.test.ts` (create if absent) — minimal schema test

**Interfaces:**
- Produces: extended `datasetSchema` (tags/created_at/source/check_hint); `extractResultSchema` + `ExtractResult` type; `extractDataset(file)`, `updateDataset(id, patch)`, extended `createDataset` body.

- [ ] **Step 1: Write the failing test**

Create `web/src/lib/api.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { datasetSchema, extractResultSchema } from "./api";

describe("datasetSchema", () => {
  it("defaults tags to [] and accepts metadata", () => {
    const d = datasetSchema.parse({
      id: "x", name: "n", description: "", examples: [],
      created_at: "2026-06-22T00:00:00Z", source: "pasted", check_hint: "substring",
    });
    expect(d.tags).toEqual([]);
    expect(d.check_hint).toBe("substring");
  });
});

describe("extractResultSchema", () => {
  it("parses an extract response", () => {
    const r = extractResultSchema.parse({ format: "csv", text: "input,expected\na,b", warnings: [] });
    expect(r.format).toBe("csv");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test -- api.test`
Expected: FAIL (`extractResultSchema` not exported; `tags` missing on schema).

- [ ] **Step 3: Implement client changes**

In `web/src/lib/api.ts`, extend `datasetSchema` (add the four fields after `is_sample`):

```ts
export const datasetSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  examples: z.array(exampleSchema),
  is_sample: z.boolean().optional(),
  tags: z.array(z.string()).optional().default([]),
  created_at: z.string().optional().default(""),
  source: z.string().optional().default(""),
  check_hint: z.string().nullable().optional(),
});
```

Add the extract result schema after `parseResultSchema`:

```ts
export const extractResultSchema = z.object({
  format: importFormatSchema,
  text: z.string(),
  warnings: z.array(z.string()),
});
export type ExtractResult = z.infer<typeof extractResultSchema>;
```

Extend `createDataset`'s body type and add the two new functions after `createDataset`:

```ts
export async function createDataset(body: {
  name: string;
  description?: string;
  format: ImportFormat;
  text: string;
  tags?: string[];
  source?: string;
  check_hint?: string | null;
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

export async function extractDataset(file: File): Promise<ExtractResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/datasets/extract", { method: "POST", body: form });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Could not read the file (HTTP ${res.status})`);
  }
  return extractResultSchema.parse(await res.json());
}

export async function updateDataset(
  id: string,
  patch: { tags?: string[]; description?: string; check_hint?: string | null },
): Promise<Dataset> {
  const res = await fetch(`/api/datasets/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Update failed (HTTP ${res.status})`);
  }
  return datasetSchema.parse(await res.json());
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --dir web test -- api.test`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/api.ts web/src/lib/api.test.ts
git commit -m "feat(datasets): api client for extract, update, and dataset metadata

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Tag tokens (CSS) + tag helper + TagChips component

**Files:**
- Modify: `web/src/styles/index.css` (categorical tag tokens + `.of-tag` classes)
- Create: `web/src/features/proof/tags.ts` (`tagToken`, `CHECK_HINTS`)
- Create: `web/src/features/proof/TagChips.tsx`
- Test: `web/src/features/proof/tags.test.ts`

**Interfaces:**
- Produces:
  - `tagToken(label: string): "t1" | "t2" | "t3" | "t5" | "t7"` (stable per label)
  - `CHECK_HINTS: { value: string; label: string }[]`
  - `<TagChips tags={string[]} />`

- [ ] **Step 1: Write the failing test**

Create `web/src/features/proof/tags.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { tagToken } from "./tags";

describe("tagToken", () => {
  it("is stable and case-insensitive for the same label", () => {
    expect(tagToken("Legal")).toBe(tagToken("legal"));
  });
  it("returns a valid categorical token", () => {
    expect(["t1", "t2", "t3", "t5", "t7"]).toContain(tagToken("Finance"));
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test -- tags.test`
Expected: FAIL (`./tags` not found).

- [ ] **Step 3: Add categorical tag tokens to the theme CSS**

In `web/src/styles/index.css`, after the `:root[data-theme="light"]` override block, add a dark-default `:root` block and a light override (values copied verbatim from the brand values sheet). Place this comment + rules:

```css
/* Categorical value-tag tokens (Orionfold brand values sheet) — NEVER interactive; tags stay
   squared. Dark is the default; light overrides. Reused by dataset domain tags (and, later, the
   shared badge/chip kit). */
:root {
  --t1bg: #16345e; --t1fg: #7fb4ff;
  --t2bg: #143a28; --t2fg: #62d98c;
  --t3bg: #4a3410; --t3fg: #f5b14a;
  --t5bg: #2e2256; --t5fg: #b79cff;
  --t7bg: #1e2a5e; --t7fg: #aab6ee;
}
:root[data-theme="light"] {
  --t1bg: #d2e5ff; --t1fg: #1257c4;
  --t2bg: #d3f8e6; --t2fg: #157a3c;
  --t3bg: #ffe8c2; --t3fg: #9a5a00;
  --t5bg: #e6dcff; --t5fg: #6b32d6;
  --t7bg: #dfe2f5; --t7fg: #2c3a78;
}

.of-tag {
  display: inline-flex; align-items: center; gap: 4px;
  font-family: var(--font-mono); font-size: 11px; font-weight: 500; letter-spacing: 0.03em;
  padding: 2px 8px; border-radius: 3px; /* squared, not pill */
  border: 1px solid var(--color-panel-line);
}
.of-tag--t1 { background: var(--t1bg); color: var(--t1fg); }
.of-tag--t2 { background: var(--t2bg); color: var(--t2fg); }
.of-tag--t3 { background: var(--t3bg); color: var(--t3fg); }
.of-tag--t5 { background: var(--t5bg); color: var(--t5fg); }
.of-tag--t7 { background: var(--t7bg); color: var(--t7fg); }
```

- [ ] **Step 4: Implement the tag helper + component**

Create `web/src/features/proof/tags.ts`:

```ts
const TOKENS = ["t1", "t2", "t3", "t5", "t7"] as const;
export type TagToken = (typeof TOKENS)[number];

/** Stable per-label token from the categorical value palette. Presentation only. */
export function tagToken(label: string): TagToken {
  const key = label.trim().toLowerCase();
  let hash = 0;
  for (let i = 0; i < key.length; i++) hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
  return TOKENS[hash % TOKENS.length];
}

/** Display-only check hints — suggest a rubric at run-setup; the engine never reads these. */
export const CHECK_HINTS: { value: string; label: string }[] = [
  { value: "", label: "No hint" },
  { value: "substring", label: "Contains text" },
  { value: "numeric", label: "Numeric match" },
  { value: "exact", label: "Exact match" },
  { value: "eyeball", label: "Eyeball / judgment" },
];

export function checkHintLabel(value: string | null | undefined): string {
  return CHECK_HINTS.find((h) => h.value === (value ?? ""))?.label ?? "";
}
```

Create `web/src/features/proof/TagChips.tsx`:

```tsx
import { tagToken } from "./tags";

export function TagChips({ tags }: { tags: string[] }) {
  if (tags.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {tags.map((t) => (
        <span key={t} className={`of-tag of-tag--${tagToken(t)}`}>
          {t}
        </span>
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pnpm --dir web test -- tags.test`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web/src/styles/index.css web/src/features/proof/tags.ts web/src/features/proof/TagChips.tsx web/src/features/proof/tags.test.ts
git commit -m "feat(datasets): categorical tag tokens + tagToken helper + TagChips

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Import panel — doc upload, tags input, check-hint select

**Files:**
- Modify: `web/src/features/proof/DatasetImportPanel.tsx`
- Test: `web/src/features/proof/DatasetImportPanel.test.tsx`

**Interfaces:**
- Consumes: `extractDataset`, `createDataset` (Task 6), `CHECK_HINTS`, `TagChips` (Task 7), `doc_format_for` logic via filename extension on the client.

- [ ] **Step 1: Write the failing test**

Add to `web/src/features/proof/DatasetImportPanel.test.tsx` (keep existing tests; mock the new client fn):

```tsx
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DatasetImportPanel } from "./DatasetImportPanel";
import * as api from "../../lib/api";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient();
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("DatasetImportPanel doc upload", () => {
  it("extracts an uploaded .xlsx into the textarea + format", async () => {
    vi.spyOn(api, "extractDataset").mockResolvedValue({
      format: "csv", text: "input,expected\nPing?,Pong.", warnings: ["heads up"],
    });
    wrap(<DatasetImportPanel onClose={() => {}} />);
    const file = new File([new Uint8Array([1, 2, 3])], "cases.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    const input = screen.getByLabelText(/upload dataset file/i) as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() =>
      expect((screen.getByPlaceholderText(/input,expected|per line|## Input/i) as HTMLTextAreaElement).value)
        .toContain("Ping?"),
    );
    expect(api.extractDataset).toHaveBeenCalled();
    expect(screen.getByText(/heads up/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test -- DatasetImportPanel`
Expected: FAIL (no extract behavior; doc files not handled).

- [ ] **Step 3: Implement the panel changes**

Edit `web/src/features/proof/DatasetImportPanel.tsx`. Update imports:

```tsx
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  createDataset,
  extractDataset,
  previewDataset,
  type ImportFormat,
  type ParseResult,
} from "../../lib/api";
import { CHECK_HINTS } from "./tags";

const DOC_EXTENSIONS = [".xlsx", ".docx", ".pdf"];
```

Add state for tags, check hint, extraction warnings, and source (after the existing `preview` state):

```tsx
  const [tags, setTags] = useState<string[]>([]);
  const [tagDraft, setTagDraft] = useState("");
  const [checkHint, setCheckHint] = useState("");
  const [source, setSource] = useState("pasted");
  const [extractWarnings, setExtractWarnings] = useState<string[]>([]);
```

Add an extract mutation and update `createMutation` to send the metadata:

```tsx
  const extractMutation = useMutation({
    mutationFn: (file: File) => extractDataset(file),
  });
  const createMutation = useMutation({
    mutationFn: () =>
      createDataset({
        name,
        format,
        text,
        tags,
        source,
        check_hint: checkHint || null,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["datasets"] });
      onClose();
    },
  });
```

Replace `onFile` so binary docs route through `/extract` and text files keep the FileReader path:

```tsx
  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setPreview(null);
    previewMutation.reset();
    setExtractWarnings([]);
    setSource(`file:${file.name}`);
    const isDoc = DOC_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext));
    if (isDoc) {
      const result = await extractMutation.mutateAsync(file);
      setText(result.text);
      setFormat(result.format);
      setExtractWarnings(result.warnings);
    } else {
      setText(await file.text());
    }
  }

  function addTag() {
    const t = tagDraft.trim();
    if (t && !tags.includes(t)) setTags([...tags, t]);
    setTagDraft("");
  }
```

Widen the file `accept` attribute:

```tsx
          accept=".jsonl,.json,.csv,.md,.markdown,.txt,.xlsx,.docx,.pdf"
```

Surface extraction state — add right after the `<input type="file" .../>` block's containing `<div>` (before the Preview button's sibling content), render extraction warnings and a pending hint:

```tsx
      {extractMutation.isPending && (
        <p className="text-xs text-(--color-ink-faint)">Reading document…</p>
      )}
      {extractMutation.isError && (
        <p className="text-sm text-(--color-danger)">{(extractMutation.error as Error).message}</p>
      )}
      {extractWarnings.length > 0 && (
        <ul className="grid gap-1 rounded-lg border border-dashed border-(--color-panel-line) p-3 text-xs text-(--color-ink-faint)">
          {extractWarnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}
```

In the `{preview && (...)}` block, add a tags editor + check-hint select between the name `<label>` and the Freeze button row:

```tsx
          <label className="grid gap-1 text-sm">
            <span className="text-(--color-ink-muted)">Tags (optional)</span>
            <div className="flex flex-wrap items-center gap-1.5">
              {tags.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTags(tags.filter((x) => x !== t))}
                  className="rounded border border-(--color-panel-line) px-2 py-0.5 text-xs text-(--color-ink-muted) hover:text-(--color-ink)"
                  aria-label={`Remove tag ${t}`}
                >
                  {t} ×
                </button>
              ))}
              <input
                value={tagDraft}
                onChange={(e) => setTagDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addTag();
                  }
                }}
                onBlur={addTag}
                placeholder="e.g. Legal"
                className="rounded-lg border border-(--color-panel-line) bg-(--color-panel-card) p-1.5 text-xs text-(--color-ink)"
              />
            </div>
          </label>

          <label className="grid gap-1 text-sm">
            <span className="text-(--color-ink-muted)">Check hint (suggests a rubric)</span>
            <select
              value={checkHint}
              onChange={(e) => setCheckHint(e.target.value)}
              className="w-full rounded-lg border border-(--color-panel-line) bg-(--color-panel-card) p-2 text-sm text-(--color-ink)"
            >
              {CHECK_HINTS.map((h) => (
                <option key={h.value} value={h.value}>
                  {h.label}
                </option>
              ))}
            </select>
          </label>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --dir web test -- DatasetImportPanel`
Expected: PASS (existing paste→preview→freeze test still green; new upload test passes).

- [ ] **Step 5: Commit**

```bash
git add web/src/features/proof/DatasetImportPanel.tsx web/src/features/proof/DatasetImportPanel.test.tsx
git commit -m "feat(datasets): import panel doc upload + tags + check hint

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Dataset cards — tags, metadata, check hint, inline edit

**Files:**
- Modify: `web/src/features/proof/DatasetsView.tsx`
- Test: `web/src/features/proof/DatasetsView.test.tsx` (create)

**Interfaces:**
- Consumes: `updateDataset` (Task 6), `TagChips`, `checkHintLabel`, `tagToken` (Task 7).

- [ ] **Step 1: Write the failing test**

Create `web/src/features/proof/DatasetsView.test.tsx`:

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DatasetsView } from "./DatasetsView";
import * as api from "../../lib/api";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient();
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("DatasetsView", () => {
  it("renders tags, metadata, and the check hint on a card", async () => {
    vi.spyOn(api, "getDatasets").mockResolvedValue([
      {
        id: "d1", name: "Client memos", description: "", examples: [],
        tags: ["Legal", "Finance"], created_at: "2026-06-22T10:00:00Z",
        source: "file:cases.xlsx", check_hint: "substring",
      } as never,
    ]);
    wrap(<DatasetsView />);
    expect(await screen.findByText("Client memos")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Legal")).toBeInTheDocument());
    expect(screen.getByText("Finance")).toBeInTheDocument();
    expect(screen.getByText(/Contains text/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test -- DatasetsView`
Expected: FAIL (no tags/metadata/check-hint rendered).

- [ ] **Step 3: Implement the card changes**

Edit `web/src/features/proof/DatasetsView.tsx`. Update imports:

```tsx
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getDatasets, updateDataset, type Dataset } from "../../lib/api";
import { ViewNotice, ViewShell } from "./ViewShell";
import { DatasetImportPanel } from "./DatasetImportPanel";
import { TagChips } from "./TagChips";
import { checkHintLabel } from "./tags";
```

Replace the card `<section>` body (the block rendering name, example count, description, details) so it also renders tags, a metadata line, a check-hint chip, and an inline tag editor. Replace the inner content of `datasets.data.map((d) => ( ... ))` with a dedicated `DatasetCard` component reference:

```tsx
          {datasets.data.map((d) => (
            <DatasetCard key={d.id} d={d} />
          ))}
```

Then add these components at the bottom of the file (keep the existing `ExampleField`):

```tsx
function formatDate(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString();
}

function sourceLabel(source: string): string {
  if (!source || source === "pasted") return "pasted";
  return source.startsWith("file:") ? source.slice(5) : source;
}

function DatasetCard({ d }: { d: Dataset }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState((d.tags ?? []).join(", "));
  const save = useMutation({
    mutationFn: () =>
      updateDataset(d.id, {
        tags: draft.split(",").map((t) => t.trim()).filter(Boolean),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["datasets"] });
      setEditing(false);
    },
  });

  const created = formatDate(d.created_at ?? "");
  const metaBits = [
    `${d.examples.length} example${d.examples.length === 1 ? "" : "s"}`,
    created && `created ${created}`,
    sourceLabel(d.source ?? ""),
  ].filter(Boolean);

  return (
    <section className="rounded-xl border border-(--color-panel-line) bg-(--color-panel-card) p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="flex items-center gap-2 text-base font-medium text-(--color-ink)">
          {d.name}
          {d.is_sample ? (
            <span className="rounded border border-(--color-panel-line) bg-(--color-panel-card) px-2 py-0.5 text-[11px] font-medium text-(--color-ink-muted)">
              Sample
            </span>
          ) : null}
        </h3>
        <span className="text-xs text-(--color-ink-faint)">{metaBits.join(" · ")}</span>
      </div>

      {d.description && <p className="mt-1 text-sm text-(--color-ink-muted)">{d.description}</p>}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <TagChips tags={d.tags ?? []} />
        {d.check_hint ? (
          <span className="of-tag of-tag--t5">{checkHintLabel(d.check_hint)}</span>
        ) : null}
        <button
          type="button"
          onClick={() => setEditing((v) => !v)}
          className="text-xs text-(--color-ink-faint) hover:text-(--color-accent)"
        >
          {editing ? "Cancel" : "Edit tags"}
        </button>
      </div>

      {editing && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="comma-separated, e.g. Legal, Finance"
            className="grow rounded-lg border border-(--color-panel-line) bg-(--color-panel-card) p-1.5 text-xs text-(--color-ink)"
          />
          <button
            type="button"
            onClick={() => save.mutate()}
            disabled={save.isPending}
            className="rounded-lg bg-(--color-accent-strong) px-3 py-1.5 text-xs font-medium text-(--color-accent-ink) disabled:opacity-50"
          >
            {save.isPending ? "Saving…" : "Save tags"}
          </button>
        </div>
      )}

      <details className="mt-3">
        <summary className="cursor-pointer text-sm text-(--color-ink-muted) hover:text-(--color-ink)">
          Examples
        </summary>
        <ol className="mt-3 grid gap-3">
          {d.examples.map((ex, i) => (
            <li key={i} className="grid gap-1 border-t border-(--color-panel-line) pt-3 text-sm">
              <ExampleField label="Input" value={ex.input_text} />
              <ExampleField label="Expected" value={ex.expected_text} />
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}
```

Note: the check-hint chip reuses `of-tag--t5` (Quality violet) deliberately — a single fixed categorical hue for the hint, distinct from the hashed domain-tag colors.

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --dir web test -- DatasetsView`
Expected: PASS.

- [ ] **Step 5: Run full frontend suite + typecheck**

Run: `pnpm --dir web test && pnpm --dir web exec tsc --noEmit`
Expected: all green (the prior 90 tests + the new ones).

- [ ] **Step 6: Commit**

```bash
git add web/src/features/proof/DatasetsView.tsx web/src/features/proof/DatasetsView.test.tsx
git commit -m "feat(datasets): cards show tags/metadata/check-hint + inline tag edit

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: E2E, invariants, build, and handoff

**Files:**
- Create: `e2e/playwright/dataset-doc-import.spec.ts`
- Create: `docs/worklog/2026-06-22-datasets-completion.md`
- Modify: `HANDOFF.md`

**Interfaces:** none (integration + verification task).

- [ ] **Step 1: Write the E2E spec**

Create `e2e/playwright/dataset-doc-import.spec.ts` (model it on the existing `dataset-import.spec.ts`; it runs against the embedded build, so a rebuild is required first — Step 3):

```ts
import { test, expect } from "@playwright/test";
import { Workbook } from "exceljs"; // if exceljs is unavailable, generate the .xlsx in a fixtures/ file instead

// NOTE: if the repo has no xlsx writer in node deps, commit a small fixture at
// e2e/playwright/fixtures/cases.xlsx (input/expected header + 2 rows) and use setInputFiles(path).
test("dataset doc import: upload .xlsx → extract → preview → freeze → tagged", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /datasets/i }).click();
  await page.getByRole("button", { name: /import dataset/i }).click();
  await page.getByLabel(/upload dataset file/i).setInputFiles("e2e/playwright/fixtures/cases.xlsx");
  await page.getByRole("button", { name: /preview/i }).click();
  await expect(page.getByText(/example/i)).toBeVisible();
  await page.getByPlaceholder(/Client summaries/i).fill("E2E doc set");
  await page.getByPlaceholder(/e\.g\. Legal/i).fill("Legal");
  await page.getByRole("button", { name: /freeze dataset/i }).click();
  await expect(page.getByText("E2E doc set")).toBeVisible();
  await expect(page.getByText("Legal")).toBeVisible();
});
```

If no node xlsx writer is available, create `e2e/playwright/fixtures/cases.xlsx` by running once:
`uv run python -c "from openpyxl import Workbook; wb=Workbook(); ws=wb.active; ws.append(['input','expected']); ws.append(['Ping?','Pong.']); ws.append(['Sky?','Blue.']); wb.save('e2e/playwright/fixtures/cases.xlsx')"`
and commit the fixture.

- [ ] **Step 2: Verify invariants are untouched**

Run: `uv run pytest -k "config_hash or receipt or hash" -v`
Expected: PASS — the existing tests assert `config_hash` is still `467ddd96c9a5` and `RECEIPT_VERSION` is still `6`. Also confirm the domain model is unchanged:
Run: `uv run python -c "from orionfold.domain.models import Dataset, Example; print(sorted(Dataset.model_fields)); print(sorted(Example.model_fields))"`
Expected: `['description', 'examples', 'id', 'name']` and `['expected_text', 'input_text', 'keypoints']` (no new fields).

- [ ] **Step 3: Rebuild the embedded bundle and run E2E**

Run: `bash scripts/build.sh`
Then: `pnpm --dir web exec playwright test dataset-doc-import`
Expected: PASS. (If `:8787` is occupied, follow the HANDOFF note to use a free port.)

- [ ] **Step 4: Full verification sweep**

Run: `uv run pytest && uv run pyright src/orionfold && pnpm --dir web test && pnpm --dir web exec tsc --noEmit`
Expected: all green.

- [ ] **Step 5: Write the worklog**

Create `docs/worklog/2026-06-22-datasets-completion.md` with: Summary (what shipped), Verification (exact commands + counts + that `config_hash`/`RECEIPT_VERSION` are unchanged), Product impact (broad-ICP doc import + trustworthy tagging), Risks (PDF extraction lossiness; tag-color is hash-based not chosen), Next recommended step (sub-project 2: Leaderboard presentation).

- [ ] **Step 6: Update HANDOFF.md**

Update `HANDOFF.md`: mark Datasets completion shipped (commits, evidence path), record new invariants (migration index 5; `DatasetMeta` lives on DB+API only; `/extract` + `PATCH` endpoints; `.of-tag` categorical tokens; 4 new backend deps), and set the next action to **sub-project 2: Leaderboard presentation** (the next sequenced spec). Keep the "git remote + push queued LAST until packaging" directive intact.

- [ ] **Step 7: Commit**

```bash
git add e2e/playwright/dataset-doc-import.spec.ts e2e/playwright/fixtures/cases.xlsx docs/worklog/2026-06-22-datasets-completion.md HANDOFF.md
git commit -m "test(datasets): e2e doc import + worklog + handoff

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- §3.1 extract-to-text reuse → Tasks 4, 5, 8. ✓
- §3.2 `extractors.py` → Task 4. ✓
- §3.3 `/extract` endpoint (size cap, no write) → Task 5. ✓
- §3.4 tags/created_at/source/check_hint columns (migration 5, DB+API only) → Tasks 1, 2. ✓
- §3.5 `PATCH` (meta only, never examples) → Task 2. ✓
- §3.6 tag color from token palette → Task 7. ✓
- §3.7 frontend (api hooks, import panel, cards, inline edit) → Tasks 6, 8, 9. ✓
- §6 testing (extractor unit, extract integration, PATCH round-trip, tag-color stability, panel test, e2e) → Tasks 4–10. ✓
- §7 deps approval gate → Task 3. ✓ (added `python-multipart`, required for uploads, beyond the spec's three — flagged.)
- Invariants (config_hash/RECEIPT_VERSION/domain model/append-only) → Task 10 Step 2. ✓

**Placeholder scan:** No TBD/TODO. The one conditional is the E2E xlsx fixture (node xlsx writer may be absent) — resolved with an explicit `uv run python` fixture-generation command + `setInputFiles(path)`. Acceptable, not a placeholder.

**Type consistency:** `DatasetMeta` fields match between repository (Task 1), routes projection (Task 2), and Zod schema (Task 6). `ExtractResult{format,text,warnings}` identical in Python (Task 4) and Zod (Task 6). `tagToken` return union matches `.of-tag--*` classes (Task 7). `createDataset` body extension (Task 6) matches what the panel sends (Task 8) and what `DatasetCreateRequest` accepts (Task 2). `check_hint` `''`↔`None` normalization handled in `_load_meta` (Task 1) and `null` over the wire (Tasks 2, 6).

**Deviation flagged:** the spec listed three deps; the plan adds a fourth (`python-multipart`) because FastAPI `UploadFile` requires it. This is a necessary, surfaced addition under the same Task 3 approval gate.
