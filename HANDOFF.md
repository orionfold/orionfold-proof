# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-21 · **#6 PROMPT-VARIANT CANDIDATES — SHIPPED, merge-ready.** A new comparison
axis: hold the model fixed, vary the system prompt ("one model, N prompts" in a single run).
Brainstorm → spec → plan → subagent-driven (12 tasks) → Opus whole-branch review (Ready to merge=YES,
0 Critical/0 Important) → operator-approved cleanup. 14 commits `41cc8e2..d411e71` on `main` (NOT
pushed — no remote)._

**What shipped.** A `Compare by: Models | Prompts` toggle in the Proof Run setup. Models mode = the
existing picker + recipes, unchanged. Prompts mode = pick ONE model + author ≥2 named system prompts;
the server fans them into one candidate per prompt; each becomes a leaderboard row; the receipt
records every variant's full prompt text (provenance). The architectural seam: **`system_prompt` is a
field on `Candidate`**, so a prompt variant is just a candidate — the 2-D matrix, streaming,
leaderboard, scoring, failure browser are all unchanged. **No new provider machinery.**

**Key invariants (do NOT regress):**
- **config_hash** includes `system_prompt` ONLY when non-None → model-compare runs hash byte-identical
  (zero churn; locked by `test_config_hash_unchanged_for_model_compare_runs` + a same-id assertion).
- **RECEIPT_VERSION is now 6** (bump on ANY further receipt-schema change). `prompt_variants` is
  additive/optional; old persisted reports still deserialize. Sample config_hash stayed `467ddd96c9a5`.
- **Keyless invariant**: mocks ignore `system_prompt` (deterministic); `defaultPromptModel` prefers an
  available (keyless mock) model so prompt-compare runs keyless. The e2e proves the path on a mock.
- **Identity**: variant id = `{model_id}#{slug}` (deduped); `#` is distinct from the `:` model split —
  engine routes on bare `provider_id`, `build_candidates` splits on `:`. No routing/parse hazard.
- **Both run endpoints** route through one `_resolve_candidates` (422 on not-one-model / <2 variants /
  empty fields; `UnknownCandidateError` → 400; global 422 input-stripping handler intact).
- **Model-compare path is behaviorally unchanged** when the toggle is on Models (the default); its run
  request carries NO `prompt_variants` key. Secrets: prompt text is author instructions, never a key.
- Frontend helpers live in **`promptVariantsHelpers.ts`** (renamed from `promptVariants.ts` to avoid a
  case-only collision with the `PromptVariants.tsx` component). Baseline starter prompt is drift-locked
  to the server `TASK_SYSTEM_PROMPT` by a test.

**Verification at close (HEAD `d411e71`):** `uv run pytest` 213 passed (1 pre-existing 3rd-party
StarletteDeprecationWarning) · `uv run ruff check src tests` clean · `pnpm --dir web test` 83/83 (22
files) · `pnpm --dir web build` clean (tsc+vite) · `bash scripts/build.sh && pnpm --dir web e2e` 6/6.

> **NEXT SESSION — pick one (all non-blocking):**
> 1. **Catalog price/source accuracy pass** (roadmap) — a few catalog values UNVERIFIED; a measured
>    receipt cost always outranks a list price, so this is refinement, not a gate.
> 2. **Prompt-aware mocks** — make `mock_good`/`mock_bad` deterministically vary output with the system
>    prompt so the KEYLESS prompt-compare demo differentiates scores (today mocks tie on a prompt run).
> 3. **Cross-product (models × prompts)** — only if a real need appears (deliberately deferred in #6).
> 4. **Set up a git remote + push** — none configured; ALL `main` commits are local.
> Workflows/RAG remain post-v0. Creative/feature work → brainstorm FIRST.

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001 + ADR-0002 +
ADR-0003, and the latest worklogs: 2026-06-21-prompt-variant-candidates,
2026-06-21-scoring-section-design-polish, 2026-06-21-meaning-aware-scoring).

