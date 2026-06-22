# Datasets Completion — Design Spec

_Date: 2026-06-22 · Status: approved (design) · Sub-project 1 of 3 (Datasets → Leaderboard → Quick-Compare)_

> First of three sequenced specs. This one completes the **Datasets** feature past its
> v0-charter floor. Leaderboard presentation and Quick-Compare get their own spec → plan →
> build cycles afterward.

## 1 · Goal

Make datasets **easier to create** for a broadened, non-technical ICP (knowledge workers,
consultants, small teams) and **richer / more trustworthy** to manage — without touching the
scoring engine, the `config_hash` surface (`467ddd96c9a5`), or `RECEIPT_VERSION`.

Two thrusts, both operator-approved:

1. **Easier to create** — import PDF / Word / Excel (on top of today's JSONL / CSV / Markdown /
   paste), with format auto-detection and a fixable preview.
2. **Richer & trustworthy** — free-form auto-colored **domain tags**, **card metadata**
   (created date, source/origin), and a dataset-level **check hint** that displays and
   *suggests* a rubric at run-setup (never consumed by the engine).

### Non-goals (explicitly out of scope this cycle)

- Per-row check kinds that change scoring (would touch the engine + `config_hash`; deferred to
  its own ADR/spec if ever pursued).
- A separate dataset detail page / route (`GET /api/datasets/{id}`). Richer data is surfaced on
  the existing cards. Deferred unless datasets-get-large pressure appears.
- Edit/delete of dataset **examples** (only `tags` / `description` / `check_hint` are editable).
- Extract-then-map UI (interactive column/section pickers). The fixable textarea covers messy
  docs adequately for v0.
- Any RAG / corpus-ingestion mental model. A dataset stays `(input_text, expected_text)` pairs.

## 2 · Current state (what we build on)

- Parse entry point: `parse_dataset(text, fmt)` → `ParseResult{examples, warnings, count}` /
  `DatasetParseError` in `src/orionfold/data/importers.py`. `ImportFormat =
  Literal["jsonl","csv","markdown"]`.
- API: `GET /api/datasets` → `list[DatasetRow]`; `POST /api/datasets/preview` (never writes);
  `POST /api/datasets` (re-parses server-side, calls `save_dataset`). `routes.py:120-160`.
- `DatasetRow` (API) carries `is_sample`; the domain `Dataset` model does **not** — this split
  keeps `config_hash` safe. New display fields follow the **same rule: API/DB layer only**.
- Persistence: `datasets(id, name, description, examples)` + migration 2 `is_sample`. Next
  append-only migration index is **5**. No `created_at` exists yet.
- Frontend: `DatasetsView.tsx` (list + import toggle), `DatasetImportPanel.tsx` (format radio →
  paste/upload → preview → freeze), Zod schemas + TanStack hooks in `web/src/lib/api.ts`.

## 3 · Architecture

### 3.1 Approach: extract-to-text, reuse existing parsers (chosen)

Documents are treated as **smart paste**. The server extracts a binary doc into the *normalized
text of an existing format*, hands it to the import textarea, and the proven
`preview → freeze` path runs unchanged. Binary-specific code is quarantined behind one new
endpoint; nothing downstream changes.

| Source | Extracts to | Reuses parser | Library |
| --- | --- | --- | --- |
| `.xlsx` | CSV-text (header row + `input`/`expected` columns) | `_parse_csv` | `openpyxl` (BSD) |
| `.docx` | Markdown-text (`## Input` / `## Expected`, incl. 2-col tables) | `_parse_markdown` | `python-docx` (MIT) |
| `.pdf` | Markdown-text (heading/structure inference) | `_parse_markdown` | `pypdf` (BSD) |

Rejected alternatives: dedicated binary→pairs parsers (duplicate logic, extraction errors not
user-fixable); extract-then-map UI (too much new UI for this slice).

### 3.2 New module: `src/orionfold/data/extractors.py`

Pure, keyless, deterministic — same discipline as `importers.py`.

