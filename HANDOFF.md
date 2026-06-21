# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-21 · **Scoring-section DESIGN POLISH (operator live review) + folder rename
finished. Frontend-only, merge-ready.** Two things this session:_

1. _**Folder rename finished** (`orionfold-proof-claude` → `orionfold-proof`). `uv sync --reinstall`
   repointed ALL `.venv/bin/*` shebangs (plain `uv sync` only fixes the editable project pkg → stale
   pytest/etc. interpreters); two old-name doc refs updated; `git grep orionfold-proof-claude` clean.
   Commit `9771cd2`. Worklog `2026-06-21-folder-rename.md`._
2. _**Scoring-method UI polish** (operator drove it in-browser; HMR loop). (a) **All four method cards
   now sit in ONE responsive row** (`lg:grid-cols-4`, 2×2 narrow): Auto/Keypoint/Similarity/LLM judge,
   equal width AND height — `MethodCard` is now `flex h-full flex-col` with the cost chip pinned to the
   bottom (`mt-auto`) so chips align; guidance reworded to ~52 chars each + `text-balance` so every card
   wraps to two even lines. The two uppercase group headers ("Free · instant · repeatable" / "Costs
   money · adds latency") were REPLACED by a single helper line; the free-vs-paid guard now lives in each
   card's cost chip (`Free` vs `$ per run · slower`). (b) **JudgeFilter is now a single-row stepper that
   matches the top StageStepper** — ①②③ filled-accent number badges + `h-px w-5 bg-(--color-panel-line)`
   hairline connectors (NOT arrow icons — operator asked for consistency with Configure/Run/Decide);
   "Run on / Optimize / Judge model" labels, lines, AND controls all inline on one row (`flex flex-wrap
   items-center`). Added `aria-label="Judge model"` to the `<select>` (the old `<label>` wrapper was
   dropped → needed for a11y + the e2e `getByLabel`). Gated hint reworded to "Pick one once its key is
   set below." (the old "Add a key…" duplicated the KeyEntry's `/add a key/` text → made a test match two
   nodes). (c) **`vite.config.ts`**: dev `port` + `/api` proxy target are now env-overridable
   (`VITE_DEV_PORT` / `VITE_API_PROXY`, defaults unchanged) so a 2nd checkout runs on free ports without
   colliding with the sibling codex checkout (8787/5173)._

_**No backend/scoring/receipt change — RECEIPT_VERSION stays 5, config_hash untouched.** Files changed:
`MethodCard.tsx`, `ScoringMethod.tsx`, `JudgeFilter.tsx`, `vite.config.ts`. vitest 72/72 · build clean
(tsc+vite) · e2e 5/5 (rebuilt embed first) · browser-verified on isolated ports 5180→8790. KEYLESS
INVARIANT intact: Mock judge stays the Local+Cheapest default; `mock_good`/`mock_bad` never judge
options; Auto omits the rubric → server resolves `default_rubric_for`. Design-polish commit is HEAD on
`main` (NOT pushed — no remote). Worklog `2026-06-21-scoring-section-design-polish.md`._

_LESSON: vitest does NOT typecheck AND does not run the e2e — for a layout change run BOTH
`pnpm --dir web build` AND the Playwright e2e (rebuild the embed via `bash scripts/build.sh` first,
since `orionfold up` serves the embedded cockpit, not vite). Dropping a `<label>` wrapper silently
breaks `getByLabel` — add an explicit `aria-label`._

_Prior session: **Scoring-section redesign** shipped grouped method cards + the two-step judge filter
(this session reflowed them into one row + a stepper). Before that: **meaning-aware scoring (Finding 2)**
— keypoint-coverage + LLM-judge scoring, RunCostSummary, RECEIPT_VERSION 4→5._
>
> **NEXT SESSION — #6 PROMPT-VARIANT CANDIDATES** (the next candidate axis): same model, different
> system prompt, compared in one run — composes with the picker (#4) + recipes (#5) and the new
> scoring methods; still text-in/text-out, **no new provider machinery**. It is creative/feature
> work → **brainstorm FIRST** (`superpowers:brainstorming`), then spec → plan → subagent-driven, same
> loop. THEN the **catalog price/source accuracy pass** (roadmap; non-blocking — a measured receipt
> cost always outranks a list price). Workflows/RAG remain post-v0._

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001 +
ADR-0002 + ADR-0003, and the latest worklogs: 2026-06-21-meaning-aware-scoring,
2026-06-20-leaderboard-recommendation-fix, 2026-06-20-decision-recipes).