RECENT WORK (committed to main, not pushed — no git remote configured):
- (this session) #6 PROMPT-VARIANT CANDIDATES — SHIPPED, merge-ready. New axis: hold model fixed, vary
  system prompt ("one model, N prompts" in one run). Compare-by Models|Prompts toggle. system_prompt is
  a Candidate field (variant = candidate; 2-D matrix unchanged; NO new provider machinery).
  expand_prompt_variants mints {model_id}#{slug} candidates; server _resolve_candidates fans out in both
  run endpoints (422 on not-one-model/<2/empty). config_hash conditional (zero churn for model runs;
  variants distinct). RECEIPT_VERSION 5→6 records each variant's prompt + honest repro. Frontend:
  api.ts types, promptVariantsHelpers.ts (renamed from promptVariants.ts — case-collision), PromptVariants
  editor, RunSetup toggle + ProofCockpit run-request branches. e2e keyless prompt-compare. Opus
  whole-branch review = Ready to merge YES, 0 Critical/0 Important. Spec/plan:
  docs/superpowers/{specs,plans}/2026-06-21-prompt-variant-candidates*. Commits 41cc8e2..d411e71.
- (prior) SCORING-SECTION DESIGN POLISH (one-row method cards + judge stepper). MEANING-AWARE SCORING
  (keypoint + LLM-judge, RECEIPT_VERSION 4→5). DECISION RECIPES (#5), MODEL PICKER (#4), CATALOG (#1).

>> START HERE — pick one non-blocking option (none is a gate):
   1. Catalog price/source accuracy pass (roadmap refinement).
   2. Prompt-aware mocks (so the keyless prompt-compare demo differentiates scores; today mocks tie).
   3. Cross-product models×prompts (only if a real need appears; deferred in #6).
   4. Set up a git remote + push (all main commits are local).
   Workflows/RAG remain post-v0. Creative/feature work → brainstorm FIRST.

Do NOT regress (#6 invariants): config_hash includes system_prompt ONLY when non-None (model-compare
runs hash byte-identical — zero churn; the sample config_hash is 467ddd96c9a5); RECEIPT_VERSION is 6
(bump on any further receipt change), prompt_variants additive/optional so old reports deserialize;
mocks ignore system_prompt (keyless prompt-compare = plumbing demo, not score-differentiator);
defaultPromptModel prefers an available keyless mock; variant id = {model_id}#{slug} (deduped), # distinct
from the : model split so engine routes on bare provider_id; both run endpoints go through
_resolve_candidates (422 on not-one-model/<2-variants/empty; UnknownCandidateError→400); model-compare
run request carries NO prompt_variants key and is behaviorally unchanged (toggle defaults to "models");
prompt text is author instructions, never a secret; frontend helpers are promptVariantsHelpers.ts (NOT
promptVariants.ts — renamed to avoid the case-collision with PromptVariants.tsx); Baseline starter prompt
is drift-locked to server TASK_SYSTEM_PROMPT by a test.

Plus the STANDING invariants: meaning-aware scoring (keypoint coverage = fraction of authored keypoints
present; default_rubric_for picks keypoint only when a dataset has keypoints, NEVER judge; MockJudge is
the keyless deterministic judge; a JUDGE error is an error not a low-scoring fail; judge cost stays in
ResultRow.judge_cost_usd + RunCostSummary, never in estimated_cost_usd or leaderboard ranking; a
misconfigured judge → 422). Leaderboard NEVER recommends a 0-pass/all-errored candidate; calm NEUTRAL
"No clear winner" across cockpit + 3 receipt formats; errored rows say "errored, no output". Keyless mock
default (mocks pre-selected, bare-id, model=None); Proof Run is the DEFAULT view; both run endpoints route
through build_candidates; /api/selection + /api/catalog + /api/recipes leak NO secrets; /api/credentials
NEVER echoes a key + writes ONLY whitelisted cloud providers to a 0o600 .env.local; the global 422
input-stripping handler stays. Test-contract strings ("Orionfold Proof", "Connected", button /Run proof/,
regions Leaderboard / Failure cases / Proof Receipt export, "Export Markdown|HTML|JSON", "100% (5/5)",
"Failure cases (5)", "simulated provider failure"). Verdict vocabulary includes "No clear winner"; the
receipt shows a "Scored by" line + "Run cost" summary + (for prompt runs) a "Prompt variants" section.
Tailwind v4: CSS vars use the PARENTHESIS shorthand bg-(--color-x), never bg-[--color-x].

NOTES (non-blocking):
- A sibling orionfold-proof-codex checkout runs its own servers (8787/5173); leave its processes/tabs
  alone and bind a PROVABLY-FREE port. uvicorn does NOT hot-reload backend code OR the @cache
  load_catalog()/load_recipes() data — RESTART `orionfold up` after backend/catalog/recipe changes. The
  embedded cockpit is served from src/orionfold/server/static (gitignored; rebuilt by `bash scripts/build.sh`
  — REBUILD before any e2e or browser check).
- The frontend `test` script is `vitest run` (already non-watch) — run `pnpm --dir web test` (NOT
  `--run`, which pnpm mis-parses). e2e: `pnpm --dir web e2e` (rebuild the embed first). The harness emits
  STALE TS "cannot find module" diagnostics mid-edit (e.g. claimed compareBy absent from RunSetupProps
  after it was added; claimed ./promptVariants missing) — trust `pnpm --dir web build` + the actual
  test/e2e runs. @playwright/test "cannot find module" in e2e specs is a perennial false alarm.
- The Playwright e2e uses a fresh DB; a STALE local server/DB can cause a false failure — kill the port +
  delete /tmp/orionfold-e2e.db, rebuild the embed, re-run. The receipt preview iframe is CSP-sandboxed,
  so e2e asserts receipt content via the JSON receipt (page.request.get), not the iframe.
- create-dataset route field is `text` (not `content`): POST /api/datasets {name, format, text}.
- Regenerate sample receipts after ANY receipt change: `uv run python scripts/gen_samples.py` (now v6;
  model-compare samples carry prompt_variants: []).
Start in plan mode for anything substantial; brainstorm creative/feature work first. Verify with
uv run pytest, uv run ruff check src tests, pnpm --dir web test, the Playwright e2e (rebuild embed first),
and a real browser/server check on a free port. Open review-bound markdown in Obsidian one at a time.
Append a docs/worklog entry and overwrite HANDOFF.md.
```

## Where to look (durable context)

- `docs/worklog/2026-06-21-prompt-variant-candidates.md` — this session's evidence (latest).
- `docs/superpowers/specs/2026-06-21-prompt-variant-candidates-design.md` ·
  `docs/superpowers/plans/2026-06-21-prompt-variant-candidates.md` — approved design + 12-task plan.
- `docs/worklog/2026-06-21-scoring-section-design-polish.md` · `2026-06-21-meaning-aware-scoring.md` —
  the prior two sessions.
- `docs/ux/product-design-system.md` — the three-pane target + Theming subsection.
- `docs/adr/0001-…-architecture.md` · `0002-provider-integration-and-credentials.md` ·
  `0003-streaming-run-progress.md` — Accepted.
- `docs/release-charter.md` — v0 scope, journey, acceptance criteria (Accepted; all met).
- `CHANGELOG.md` ([Unreleased] now covers prompt-variant candidates + RECEIPT_VERSION 6) ·
  `docs/demo-script.md`.
- `.claude/rules/{providers,receipts,storage}.md` — enforced constraints.
- `CLAUDE.md` — operating guide and release gates.

## Ship-candidate quick reference

- Build wheel: `bash scripts/build.sh` → `dist/orionfold_proof-0.1.0-py3-none-any.whl`
  (cockpit + dataset embedded, RECEIPT_VERSION=6, catalog.json + recipes.json bundled). dist/ and
  src/orionfold/server/static are gitignored.
- Clean-install check: `uv venv /tmp/x && uv pip install --python /tmp/x/bin/python dist/*.whl`
  then `/tmp/x/bin/orionfold up --port <free>` — bind a PROVABLY-FREE port; confirm the listener
  PID is yours.
- Dev: `uv run orionfold dev` + `pnpm --dir web dev`. Tests: `uv run pytest` · `uv run ruff check
  src tests` · `pnpm --dir web test` · `pnpm --dir web e2e` (rebuild embed first). Frontend build:
  `pnpm --dir web build`.
- Regenerate sample receipts after any receipt change: `uv run python scripts/gen_samples.py`.
- Inspect a prompt-compare run: POST /api/runs with `{dataset_id, candidate_ids: ["<model>"],
  prompt_variants: [{name, system_prompt}, …]}`.
- Env knobs: `OPENAI_API_KEY` `OPENROUTER_API_KEY` `GEMINI_API_KEY` `ANTHROPIC_API_KEY` (also
  settable in-app via POST /api/credentials → .env.local); `OLLAMA_HOST` `OPENAI_BASE_URL`
  `OPENROUTER_BASE_URL` `LMSTUDIO_BASE_URL`;
  `ORIONFOLD_{OLLAMA,OPENAI,OPENROUTER,GEMINI,ANTHROPIC,LMSTUDIO}_MODEL` (override catalog default);
  `ORIONFOLD_MAX_TOKENS` (2048) `ORIONFOLD_TIMEOUT_S` (120) `ORIONFOLD_ENV_FILE` `ORIONFOLD_DB`.