```python
DocFormat = Literal["xlsx", "docx", "pdf"]

class ExtractResult(BaseModel):
    format: ImportFormat        # the target text format the doc was normalized into
    text: str                   # normalized CSV-text or Markdown-text
    warnings: list[str]         # extraction-level warnings (lossy pages, empty sheet, etc.)

def extract_document(data: bytes, doc_format: DocFormat) -> ExtractResult: ...
# internal: extract_xlsx(bytes)->(text,warnings); extract_docx(...); extract_pdf(...)
```

- `xlsx`: first worksheet; map columns case-insensitively to `input`/`expected` (mirror
  `_parse_csv` header logic); serialize back to CSV-text so the existing parser is the single
  source of truth. Warn on missing columns / empty sheet.
- `docx`: paragraphs → emit `## Input` / `## Expected` sections; also detect 2-column tables
  (col1=input, col2=expected) → emit paired sections. Warn when structure is ambiguous.
- `pdf`: extract text per page; infer Input/Expected headings; emit Markdown-text. Always warn
  that PDF extraction is lossy and the user should review before freezing.
- Raise a typed `DocExtractError(ValueError)` when a file can't be opened/parsed → HTTP 422.

### 3.3 New endpoint: `POST /api/datasets/extract`

- Multipart upload (`file`) + `doc_format` (or inferred from filename extension).
- **Size cap** (e.g. 5 MB) and extension allow-list enforced before reading; reject otherwise
  with 413/422. Never writes to disk or DB. No secrets, no network.
- Returns `ExtractResult` JSON `{format, text, warnings}`.
- The client then drives the existing `preview` / create flow with the returned `text`+`format`.

### 3.4 Tags, metadata, check hint (DB + API layer only)

Append-only migration index **5** (single `executescript`):

```sql
ALTER TABLE datasets ADD COLUMN tags        TEXT NOT NULL DEFAULT '[]';   -- JSON array[str]
ALTER TABLE datasets ADD COLUMN created_at  TEXT NOT NULL DEFAULT '';     -- ISO8601, '' for legacy/sample
ALTER TABLE datasets ADD COLUMN source      TEXT NOT NULL DEFAULT '';     -- 'pasted' | 'file:<name>' | format
ALTER TABLE datasets ADD COLUMN check_hint  TEXT NOT NULL DEFAULT '';     -- '' | 'substring' | 'numeric' | 'exact' | 'eyeball'
```

- These live on the **DB row + API `DatasetRow`** only. The domain `Dataset` model is
  untouched → `config_hash` stays `467ddd96c9a5`.
- `DatasetRow` gains: `tags: list[str]`, `created_at: str`, `source: str`,
  `check_hint: str | None`.
- `save_dataset(...)` gains optional `tags`, `source`, `check_hint`; stamps `created_at`
  (caller passes the timestamp — keep functions deterministic/testable). `seed_datasets`
  leaves the bundled sample's `created_at=''` and `tags=[]` (taggable later via PATCH).

### 3.5 New endpoint: `PATCH /api/datasets/{id}`

- Body: optional `tags`, `description`, `check_hint`. **Never** edits `examples` (protects the
  frozen, hashed content).
- 404 if id unknown; 200 with the updated `DatasetRow`.
- Repository: `update_dataset_meta(conn, id, *, tags=None, description=None, check_hint=None)`.

### 3.6 Tag color assignment

- Free-form labels. A deterministic helper (frontend) maps each distinct label → one of the
  five categorical tokens by a stable hash:
  `token = TOKENS[hash(label.toLowerCase()) % 5]` where `TOKENS=[t1,t2,t3,t5,t7]`.
- Tokens are **categorical, never interactive** (brand contract). Tag chips reuse the
  `.tag` / `t1..t7` styling from the brand values sheet (squared, dashed left border, mono).
- Color is presentation-only; the stored value is just the label string.

### 3.7 Frontend changes

- `DatasetImportPanel.tsx`:
  - File picker accepts `.jsonl,.csv,.md,.xlsx,.docx,.pdf`. On a **doc** upload → call
    `extractDataset(file)` → populate textarea + set format + show extraction warnings; user
    edits → existing Preview → Freeze. On a **text** file → today's FileReader path.
  - Auto-detect format from extension; manual radio remains an override.
  - New fields before Freeze: **tags** input (chips) and an optional **check-hint** select.