RECENT WORK (committed to main, not pushed — no git remote configured):
- (this session) SCORING-SECTION REDESIGN (frontend-only), merge-ready. Grouped method cards
  (free=Auto/Keypoint/Similarity, paid=LLM judge) w/ guidance + cost indicators; two-step judge filter
  (Local/Hosted=privacy → Cheapest/Balanced/Best=tier) → model <select> w/ opinionated default; Auto card
  shows resolved kind; control moved INTO RunSetup form above Run proof. New web/src/features/proof units:
  scoring.ts (resolveAutoKind; filterJudgeModels — excludes mock_good/bad, default = mockJudge ?? recommended
  ?? latest ?? first, gated=unavailable cloud w/ KeyEntry), MethodCard.tsx, JudgeFilter.tsx; ScoringMethod.tsx
  slimmed 308→54; selectionMeta.ts += METHOD_META/JUDGE_TIERS; api.ts += keypoints field + exported Privacy
  TYPE; RunSetup/ProofCockpit placement. NO backend change (RECEIPT_VERSION 5, config_hash untouched). vitest
  72/72, build clean, e2e 5/5, pure-frontend. Do NOT regress: Mock judge is the keyless Local+Cheapest default
  (recommended:false but IS the default); mock_good/mock_bad never judge options; Auto omits rubric → server
  resolves default_rubric_for. Spec/plan: docs/superpowers/{specs,plans}/2026-06-21-scoring-section-redesign*.
- (prior session) MEANING-AWARE SCORING (live-review Finding 2), merge-ready. RubricKind +=
  keypoint, judge. scoring/rubric.py: score_keypoints(keypoints, output, rubric) = fraction whose
  normalized text is a substring of the normalized output (empty list → 0.0 sentinel; the ENGINE
  owns the fallback-to-similarity for keypoint-less rows via a module-level _SIMILARITY);
  default_rubric_for(dataset) → keypoint if any example has keypoints else similarity. scoring/judge.py
  (NEW): JudgeOutcome(score, cost_usd, latency_ms, error); parse_score (>10→/100, >2→/10, (1,2]→clamp
  — documented+tested); MockJudge (difflib, fixed 0.0001/5, keyless/pure); LLMJudge (reuses
  safe_generate → inherits redaction; provider-error OR unparseable → error outcome score 0.0);
  build_judge(rubric) (mock_judge→MockJudge else LLMJudge; ValueError if no judge_provider_id).
  engine.py: iter_matrix branches (candidate-error short-circuits BEFORE judge; keypoint; judge carries
  cost/latency + outcome.error→row.error+did_pass False; else unchanged); judge built ONCE pre-loop;
  build_cost_summary(rows). models.py: Example.keypoints; Rubric.judge_provider_id/judge_model;
  ResultRow.judge_cost_usd/judge_latency_ms; RunCostSummary; ProofReport.cost_summary (zeroed
  default_factory so old persisted reports read back). receipts/export.py: RECEIPT_VERSION 5;
  _scored_by + "cost" block; MD/HTML "Scored by"+"Run cost". routes.py: RunRequest.rubric Rubric|None;
  both endpoints `body.rubric or default_rubric_for(dataset)`; judge pre-validated → 422 on
  ValueError+KeyError; stream threads the RESOLVED rubric through iter_matrix+ProofRun+config_hash.
  Frontend: api.ts rubric/judge + cost_summary schemas + scoredByLabel; ScoringMethod.tsx picker
  (reuses getSelection + KeyEntry; CLOUD_KEY_NAMES → shared selectionMeta.ts); ProofCockpit rubric
  state (null=Auto, omitted from run request when null) + DecisionSummary/ReceiptsView "Scored by" +
  "Run cost". Demo dataset got keypoints; samples regenerated (config_hash 467ddd96c9a5).
