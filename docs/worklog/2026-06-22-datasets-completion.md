# Worklog — 2026-06-22 · Datasets completion (sub-project 1 of 3)

## Summary
Completed the **Datasets** feature past its v0 floor, as the first of three sequenced
sub-projects (Datasets → Leaderboard → Quick-Compare). Two operator-approved thrusts:

1. **Easier to create (broad ICP):** import **PDF / Word / Excel** on top of the existing
   JSONL / CSV / Markdown / paste. Documents are treated as "smart paste" — the server
   extracts a binary doc into the *normalized text of an existing format* (xlsx→CSV-text,
   docx/pdf→Markdown-text) behind one new endpoint; the proven preview→freeze pipeline is
   unchanged and the extracted text is editable before freezing (handles PDF lossiness).
2. **Richer & trustworthy:** free-form **domain tags** (auto-colored from the categorical
   `t1/t2/t3/t5/t7` value tokens), **card metadata** (examples · created · source), and a
   dataset-level **check hint** that displays and *suggests* a rubric at run-setup. Tags are
   editable retroactively (incl. the bundled sample) via a new PATCH endpoint.

Design + plan: `docs/superpowers/specs/2026-06-22-datasets-completion-design.md`,
`docs/superpowers/plans/2026-06-22-datasets-completion.md`.

## What changed
- **Backend**
  - Migration **index 5**: `datasets` gains `tags`, `created_at`, `source`, `check_hint`
    (append-only; indices 0–4 untouched).
  - `repository.py`: `DatasetMeta` model; `list_dataset_rows` now returns
    `(Dataset, DatasetMeta)`; new `get_dataset_meta` / `update_dataset_meta`; `save_dataset`
    extended with `tags`/`source`/`check_hint`/`created_at`. **All metadata lives on the DB row +
    API only — the domain `Dataset`/`Example` models are unchanged**, so `config_hash` is safe.
  - `data/extractors.py` (new): `extract_document` (xlsx/docx/pdf) + `normalize_pairs_to_markdown`
    + `doc_format_for`; pure, keyless, `DocExtractError` → 422.
  - `routes.py`: `DatasetRow` carries the metadata; `POST /api/datasets/extract` (multipart, 5 MB
    cap, never writes); `PATCH /api/datasets/{id}` (tags/description/check_hint only — never
    examples); `create_dataset` stamps `created_at` and returns a `DatasetRow`.
- **Frontend**
  - `lib/api.ts`: `datasetSchema` gains optional metadata (loose, matching `is_sample`);
    `extractResultSchema`; `extractDataset(file)`, `updateDataset(id, patch)`; `createDataset`
    body extended.
  - `features/proof/tags.ts` + `TagChips.tsx`: stable hashed `tagToken`, `CHECK_HINTS`,
    `checkHintLabel`. `styles/index.css`: categorical `.of-tag` tokens (squared, never
    interactive) from the brand values sheet (dark default + light override).
  - `DatasetImportPanel.tsx`: doc upload → `/extract` → editable textarea + warnings; tags input;
    check-hint select. `DatasetsView.tsx`: `DatasetCard` shows tags, metadata line, check-hint
    chip, and inline "Edit tags" (PATCH).
- **Dependencies (operator-approved):** `openpyxl`, `python-docx`, `pypdf`,
  `python-multipart` — pure-Python, permissive, backend-only, no network.

## Verification
- `uv run pytest` → **254 passed** (10 storage + 7 extractor + extract/PATCH/tags integration).
- `uv run pyright src/orionfold` → **clean in all changed files** (pre-existing errors remain in
  `receipts/export.py` and `recipes/resolution.py`, untouched here).
- `pnpm --dir web test` → **96 passed** (25 files); `pnpm --dir web exec tsc --noEmit` → clean
  (app; e2e `.spec.ts` excluded as before).
- `bash scripts/build.sh` → embedded bundle rebuilt; `playwright test dataset-import
  dataset-doc-import` → **2 passed** (paste JSONL path + upload .xlsx → extract → tag → freeze).
- **Invariants held:** computed `config_hash` for the canonical keyless config = **467ddd96c9a5**
  (unchanged); `RECEIPT_VERSION` = **6** (unchanged); domain `Dataset` =
  `{description, examples, id, name}` and `Example` = `{expected_text, input_text, keypoints}`
  (no new fields).

## Product impact
A non-technical knowledge worker can now drop in a spreadsheet or document of question/answer
pairs (not just engineer-shaped JSONL), review and fix the extraction, tag it by domain, and
freeze a trustworthy, labeled dataset — broadening the ICP without touching the proof engine or
the receipt. Reinforces the brand's "speed to a usable dataset" and "trust you can verify".

## Risks / notes
- **PDF extraction is lossy** by nature; mitigated by the editable-text review step + an explicit
  warning. Excel/Word map cleanly.
- **Tag colors are hash-derived**, not user-chosen — stable per label but two labels can share a
  hue. Acceptable for categorical brand expression; revisit if users want to pick colors.
- **Check hint is display+suggest only** — the engine never reads it (`config_hash` protected).
  Per-row, scoring-driving checks remain a deferred, ADR-gated future spec.
- Legacy/seeded datasets show no `source`/`created` (empty) — intentional; only user-created rows
  stamp them.
- E2E specs share one webServer DB (serial) — new assertions are scoped to each test's card.

## Next recommended step
**Sub-project 2: Leaderboard presentation** (next sequenced spec): rank + top-3 medals, traffic-
light score bars, a `$/quality` efficiency column, and a prominent local/private badge — all
additive to data the receipt already carries (one `RECEIPT_VERSION` bump only if `$/quality` is
stored). Brainstorm/confirm scope first.