- `DatasetsView.tsx` / card: render a tags row (colored chips), a metadata line
  (`N examples · created <date> · <source>`), a check-hint chip, and an inline **edit tags**
  affordance (calls `PATCH`).
- `web/src/lib/api.ts`: extend `datasetSchema` (tags/created_at/source/check_hint, all loose
  for fixtures); add `extractDataset(file)` (multipart) and `updateDataset(id, patch)` hooks;
  invalidate `["datasets"]` after create/patch.

## 4 · Data flow

```
Upload .xlsx/.docx/.pdf
  → POST /api/datasets/extract (multipart)
  → ExtractResult{format, text, warnings}            [no write]
  → textarea populated, warnings shown, user edits
  → POST /api/datasets/preview {format, text}        [no write]  (existing)
  → POST /api/datasets {name, description, format, text, tags?, source?, check_hint?}
  → save_dataset(...) re-parses server-side (source of truth), stamps created_at  (201)
  → GET /api/datasets → cards show tags + metadata + check-hint
  → PATCH /api/datasets/{id} {tags?, description?, check_hint?}  → retroactive tagging
```

Text file (`.jsonl/.csv/.md`) and paste paths are unchanged (no extract step).

## 5 · Error handling

- Extraction failure → `DocExtractError` → 422 with a human message; the panel shows it inline
  (same pattern as preview errors).
- Oversize / disallowed file → rejected before read (413/422); never partially processed.
- Empty/ambiguous extraction → returns `text` + warnings (not an error) so the user can fix in
  the textarea; freeze still requires ≥1 valid pair (existing `DatasetParseError`).
- PATCH unknown id → 404. Duplicate-name on create → existing 409.
- New deps are sandboxed: extractors do no network and never log file contents (privacy posture;
  store may hold confidential client text).

## 6 · Testing

- **Unit (`tests/unit/test_extractors.py`)**: xlsx columns → CSV-text; docx headings + table →
  Markdown-text; pdf headings → Markdown-text; malformed/empty/oversize → `DocExtractError` or
  warnings; round-trip through `parse_dataset` yields expected pairs.
- **Unit (`test_storage.py`)**: `update_dataset_meta` round-trip; `save_dataset` with
  tags/source/check_hint; `created_at` stamping; tag JSON (de)serialization.
- **Integration (`test_proof_api.py`)**: `/extract` returns text+warnings without writing;
  oversize/bad-type rejected; `PATCH` round-trip + 404; create-with-tags appears in list.
- **Frontend**: import panel upload→extract→populate→preview→freeze; tag-color stability
  (same label → same token); inline edit-tags PATCH.
- **E2E (Playwright)**: upload a small `.xlsx` → preview → freeze → appears tagged in the list.
- **Invariants**: `RECEIPT_VERSION` and `config_hash 467ddd96c9a5` unchanged (assert/observe);
  domain `Dataset` model still has no extra fields; migrations append-only (index 5 added, 0–4
  untouched).

## 7 · Dependencies (require explicit operator approval before editing `pyproject.toml`)

| Package | License | Purpose | Why this one |
| --- | --- | --- | --- |
| `openpyxl` | MIT | read `.xlsx` | de-facto standard, pure-Python, no native build |
| `python-docx` | MIT | read `.docx` (paragraphs + tables) | standard, pure-Python |
| `pypdf` | BSD | extract `.pdf` text | pure-Python, lightweight; (vs `pdfplumber` which is heavier — defer unless layout fidelity needed) |

All are pure-Python, permissively licensed, single-purpose, no network. Backend-only (not
shipped to the browser bundle).

## 8 · Build sequence (for the plan)

1. Migration 5 + repository (`save_dataset` extend, `update_dataset_meta`, row reads) + tests.
2. `DatasetRow` fields + `GET` wiring + `PATCH` endpoint + integration tests.
3. `extractors.py` + `/extract` endpoint + deps (after approval) + unit/integration tests.
4. Frontend: api hooks + schema, import-panel upload/extract/tags/check-hint, card surfacing,
   inline edit + tests.
5. E2E path + invariant checks + worklog + HANDOFF update.