- (prior) LEADERBOARD RECOMMENDATION FIX (Finding 1 + fable-5 removal Finding 3). DECISION RECIPES (#5),
  MODEL-PER-CANDIDATE PICKER (#4), MODEL CATALOG (#1), DATASET IMPORT (#9).

THE DECISION-RECIPES THREAD (operator's strategic bet). Done: #1 catalog, #4 picker, #5 recipes.
LIVE-REVIEW FINDINGS: ALL THREE DONE (#1 leaderboard bug, #2 similarity rubric, #3 fable-5).

>> START HERE — #6 PROMPT-VARIANT CANDIDATES: same model, different system prompt, compared in one
   run. The next candidate axis; composes with the picker + recipes + the new scoring methods; still
   text-in/text-out, NO new provider machinery. Creative/feature work → invoke superpowers:brainstorming
   FIRST (present a design, get operator approval), then spec → plan → subagent-driven, same loop.
   THEN the CATALOG PRICE/SOURCE accuracy pass (roadmap, non-blocking). Workflows/RAG remain post-v0.

Do NOT regress (meaning-aware scoring invariants): keypoint coverage = fraction of authored keypoints
present (normalized substring); default_rubric_for picks keypoint only when a dataset has keypoints,
NEVER judge (judge is opt-in, needs a key); MockJudge (judge_provider_id="mock_judge") is the keyless
deterministic judge that keeps the suite keyless. A JUDGE error is an ERROR (row.error set, did_pass
False), NOT a low-scoring fail — so an all-errored judge candidate ranks last; the candidate's own
provider error short-circuits BEFORE the judge is consulted (judge_cost stays 0). Judge cost lives ONLY
in ResultRow.judge_cost_usd + RunCostSummary — it MUST NOT enter a candidate's estimated_cost_usd or
leaderboard.py ranking. RECEIPT_VERSION stays 5 (bump on ANY further receipt-schema change);
ProofReport.cost_summary keeps its zeroed default_factory (old-report read-back). The judge API key
NEVER appears in a receipt/log/response — the judge reuses safe_generate's redaction; Rubric has no key
field. Keypoints must be normalized substrings of their expected_text (so mock_good stays 5/5). Auto =
omit the rubric → server resolves default_rubric_for. A misconfigured/unavailable judge → 422 (not 500).

Plus the STANDING invariants: leaderboard NEVER recommends a 0-pass/all-errored candidate; calm NEUTRAL
"No clear winner" state across cockpit + 3 receipt formats; errored rows say "errored, no output".
Keyless mock default (mocks pre-selected, bare-id, model=None); Proof Run is the DEFAULT view; both run
endpoints route through build_candidates; /api/selection + /api/catalog + /api/recipes leak NO secrets;
/api/credentials NEVER echoes a key + writes ONLY whitelisted cloud providers to a 0o600 .env.local;
the global 422 input-stripping handler stays. Test-contract strings ("Orionfold Proof", "Connected",
button /Run proof/, regions Leaderboard / Failure cases / Proof Receipt export, "Export
Markdown|HTML|JSON", "100% (5/5)", "Failure cases (5)", "simulated provider failure"). Verdict
vocabulary includes "No clear winner"; the receipt also shows a "Scored by" line + "Run cost" summary.
Tailwind v4: CSS vars use the PARENTHESIS shorthand bg-(--color-x), never bg-[--color-x].

NOTES (non-blocking):
- A sibling orionfold-proof-codex checkout runs its own servers; leave its processes/tabs alone and
  bind a PROVABLY-FREE port (assert the listener PID is yours). uvicorn does NOT hot-reload backend
  code OR the @cache load_catalog()/load_recipes() data — RESTART `orionfold up` after backend/catalog/
  recipe changes. The embedded cockpit is served from src/orionfold/server/static (gitignored; rebuilt
  by `bash scripts/build.sh` — REBUILD before any e2e or browser check). catalog.json + recipes.json +
  the bundled dataset (with keypoints) ship in the wheel automatically.
- The harness emits STALE TS diagnostics mid-edit (false "cannot find module" / "no exported member",
  e.g. it claimed scoredBy/cost_summary/ScoringMethod were missing AFTER they were added). False
  alarms — trust `pnpm --dir web build` (tsc --noEmit && vite build) + the actual test/e2e runs.
  @playwright/test "cannot find module" in e2e specs is a perennial false alarm (resolves at runtime).
- The Playwright e2e uses a fresh DB; a STALE local server/DB (reuseExistingServer when not CI) can
  cause a false failure — kill the port + delete /tmp/orionfold-e2e.db, rebuild the embed, re-run.
- create-dataset route field is `text` (not `content`): POST /api/datasets {name, format, text}.
- Regenerate sample receipts after ANY receipt change: `uv run python scripts/gen_samples.py` (now uses
  default_rubric_for(dataset) → keypoint; mock_good stays 5/5 ⭐, mock_bad error_count=1).
Start in plan mode for anything substantial; brainstorm creative/feature work first. Verify with
uv run pytest, uv run ruff check src tests, pnpm --dir web test, the Playwright e2e (rebuild embed
first), and a real browser/server check on a free port. Open review-bound markdown in Obsidian one at
a time. Append a docs/worklog entry and overwrite HANDOFF.md.
```

## Where to look (durable context)

- `docs/worklog/2026-06-21-meaning-aware-scoring.md` — this session's evidence (latest).
- `docs/superpowers/specs/2026-06-21-meaning-aware-scoring-design.md` ·
  `docs/superpowers/plans/2026-06-21-meaning-aware-scoring.md` — design + 12-task plan.
- `docs/worklog/2026-06-20-leaderboard-recommendation-fix.md` · `2026-06-20-decision-recipes.md` —
  the three live-review findings (all now addressed) + recipes thread.
- `docs/ux/product-design-system.md` — the three-pane target + Theming subsection.
- `docs/adr/0001-…-architecture.md` · `0002-provider-integration-and-credentials.md` ·
  `0003-streaming-run-progress.md` — Accepted.
- `docs/release-charter.md` — v0 scope, journey, acceptance criteria (Accepted; all met).
- `CHANGELOG.md` ([Unreleased] now covers meaning-aware scoring + run-cost + RECEIPT_VERSION 5) ·
  `docs/demo-script.md`.
- `.claude/rules/{providers,receipts,storage}.md` — enforced constraints.
- `CLAUDE.md` — operating guide and release gates.

## Ship-candidate quick reference

- Build wheel: `bash scripts/build.sh` → `dist/orionfold_proof-0.1.0-py3-none-any.whl`
  (cockpit + dataset embedded, RECEIPT_VERSION=5, catalog.json + recipes.json bundled). dist/ and
  src/orionfold/server/static are gitignored.
- Clean-install check: `uv venv /tmp/x && uv pip install --python /tmp/x/bin/python dist/*.whl`
  then `/tmp/x/bin/orionfold up --port <free>` — bind a PROVABLY-FREE port; confirm the listener
  PID is yours.
- Dev: `uv run orionfold dev` + `pnpm --dir web dev`. Tests: `uv run pytest` · `uv run ruff check
  src tests` · `pnpm --dir web test` · `pnpm --dir web e2e` (rebuild embed first). Frontend build:
  `pnpm --dir web build`.
- Regenerate sample receipts after any receipt change: `uv run python scripts/gen_samples.py`.
- Inspect recipes live: `curl -s localhost:<port>/api/recipes | python -m json.tool`. Picker panel:
  `curl -s localhost:<port>/api/selection | python -m json.tool`.
- Env knobs: `OPENAI_API_KEY` `OPENROUTER_API_KEY` `GEMINI_API_KEY` `ANTHROPIC_API_KEY` (also
  settable in-app via POST /api/credentials → .env.local); `OLLAMA_HOST` `OPENAI_BASE_URL`
  `OPENROUTER_BASE_URL` `LMSTUDIO_BASE_URL`;
  `ORIONFOLD_{OLLAMA,OPENAI,OPENROUTER,GEMINI,ANTHROPIC,LMSTUDIO}_MODEL` (override catalog default);
  `ORIONFOLD_MAX_TOKENS` (2048) `ORIONFOLD_TIMEOUT_S` (120) `ORIONFOLD_ENV_FILE` `ORIONFOLD_DB`.
