# Dataset import — preview → confirm → freeze (review finding #9)

- **Date:** 2026-06-20
- **Status:** Design — approved in brainstorm, pending spec review
- **Origin:** UI/feature review finding #9 (`docs/worklog/2026-06-20-ui-feature-review.md`) — dataset
  import is a v0 charter must-have that is **entirely absent**, not merely missing a UI.

## Problem

The charter lists dataset import (JSONL / CSV / Markdown / paste → frozen input/expected text
pairs) as a v0 must-have. Investigation found the whole import layer is missing:

- No parser for any format. The only way a dataset enters the system is `seed_datasets()` loading
  the one bundled JSON file at startup (`src/orionfold/data/__init__.py`,
  `storage/repository.py`).
- No write path in the repository (`list_datasets`/`get_dataset` only; no `save_dataset`).
- No `POST /api/datasets` — the route surface is read-only (`GET /api/datasets`,
  `server/routes.py`).
- The `DatasetsView` is read-only; its empty state already advertises an import feature
  ("Import a JSONL, CSV, or Markdown set to get started") wired to nothing.

So this is a genuine full-stack charter gap: parsing layer → repository save → endpoints →
frontend import UI.

## Decisions (locked in brainstorm)

| Decision | Choice | Rationale |
|---|---|---|
| Formats | **All four**: JSONL · CSV · Markdown · paste | Full charter coverage. "Paste" is a *channel*, not a 4th format — the same three parsers fed from a textarea instead of a file. |
| Flow | **Preview → confirm → freeze** | Evidence-first: parse server-side and show the pairs + warnings before anything is saved. |
| Markdown shape | **Heading-delimited pairs** (`## Input` / `## Expected`, examples split by `---`) | Survives multi-paragraph prose, which is what this product's content is. Tables/inline-labels break on prose. |
| UI placement | **Inline collapsible panel** in the Datasets view | Matches the app's state-based nav; no modal/focus-trap or router machinery the app doesn't already use. Preview renders where the new dataset will land. |

## Existing facts the design builds on

- `domain/models.py`: `Example{input_text, expected_text}`, `Dataset{id, name, description="", examples}`.
- SQLite `datasets(id PK, name, description, examples TEXT)` — `examples` is a single JSON blob
  column. **No `frozen` flag, no separate examples table** — datasets are immutable-by-convention,
  so "freeze" means "create a new dataset row." No edit/delete path is in scope.
- Frontend: `DatasetsView.tsx` (read-only list), `getDatasets()` in `lib/api.ts`,
  `datasetSchema`/`exampleSchema` already defined. Mutation reference: `createRun`/`createRunStream`
  + `useMutation` + `invalidateQueries`. No existing file-input or textarea pattern — introduced here.

## Architecture

### Backend

**`src/orionfold/data/importers.py`** — new, pure, keyless module. Single entry point:

```
parse_dataset(text: str, fmt: Literal["jsonl", "csv", "markdown"]) -> ParseResult
```

`ParseResult` is a Pydantic model: `examples: list[Example]`, `warnings: list[str]`,
`count: int` (== `len(examples)`).

Per-format rules:

- **JSONL** — one JSON object per non-blank line. Keys `input`/`expected`, falling back to
  `input_text`/`expected_text`. Malformed JSON or missing keys on a line → skip + warning naming
  the 1-based line number.
- **CSV** — stdlib `csv.DictReader`. Columns `input` + `expected`, matched case-insensitively
  (also accept `input_text`/`expected_text`). Row missing either value → skip + warning naming the
  1-based row number.
- **Markdown** — scan for `## Input` / `## Expected` heading pairs. Heading level-agnostic (`#`..`######`)
  and case-insensitive; section content runs from after the heading line until the next heading or a
  `---` horizontal rule or EOF. An `Input` without a following `Expected` (or vice-versa) → skip +
  warning naming the example index.

Shared validation (all formats): trim leading/trailing whitespace on both fields; if either is
empty after trim, skip + warning. **At least one valid example is required** — zero valid examples
is a parse error (surfaced as HTTP 422), not an empty success.

**`storage/repository.py`** — add `save_dataset(conn, dataset: Dataset) -> Dataset`:
- **Name uniqueness is the conflict rule.** Before insert, check whether a dataset with the same
  `name` (case-insensitive, trimmed) already exists; if so, raise a `DuplicateDatasetError` that the
  route maps to HTTP 409. Rationale: two datasets both called "Foo" in the leaderboard is confusing;
  a calm product refuses rather than silently disambiguates.
- `id` = slug of `name` (lowercase, non-alphanumeric → `-`, collapse repeats, trim). Because two
  *distinct* names can slug to the same id (e.g. "My Set!" and "My Set"), append `-2`, `-3`, … until
  the id is free. This id de-dup is a safety net, **not** the conflict path — name collisions are
  already rejected above, so it only fires for genuinely different names.
