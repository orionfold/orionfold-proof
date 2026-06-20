# 2026-06-20 — Dataset import (review finding #9)

## Summary
Closed the one real v0 **charter acceptance gap in the UI**: users can now import their own dataset.
The charter lists dataset import (JSONL / CSV / Markdown / paste → frozen input/expected pairs) as a
must-have, but investigation found the whole layer was **absent** — no parser, no write path, no
`POST /api/datasets`, and a read-only Datasets view whose empty state advertised an import feature
wired to nothing. This session built it full-stack via brainstorm → spec → plan →
subagent-driven execution (6 TDD tasks, per-task spec+quality reviews, Opus whole-branch review).

### What shipped
- **Parser** (`src/orionfold/data/importers.py`, new, pure/keyless): `parse_dataset(text, fmt) ->
  ParseResult{examples, warnings, count}`. JSONL (both `input`/`expected` and `*_text` key
  spellings), CSV (`csv.DictReader`, case-insensitive headers, names the missing column on failure),
  Markdown (**heading-delimited** `## Input` / `## Expected` pairs, level-agnostic, split on `---`/EOF
  — chosen because the product's content is prose, which breaks Markdown tables). Each parser
  skips unreadable rows with a numbered warning; **zero valid examples → `DatasetParseError`**.
- **Repository** (`storage/repository.py`): `save_dataset(conn, name, description, examples)` —
  **name-unique** (case-insensitive, trimmed) → `DuplicateDatasetError`; `id` is a unique slug
  (distinct names that slug the same de-dup `-2`, `-3`…). The uniqueness check runs **before** id
  assignment, so a same-name re-insert can never silently acquire a `-2`. **No schema migration** —
  uses the existing `datasets` table.
- **Endpoints** (`server/routes.py`): `POST /api/datasets/preview` (parses, returns pairs +
  warnings, **never writes** — enforced structurally: the handler takes no `Request`) and
  `POST /api/datasets` (201; **re-parses server-side** as source of truth, never trusts a client
  example list). `DatasetParseError`→**422**, `DuplicateDatasetError`→**409**.
- **Frontend**: `lib/api.ts` gains `previewDataset` / `createDataset` (+ `parseResultSchema`,
  `importFormatSchema`) with Zod-at-the-boundary; `ViewShell` gains an optional header `action`
  slot; new **`DatasetImportPanel`** (format radios · file picker **and** paste textarea, file read
  client-side via `FileReader` so the server stays JSON-only · **Preview → parsed pairs + warnings
  + count → name → Freeze**); `DatasetsView` toggles it above the unchanged list. On freeze:
  `invalidateQueries(["datasets"])` → close → the new dataset appears (and is then selectable in a
  Proof Run).
- **Flow**: preview → confirm → freeze (evidence-first — you see the exact pairs before committing).

New files: `importers.py` (+test), `DatasetImportPanel.tsx` (+test), `api.test.ts`,
`e2e/playwright/dataset-import.spec.ts`, design spec + plan under `docs/superpowers/`. Touched:
`repository.py`, `routes.py`, `api.ts`, `ViewShell.tsx`, `DatasetsView.tsx`, and the two
test files those extend.

## Verification
- **Backend:** `uv run pytest` → **91 passed** (+10 parser unit, +3 storage, +5 endpoint); ruff clean;
  pyright 0.
- **Frontend:** `pnpm --dir web test` → **16 passed** (+`DatasetImportPanel` 2, +`api.test` 2).
  `pnpm --dir web build` clean.
- **e2e:** rebuilt the embed (`bash scripts/build.sh`), then `pnpm --dir web e2e` → **2/2** — the
  existing proof-loop happy path **and** the new import flow (paste a 2-line JSONL → Preview → name →
  Freeze → the card appears) against the real shipped artifact.
- **Reviews:** per-task spec+quality gates all Approved (3 Important findings fixed mid-flight: CSV
  warning now names the missing column; import file input gained an `aria-label`;
  `previewMutation.reset()` clears a stale preview error on input change). **Final whole-branch review
  (Opus): Ready to merge — Yes**, no Critical/Important. It verified the load-bearing properties:
  preview/create parse identically, the name-uniqueness ordering is provably safe, imported text is
  auto-escaped (React text nodes — no XSS), and the change is additive (no migration/schema/receipt
  touch, `RECEIPT_VERSION` still 3).

Commits (on `main`, not pushed): `1001a60` · `03290fb` · `1f8864a` · `f83e4fb` · `26673b6` ·
`9184f93` · `6f4ac9f` · `ca7d69c` · `71855ae` (+ spec `2d67e25`, plan `38f6ec8`).

## Product impact
The product now lets a consultant prove **their own task**, not just the bundled demo — which is the
charter's headline outcome ("I compared my AI options on *my own task*"). Import is artifact-honest:
you preview the exact frozen pairs and see what was skipped before anything is saved, and the server
re-parses so the stored dataset can never drift from what you reviewed.

## Risks / follow-ups
- **Deferred Minors** (none blocking; logged in `.superpowers/sdd/progress.md`): CSV/Markdown
  whitespace-skip paths are correct but untested; `preview` route lacks an explicit `status_code=200`
  (defaults to 200, asserted by a test); `(err as Error).message` cast isn't defensive against
  non-Error rejections; a `postJson` helper would DRY the two inline POST client fns once a third
  appears; the parsed-pairs `<ol>` isn't visually numbered.
- **Out of scope (by design):** editing/deleting datasets, a CLI `import` command, server-side
  multipart upload, large-file size caps, per-format auto-detection. All in the spec's out-of-scope list.
- Browser evidence is the Playwright e2e (renders the real embedded build end-to-end); a manual
  screenshot is available on request if `localhost` is re-allowed in the Chrome extension.

## Next recommended step
Operator review of the shipped import flow (try a JSONL paste, a CSV, and a Markdown set; confirm
409 on a duplicate name). Then pick the next backlog thread: the cheap **#2 sticky rail footer**, or
the strategic **#5 decision recipes** (named comparison presets — its own brainstorm).
