# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-22 · **SHIPPED: Leaderboard presentation (sub-project 2 of 3).** Of the
three sequenced sub-projects (**Datasets → Leaderboard → Quick-Compare**), 1 and 2 are now DONE.
Sub-project 2 = an additive presentation upgrade: a `#`/medal rank column, a traffic-light
pass-rate **score bar**, a **`$ / quality`** efficiency column, and a strengthened **Local** privacy
tag — plus `$/quality` carried into the receipt (**`RECEIPT_VERSION` 6 → 7**). Ranking sort key,
proof engine, and `config_hash 467ddd96c9a5` all untouched (verified). 5 TDD commits on `main`.
`main` is local-only; git remote + push stay queued LAST until packaging is done (operator
directive)._

## ▶️ START HERE NEXT SESSION
1. **Open the app in a real browser first** (don't pick a task yet). The web source changed, so for
   the EMBEDDED path (`uv run orionfold dev`, `:8787`) run `bash scripts/build.sh` first; otherwise
   use live source `pnpm --dir web dev` (`:5173` → `:8787`).
   - ⚠️ `:8787` may be occupied here by an unrelated "dashboard" app — if so run the API on a free
     port (`uv run orionfold dev --port 8790`, already running this session) and the UI with
     `VITE_DEV_PORT=5174 VITE_API_PROXY=http://127.0.0.1:8790 pnpm --dir web dev` (Vite may land on
     `:5175` if `5174` is taken).
   - Verify on a **populated leaderboard** (Receipts → open a winner receipt → "Explore in cockpit",
     scroll to LEADERBOARD): a `#` column with 🥇🥈🥉 medals **only when there's a winner**; a green/
     amber/red pass-rate **bar**; a **`$ / quality`** column ("Free"/"—"/`$x.xxxx`); the **Local** tag
     reads bolder (lock glyph) than **Cloud**. Open the HTML receipt preview → "Receipt schema v7" +
     `$ / quality` column. (Old pre-v7 runs correctly show `$/quality` "—".)
2. **Then decide the next sub-project.** Plan is **sub-project 3: Quick-Compare → Proof Receipt**
   (see below). **Brainstorm/confirm scope FIRST** before building.

## ✅ LAST SESSION — Leaderboard presentation (sub-project 2 of 3)
> Evidence: `docs/worklog/2026-06-22-leaderboard-presentation.md`. Spec + plan under
> `docs/superpowers/specs|plans/2026-06-22-leaderboard-presentation*`.
> 5 TDD commits on `main` (field → receipt+samples → schema+helpers → table → local tag).

- **`$/quality`** = `cost_per_quality: float | None` on `LeaderboardEntry` only (`total_estimated_cost_usd / avg_score`; `None` when `avg_score==0` → "—"; `0.0` when free → "Free"). **Presentation only — NOT a ranking key.** Serialized into MD/HTML/JSON; **`RECEIPT_VERSION` 7**.
- **Table** (`web/.../Leaderboard.tsx`): `#`/medal column (`medalFor` gates on `entries.some(e=>e.recommended)`), pass-rate **bar** (`passRateTone` → `--color-ok` ≥0.8 / `--color-warn` ≥0.5 / `--color-danger`; **status tokens, never the accent**), `$ / quality` column (`formatCostPerQuality`). Pure helpers in `web/.../leaderboardFormat.ts`.
- **Local tag** (`web/.../badges.tsx`): `local` variant → `Lock` icon + `text-(--color-ink) font-semibold`; cloud/mock unchanged. **Green `--color-ok` deliberately NOT used for local** (reserved for PASS).
- **Verification:** backend **259** passed; web **110** passed; `tsc` clean; changed-file `pyright` 0 new errors; samples regenerated with **`config_hash 467ddd96c9a5` unchanged**; receipts secret-free; browser-verified medals/bar/`$ /quality`/Local; `proof.spec.ts:100` (leaderboard+receipt) e2e green.

## ⏭️ NEXT: the final sequenced sub-project (brainstorm FIRST)
3. **Quick-Compare → Proof Receipt** (thin Arena CompareDuel clone): a 1-prompt × 2-candidate
   "Quick Compare" entry mode reusing the existing matrix engine + exporter; head-to-head bars +
   pick-a-winner; "Save as Proof Receipt" labeled as a single-example quick check with a CTA to
   promote to a full run. **Do NOT** build the free-form chat lane or live token streaming.

## BACKLOG — non-blocking (after sub-project 3, or as operator picks)
0. **Pre-existing e2e failure (small):** `e2e/playwright/proof.spec.ts:89` asserts a recipe button
   `/Same model, different providers/i`, but the recipe is now titled **"Different providers"**
   (decision question "Same model, different hosts…"). One-line e2e assertion fix. NOT caused by
   sub-project 2 (neither `recipes.json` nor `proof.spec.ts` was touched).
0b. **Stored "Recommended on 0/5":** some 2026-06-21 stored runs persisted `recommended: true` on a
   0-pass candidate (saved before the 2026-06-20 recommend-gate took effect that session), so the
   cockpit shows a medal/badge for them. New runs are correct. Optional one-off recompute/backfill.
1. **Catalog price/source accuracy pass** — verify list prices + context windows (`current-docs-check`).
2. **Cross-product models×prompts** — N models × M prompts in one run. **Brainstorm FIRST.**
3. **DS-skin polish** — shared token-driven badge/chip kit (`.of-tag` + the new `TONE_BAR`/strengthened
   `ProviderTag` are seeds); deepen per-figure mono; receipt proof-seal stamp.
4. **Richer sample data** — extend `sample_data.py` if onboarding wants it.
5. **Packaging · licensing · distribution** — LICENSE + source headers, PyPI metadata (dist
   `orionfold-proof`, CLI `orionfold`; reserve `orionfold` + `orionfold-arena`),
   `uv tool install orionfold-proof` → `orionfold up`, release notes / demo script. **Scope FIRST.**
6. **git remote + push** — **LAST item; do NOT surface or start until packaging (#5) is done**
   (operator directive). No remote configured; `main` holds all work unpushed.

## Key invariants to NOT regress
- **Leaderboard `$/quality` (new):** `cost_per_quality` lives on `LeaderboardEntry` (a derived report
  object) ONLY — never the engine-hashed domain models — and **never enters the ranking sort key**
  `(_all_errored, -pass_rate, -avg_score, avg_latency_ms, total_estimated_cost_usd)`. `RECEIPT_VERSION`
  is now **7**; the `$/quality` display rule (`None→"—"`, `0→"Free"`, else `$x.xxxx`) is written
  identically in Python (`_cost_per_quality_label`) and TS (`formatCostPerQuality`). Score bar +
  Local tag use **status tokens / neutral ink, never `--color-accent` or `--color-ok` for non-PASS**.
- **Datasets metadata:** `tags`/`created_at`/`source`/`check_hint` live on the DB row + API `DatasetRow`
  ONLY — never the domain `Dataset`/`Example` model. Migrations append-only; next index is **6**.
  `check_hint` is display+suggest only; `/extract` never writes; `PATCH` never edits examples.
- **Mocks:** bare ids `mock_good`/`mock_bad`; engine labels `Mock · good`/`Mock · bad`; picker
  groups them only when Sandbox is on. `config_hash 467ddd96c9a5` unchanged.
- **Sample detection:** receipts by `run_sample…` id prefix; datasets by the `is_sample` column.
- **Migrations append-only.** Settings is a global KV; e2e runs serial (shared webServer DB — scope
  list assertions to the target card).
- **The accent/status split (DS skin):** cyan `--color-accent` = the only interactive colour; green
  `--color-ok` = PASS/verified ONLY; semantic-token layer only; light + dark + AA; dark is `@theme`
  default; categorical value tags neutral/squared.
- **Proof Run setup:** shared `WorkflowStep` (`Step`/`StepLine`); `SelectField`'s `className` sizes
  the wrapper; decision recipes render only in the Models branch (recipes.json loads at backend
  startup — restart to see edits).

## Paste prompt for the next session
```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001/0002/0003,
latest worklog 2026-06-22-leaderboard-presentation, and the specs/plans under docs/superpowers/).

FIRST, before any task: open the app in a real browser and check a POPULATED leaderboard — do NOT
pick work yet.
- Web source changed, so for the EMBEDDED path (`uv run orionfold dev`, :8787) run
  `bash scripts/build.sh` first; otherwise live source `pnpm --dir web dev` (:5173 → :8787).
- NOTE: :8787 may be occupied by an unrelated app here — if so use `--port 8790` for the API and
  `VITE_DEV_PORT=5174 VITE_API_PROXY=http://127.0.0.1:8790 pnpm --dir web dev` (Vite may use :5175).
- Confirm the leaderboard (Receipts → open a winner receipt → "Explore in cockpit" → scroll to
  LEADERBOARD): #/medal column (🥇🥈🥉 only with a winner), traffic-light pass-rate bar, $ / quality
  column (Free/—/$x.xxxx), strengthened Local tag (lock, bolder than Cloud). Receipt preview shows
  "Receipt schema v7" + the $ / quality column.
THEN decide the next sub-project. Plan is sub-project 3 (Quick-Compare → Proof Receipt). BRAINSTORM
scope FIRST before building.

RECENT WORK (committed to main; no git remote; presentation + receipt only, config_hash untouched):
- (latest) LEADERBOARD presentation (sub-project 2 of 3): #/medal rank column, traffic-light
  pass-rate score bar, $ / quality efficiency column, strengthened Local tag; $/quality stored on
  LeaderboardEntry + serialized into the receipt (RECEIPT_VERSION 6→7), presentation-only, ranking
  unchanged. Verified: backend 259, web 110, tsc/pyright clean, samples regen with config_hash
  467ddd96c9a5 unchanged, browser + receipt-quality verified. Evidence:
  docs/worklog/2026-06-22-leaderboard-presentation.md.

NEXT (sequenced, brainstorm FIRST): (3) Quick-Compare → Proof Receipt — thin 1-prompt × 2-candidate
CompareDuel clone reusing the matrix engine + exporter; head-to-head bars + pick-a-winner; "Save as
Proof Receipt" as a single-example quick check. NOT a free-form chat lane, NOT live token streaming.

BACKLOG (after the above / as operator picks): pre-existing e2e fix (proof.spec.ts:89 recipe rename);
optional stored-recommended-on-0/5 backfill; catalog price pass; cross-product models×prompts
(BRAINSTORM); DS-skin polish (token kit — .of-tag + TONE_BAR + strengthened ProviderTag are seeds);
richer sample data; packaging·licensing·distribution (BRAINSTORM); git remote + push — LAST, do NOT
surface until packaging is done (operator directive).

Do NOT regress invariants in HANDOFF.md (leaderboard $/quality on LeaderboardEntry only + never a
ranking key / RECEIPT_VERSION 7 / display rule identical in Py+TS / score-bar+Local use status-tokens
not accent and never --color-ok for non-PASS; datasets metadata DB+API-only / check_hint display-only
/ config_hash 467ddd96c9a5; append-only migrations next index 6; mock bare-ids; DS accent/status
split; e2e serial shared DB; WorkflowStep + SelectField + recipes-Models-only).
```