- Plain `INSERT` (not `INSERT OR IGNORE`) so any unexpected id conflict still surfaces.

**`server/routes.py`** — two endpoints, both accepting JSON `{format, text}`. The browser reads an
uploaded file with `FileReader` and posts its text, so the **server never handles multipart** — one
code path for both file and paste channels.

- `POST /api/datasets/preview` — body `{format, text}` → `parse_dataset` → returns
  `ParseResult{examples, warnings, count}`. **No write.** Zero valid examples → 422 with a clear
  message.
- `POST /api/datasets` — body `{name, description?, format, text}` → re-parses server-side (the
  POST is the source of truth; never trust a client-supplied example list) → `save_dataset` →
  returns the saved `Dataset`. Duplicate name → 409; zero valid examples → 422.

### Frontend

**`lib/api.ts`** — add:
- `previewDataset({format, text}) -> ParseResult` (new `parseResultSchema` = `{examples:
  exampleSchema[], warnings: string[], count: number}`).
- `createDataset({name, description?, format, text}) -> Dataset` (reuse `datasetSchema`).

**`features/proof/DatasetImportPanel.tsx`** — new collapsible panel:
- Format radio: JSONL / CSV / Markdown.
- Channel: a file picker **and** a paste `<textarea>` — either populates the same `text` state
  (choosing a file reads it via `FileReader` into the textarea, so the user sees what they're
  importing and can edit before preview).
- **Preview** button → `previewDataset` → renders the parsed input/expected pairs, a warnings strip
  (skipped lines/rows), and the valid count.
- **Name** field (required) + **Freeze dataset** button → `createDataset` → on success
  `queryClient.invalidateQueries(["datasets"])`, collapse the panel, reset state; the new dataset
  appears in the list.
- States: empty (no text) · previewing (loading) · preview-ready · preview-with-warnings ·
  error (422 parse fail / 409 duplicate name) · success. Core actions keyboard-accessible; the
  panel toggle and primary buttons are real `<button>`s.

**`features/proof/ViewShell.tsx`** — add an optional header `action` slot (right-aligned in the
header) so the Datasets view can mount an "Import dataset" toggle button without a bespoke layout.

**`features/proof/DatasetsView.tsx`** — render the "Import dataset" toggle in the `ViewShell`
action slot; show `DatasetImportPanel` above the list when toggled open.

**`app/App.tsx`** — no new global state required; the panel's open/closed state is local to the
Datasets view. (`DatasetsView` currently takes no props; it keeps managing its own query and gains
local panel state.)

## Error handling

- **422** (parse error — zero valid examples) → panel shows the server message inline, keeps the
  user's text so they can fix and retry.
- **409** (duplicate dataset name) → name field shows "a dataset named X already exists"; user
  renames and retries. The already-parsed preview is preserved.
- **Per-row warnings** never block import — they inform. A user can freeze a 4-example dataset from a
  6-line file with 2 skipped lines, having seen exactly what was skipped.
- Network/unknown error → generic inline error, text preserved.

## Testing

**Backend (`tests/`)** — all keyless:
- Parser unit tests per format: happy path; malformed line/row (skipped + warning); both-key vs
  fallback-key JSONL; case-insensitive CSV headers; Markdown heading level/case variants and
  `---`/EOF boundaries; whitespace-only field skipped; zero-valid → error.
- Endpoint tests: `preview` returns pairs and **does not write** (assert dataset count unchanged);
  `POST /api/datasets` round-trips (the new dataset is then readable via `GET`); 422 on zero valid;
  409 on duplicate name; id slug de-dup on a name whose slug already exists.

**Frontend (`web/`)**:
- `DatasetImportPanel` test: paste JSONL → Preview → assert pairs + warning strip render → enter
  name → Freeze → assert `createDataset` called and `["datasets"]` invalidated.

**e2e (`web/`)**: a focused Playwright spec (not folded into the happy path, to keep that lean) —
open Datasets, open the import panel, paste a 2-line JSONL, Preview, name it, Freeze, assert it
appears in the list. Confirm scope at plan time.

## Out of scope (deferred)

- Editing or deleting datasets (no update/delete path exists; import only creates).
- A CLI `import` subcommand (HTTP-first; CLI can follow if wanted).
- Server-side multipart upload (browser reads file text; server stays JSON-only).
- Large-file streaming / size caps beyond a simple sanity limit (datasets are "small, frozen sets").
- Schema migration / a `frozen` column — datasets remain immutable-by-convention.
- Per-format auto-detection — the user picks the format explicitly.

## Non-regression

Purely additive. No change to: existing test-contract strings, the Proof Run default view, the
3-format receipt, `RECEIPT_VERSION` (still 3), or the batch/stream run endpoints. New routes are
additive; `GET /api/datasets` is unchanged.
