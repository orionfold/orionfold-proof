# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-22 · **SHIPPED: Datasets completion (sub-project 1 of 3).** A three-part
sequenced effort was scoped from research into Orionfold brand/domains + the Arena sister product:
**Datasets → Leaderboard → Quick-Compare**, each its own spec→plan→build cycle. Sub-project 1 is
DONE: PDF/Word/Excel import (extract-to-text reuse), free-form auto-colored domain tags, card
metadata, and a display+suggest check hint. Engine, `config_hash 467ddd96c9a5`, and
`RECEIPT_VERSION 6` all untouched (verified). 4 backend deps added with operator approval
(openpyxl, python-docx, pypdf, python-multipart). `main` is local-only; git remote + push stay
queued LAST until packaging is done (operator directive)._

## ▶️ START HERE NEXT SESSION
1. **Open the app in a real browser first** (don't pick a task yet). The web source changed, so for
   the EMBEDDED path (`uv run orionfold dev`, `:8787`) run `bash scripts/build.sh` first; otherwise
   use live source `pnpm --dir web dev` (`:5173` → `:8787`).
   - ⚠️ `:8787` may be occupied by an unrelated app here — if so run the API on a free port
     (`uv run orionfold dev --port 8790`) and the UI with
     `VITE_DEV_PORT=5174 VITE_API_PROXY=http://127.0.0.1:8790 pnpm --dir web dev`.
   - Verify on **Datasets**: "Import dataset" accepts `.xlsx/.docx/.pdf` (uploading a doc fills the
     textarea with extracted text + warnings, editable before Preview); the freeze form has a tags
     input + check-hint select; cards show a tags row (colored squared chips), a metadata line
     (`N examples · created <date> · <source>`), a check-hint chip, and an inline "Edit tags".
2. **Then decide the next sub-project.** The plan is to do **sub-project 2: Leaderboard
   presentation** next (see below). **Brainstorm/confirm scope FIRST** before building.

## ✅ LAST SESSION — Datasets completion (sub-project 1 of 3)
> Evidence: `docs/worklog/2026-06-22-datasets-completion.md`. Spec + plan under
> `docs/superpowers/specs/` and `docs/superpowers/plans/` (`2026-06-22-datasets-completion*`).
> 10 TDD commits on `main` (migration → repo → API/PATCH → deps → extractors → /extract → api
> client → tag tokens → import panel → cards → e2e/handoff).

- **Doc import** = "smart paste": `POST /api/datasets/extract` (multipart, 5 MB cap, never writes)
  turns xlsx→CSV-text and docx/pdf→Markdown-text via `data/extractors.py`, feeding the EXISTING
  `parse_dataset` preview/freeze path. Extracted text is editable (handles PDF lossiness).
- **Tags / metadata / check-hint** live on the **DB row + API `DatasetRow` only** (migration
  index 5), never the domain model. `PATCH /api/datasets/{id}` edits tags/description/check_hint
  (never examples). Tag colors hash to the categorical `t1/t2/t3/t5/t7` value tokens (new `.of-tag`
  classes in `web/src/styles/index.css`).
- **Verification:** backend 254 passed; web 96 passed; `tsc` clean; pyright clean in changed files;
  `bash scripts/build.sh` + Playwright `dataset-import` & `dataset-doc-import` → 2 passed;
  `config_hash 467ddd96c9a5` / `RECEIPT_VERSION 6` / domain model all confirmed unchanged.

## ⏭️ NEXT: the two remaining sequenced sub-projects (brainstorm FIRST)
2. **Leaderboard presentation** (Arena clone-the-presentation, additive only): rank column + top-3
   medals, traffic-light **score bars**, a **$/quality** efficiency column, prominent local/private
   badge. Defer the sort toggle + Pareto frontier scatter. Mostly already-captured
   `LeaderboardEntry` data; only `$/quality` (if stored) bumps `RECEIPT_VERSION`.
3. **Quick-Compare → Proof Receipt** (thin Arena CompareDuel clone): a 1-prompt × 2-candidate
   "Quick Compare" entry mode reusing the existing matrix engine + exporter; head-to-head bars +
   pick-a-winner; "Save as Proof Receipt" labeled as a single-example quick check with a CTA to
   promote to a full run. **Do NOT** build the free-form chat lane or live token streaming.

## BACKLOG — non-blocking (after the sequenced sub-projects, or as operator picks)
1. **Catalog price/source accuracy pass** — verify list prices + context windows (`current-docs-check`).
2. **Cross-product models×prompts** — N models × M prompts in one run. **Brainstorm FIRST.**
3. **DS-skin polish** — shared token-driven badge/chip kit (the new `.of-tag` tokens are the seed);
   deepen per-figure mono; receipt proof-seal stamp.
4. **Richer sample data** — extend `sample_data.py` if onboarding wants it.
5. **Packaging · licensing · distribution** — LICENSE + source headers, PyPI metadata (dist
   `orionfold-proof`, CLI `orionfold`; reserve `orionfold` + `orionfold-arena`),
   `uv tool install orionfold-proof` → `orionfold up`, release notes / demo script. **Scope FIRST.**
6. **git remote + push** — **LAST item; do NOT surface or start until packaging (#5) is done**
   (operator directive). No remote configured; `main` holds all work unpushed.

## Key invariants to NOT regress
- **Datasets metadata (new):** `tags`/`created_at`/`source`/`check_hint` live on the DB row +
  API `DatasetRow` ONLY — never the domain `Dataset`/`Example` model (protects `config_hash`).
  Migrations append-only; next index is **6**. `check_hint` is **display+suggest only**; the engine
  never reads it. `/extract` never writes; `PATCH` never edits examples. `.of-tag` tokens are
  categorical + squared + never interactive.
- **Mocks:** bare ids `mock_good`/`mock_bad`; engine labels `Mock · good`/`Mock · bad`; picker
  groups them only when Sandbox is on. `config_hash 467ddd96c9a5` + `RECEIPT_VERSION 6` unchanged.
- **Sample detection:** receipts by `run_sample…` id prefix; datasets by the `is_sample` column.
- **Migrations append-only.** Settings is a global KV; e2e runs serial (shared webServer DB — scope
  list assertions to the target card).
- **The accent/status split (DS skin):** cyan `--color-accent` = the only interactive colour; green
  `--color-ok` = PASS/verified; semantic-token layer only; light + dark + AA; dark is `@theme`
  default; categorical value tags neutral/squared.
- **Proof Run setup:** shared `WorkflowStep` (`Step`/`StepLine`); `SelectField`'s `className` sizes
  the wrapper; decision recipes render only in the Models branch (recipes.json loads at backend
  startup — restart to see edits).

## Paste prompt for the next session
```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001/0002/0003,
latest worklog 2026-06-22-datasets-completion, and the specs/plans under docs/superpowers/).

FIRST, before any task: open the app in a real browser and click the Datasets screen — do NOT pick
work yet.
- Web source changed, so for the EMBEDDED path (`uv run orionfold dev`, :8787) run
  `bash scripts/build.sh` first; otherwise live source `pnpm --dir web dev` (:5173 → :8787).
- NOTE: :8787 may be occupied here — if so use `--port 8790` for the API and
  `VITE_DEV_PORT=5174 VITE_API_PROXY=http://127.0.0.1:8790 pnpm --dir web dev`.
- Confirm Datasets: doc import (.xlsx/.docx/.pdf → editable extracted text + warnings); tags +
  check-hint on the freeze form; cards show tags chips + metadata line + check-hint chip + inline
  "Edit tags".
THEN decide the next sub-project. Plan is sub-project 2 (Leaderboard presentation). BRAINSTORM scope
FIRST before building.

RECENT WORK (committed to main; no git remote; UI + import only, config_hash untouched):
- (latest) DATASETS completion (sub-project 1 of 3): PDF/Word/Excel import via extract-to-text reuse
  (POST /api/datasets/extract); free-form auto-colored domain tags + card metadata + display/suggest
  check hint (migration index 5, DB+API only); PATCH /api/datasets/{id} (meta only). 4 backend deps
  added (openpyxl, python-docx, pypdf, python-multipart). Verified: backend 254, web 96, e2e 2/2,
  config_hash 467ddd96c9a5 + RECEIPT_VERSION 6 unchanged. Evidence:
  docs/worklog/2026-06-22-datasets-completion.md.

NEXT (sequenced, brainstorm FIRST): (2) Leaderboard presentation — rank+medals, score bars,
$/quality, local/private badge (defer sort toggle + frontier scatter); (3) Quick-Compare → Proof
Receipt — thin CompareDuel clone reusing the engine + exporter, NOT a free-form chat lane.

BACKLOG (after the above / as operator picks): catalog price pass; cross-product models×prompts
(BRAINSTORM); DS-skin polish (token-driven badge/chip kit — .of-tag is the seed); richer sample
data; packaging·licensing·distribution (BRAINSTORM); git remote + push — LAST, do NOT surface until
packaging is done (operator directive).

Do NOT regress invariants in HANDOFF.md (datasets metadata DB+API-only / check_hint display-only /
config_hash 467ddd96c9a5 / RECEIPT_VERSION 6; append-only migrations next index 6; mock bare-ids;
DS accent/status split; e2e serial shared DB; WorkflowStep + SelectField + recipes-Models-only).
```
