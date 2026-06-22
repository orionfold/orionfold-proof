# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-22 · **SHIPPED: Proof Run setup polish** — numbered "① Select dataset / ②
Compare by" stepper, custom select chevron (shared `SelectField`), Prompt-variants header moved above
the boxes + 50% model select, decision recipes scoped to Models mode and retitled. Commits
`cfcaad5`…`49f8d51` on `main`. **All UI/copy only — no data-model / engine / receipt / `config_hash`
surface touched.** v0 stays real-world-verified. Remaining work is the non-blocking backlog — next
substantive item is **packaging · licensing · distribution**; **git remote + push is queued LAST and
must not be surfaced until packaging is done** (operator directive). `main` is local-only (~11
commits unpushed)._

## ▶️ START HERE NEXT SESSION
1. **Open the app in a real browser first** (don't pick a task yet). Boot it, open the Proof Run
   screen, and confirm the shipped polish reads right.
   - ⚠️ **Web source changed since the last `bash scripts/build.sh`** — the EMBEDDED bundle is stale.
     For the embedded path (`uv run orionfold dev`, `:8787`) **rebuild first**; otherwise use live
     source: `pnpm --dir web dev` (`:5173`, proxies `/api` → `:8787`; needs `orionfold dev` running).
   - ⚠️ This machine had **:8787 occupied by an unrelated app** ("self-wealth" dashboard). If so, run
     the API on a free port: `uv run orionfold dev --port 8790`, and live UI with
     `VITE_DEV_PORT=5174 VITE_API_PROXY=http://127.0.0.1:8790 pnpm --dir web dev`.
   - Verify on Proof Run: **① Select dataset / ② Compare by** render as a numbered stepper (cyan
     badges + hairline connector — same language as the top Configure/Run/Decide stepper and the
     LLM-judge ①②③ controls); all three selects (dataset, prompt-model, judge-model) show the custom
     down-chevron with right padding; in **Models** mode "Start from a decision recipe" sits INSIDE
     the section above Candidates (titles: Cost vs quality / Local vs cloud / Cheapest that passes /
     Different providers); switch to **Prompts** → recipes disappear, "Prompt variants" header sits
     ABOVE the prompt boxes, Prompt-model select is 50% wide on desktop.
2. **Then STOP and wait for operator feedback** on what to do next. Do NOT start a backlog item or
   any new work until the operator picks the next action.

## ✅ LAST SESSION — Proof Run setup polish (UI/copy only)
> Evidence: `docs/worklog/2026-06-22-proof-run-stepper-and-select-chevron.md` and
> `…-decision-recipes-models-only.md`. Commits `cfcaad5`, `74b050f`, `d2aa91f`, `004126d`, `49f8d51`
> (+ paired `docs:` worklog commits) on `main`.

- **Numbered stepper:** Dataset + Compare-by are now "① Select dataset --- ② Compare by". Extracted
  shared `WorkflowStep.tsx` (`Step` + `StepLine`) from `JudgeFilter`, so the judge picker and run
  setup share one badge/connector source of truth (alongside the stateful top `StageStepper`).
- **Custom select chevron:** new `SelectField.tsx` (+ `selectCls` in `formStyles.ts`) — native
  `appearance-none` + lucide `ChevronDown` + `pl-3 pr-9` (avoids the `px-3`/`pr-9` source-order
  race). `className` sizes the WRAPPER (the chevron's positioning context) so width is controllable
  without breaking the chevron. Applied to all three selects: dataset `w-full sm:w-[27rem]`,
  prompt-model `w-full md:w-1/2`, judge-model `w-full text-sm sm:w-80`.
- **Prompt variants:** title+subtitle moved BELOW the Prompt-model picker to head the actual prompt
  boxes. The `<fieldset>/<legend>` became a `<div>` + sub-heading (a `<legend>` only captions as the
  fieldset's first child).
- **Decision recipes → Models-only:** a recipe pre-fills the candidate MODEL panel, which a Prompts
  run ignores (`candidate_ids:[promptModel]`), so `RecipeRow` now renders only in RunSetup's Models
  branch (passed in as a `recipes?: ReactNode` slot). Titles retitled crisp/general in
  `src/orionfold/recipes/recipes.json`. **recipes.json loads at BACKEND STARTUP — restart the API to
  see edits** (`--reload` watches `.py`, not `.json`).

**Verification:** `tsc` clean · `pnpm --dir web test` 90/90 · real-browser (live source :5174 →
:8790) all states confirmed in dark + light. **NOT re-run this session:** `bash scripts/build.sh`
(embedded bundle) and `pnpm --dir web exec playwright test` (e2e). Run both before declaring
ship-clean.

## ⚠️ OPERATOR ACTION (env, NOT code) — stale shell `OPENAI_API_KEY` shadows `.env.local`
Precedence is system-env-first by design (`config/keys.py`). A stale exported `OPENAI_API_KEY` (suffix
`_0MA`) shadowed the good `.env.local` key (suffix `qVYA`). Fix: clear/refresh the stale shell key.

## BACKLOG — do NOT start until the operator picks the next action (see START HERE)
1. **Catalog price/source accuracy pass** — verify list prices + context windows vs current provider
   docs (`current-docs-check`).
2. **Cross-product models×prompts** — N models × M prompts in one run. **Brainstorm FIRST.**
3. **DS-skin polish (roadmap write-back):** cyan `m-fill` leaderboard score bars; shared token-driven
   badge/chip kit; deepen per-figure mono; categorical dataset/domain tag; receipt proof-seal stamp.
4. **Richer sample data** — extend `sample_data.py` (more sample datasets) if onboarding wants it.
5. **Packaging · licensing · distribution** — finalize shipping for Orionfold Proof: LICENSE +
   source headers, PyPI packaging/metadata (dist name `orionfold-proof`, CLI `orionfold`; reserve
   `orionfold` + `orionfold-arena`), `uv tool install orionfold-proof` → `orionfold up` install path,
   release notes / demo script. **Brainstorm/scope FIRST.**
6. **git remote + push** — **LAST item; do NOT surface, suggest, or start this until packaging ·
   licensing · distribution (#5) is done** (operator directive). No remote configured; `main` holds
   all work unpushed.

Workflows/RAG remain post-v0. Any creative/feature work → **brainstorm FIRST**.

## Key invariants to NOT regress
- **Mocks:** bare ids `mock_good`/`mock_bad`; engine labels `Mock · good`/`Mock · bad`; only the
  picker presentation groups them under a `mock` provider (Good/Bad models) and only when Sandbox is
  on. `config_hash 467ddd96c9a5` + `RECEIPT_VERSION 6` unchanged. Domain `Dataset` model has NO
  `is_sample` (it lives in the API `DatasetRow` only) so `config_hash` is safe.
- **Sample detection:** receipts by `run_sample…` id prefix (hex ids never collide); datasets by the
  `is_sample` column (user "Sample …" names slug to `sample-…`, so id-prefix would be unsafe there).
- **Migrations append-only.** Settings is a global KV; e2e runs serial to avoid shared-DB races.
- **The accent/status split (DS skin):** cyan `--color-accent` = the only interactive colour; green
  `--color-ok` = PASS/verified; `--color-danger`/`--color-warn` = status; semantic-token layer only;
  light + dark + AA; dark is the `@theme` default; provider/identity tags neutral + squared.
- **Proof Run setup (new):** the inline `WorkflowStep` (`Step`/`StepLine`) is the shared
  badge+connector primitive — reuse it, don't fork. `SelectField`'s `className` sizes the wrapper,
  not the `<select>`. Recipes only render in the Models branch.
- **Standing:** prompt-aware mocks (`_shape_for_prompt` returns same `base` object on
  system_prompt-None + cue-less paths; pure/deterministic; `mock_bad` raises on
  `_stable_int(input)%5==0` before shaping); #6 prompt variants; meaning-aware scoring; `/api/*` leak
  no secrets; `.env.local` 0o600.

## Paste prompt for the next session
```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001/0002/0003,
latest worklogs incl. 2026-06-22-proof-run-stepper-and-select-chevron and
-decision-recipes-models-only).

FIRST, before any task: open the app in a real browser and click the Proof Run screen — do NOT pick
work yet.
- Web source changed since the last build, so for the EMBEDDED path (`uv run orionfold dev`, :8787)
  run `bash scripts/build.sh` first; otherwise use live source `pnpm --dir web dev` (:5173 → :8787).
- NOTE: :8787 may be occupied by an unrelated app here — if so use `--port 8790` for the API and
  `VITE_DEV_PORT=5174 VITE_API_PROXY=http://127.0.0.1:8790 pnpm --dir web dev` for the UI.
- Confirm: ① Select dataset / ② Compare by numbered stepper; all selects show the custom chevron;
  Models mode shows "Start from a decision recipe" inside the section above Candidates (Cost vs
  quality / Local vs cloud / Cheapest that passes / Different providers); Prompts mode hides recipes,
  puts the "Prompt variants" header above the boxes, and the Prompt-model select is 50% on desktop.
THEN STOP and wait for operator feedback. Do NOT start any backlog item until the operator picks it.

RECENT WORK (committed to main; no git remote configured; UI/copy only, config_hash untouched):
- (latest) PROOF RUN setup polish: numbered ①/② stepper (shared WorkflowStep extracted from
  JudgeFilter); custom select chevron (SelectField + selectCls) on all 3 selects; Prompt-variants
  header moved above the boxes + 50% model select; decision recipes scoped to Models mode and
  retitled crisp (recipes.json loads at backend startup — restart to see edits). Commits
  cfcaad5..49f8d51. Verified: web 90/90, tsc clean, real-browser dark+light. NOT re-run: build.sh +
  Playwright e2e. Evidence: docs/worklog/2026-06-22-proof-run-stepper-and-select-chevron.md,
  -decision-recipes-models-only.md.
- (prior) THEME chooser → Settings → Appearance card; first-run default DARK. Commit 7e413b0.
- (prior) SETTINGS — sample data / sandbox / mocks off the default picker. Orionfold DS skin + brand.

BACKLOG (only after operator picks): (1) catalog price/source pass (current-docs-check);
(2) cross-product models×prompts — BRAINSTORM FIRST; (3) DS-skin polish; (4) richer sample data;
(5) packaging · licensing · distribution — BRAINSTORM/scope FIRST; (6) git remote + push — LAST, do
NOT surface or suggest until packaging (#5) is done (operator directive). Operator chore: refresh
stale shell OPENAI_API_KEY. Creative work → brainstorm FIRST.

Do NOT regress the invariants in HANDOFF.md (mock bare-ids + engine labels + config_hash 467ddd96c9a5;
domain Dataset has no is_sample; append-only migrations; e2e serial; DS accent/status split; shared
WorkflowStep + SelectField-wrapper-sizing + recipes-Models-only; prompt-aware-mocks / #6 / standing).
```
