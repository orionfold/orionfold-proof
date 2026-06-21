# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-21 · **PROMPT-AWARE MOCKS — SHIPPED, merge-ready.** The keyless mock
providers now deterministically vary output by the candidate's system prompt, so the #6
prompt-compare demo produces a real winner with NO API key (was: all variants tied). Brainstorm →
spec → plan → subagent-driven (2 tasks) → Opus whole-branch review (Ready to merge=YES, 0 Critical/
0 Important). 4 commits `73ade79..ff399b5` on `main` (NOT pushed — no remote)._

**What shipped.** A pure helper `_shape_for_prompt(base, system_prompt)` in
`src/orionfold/providers/mock.py`. Both mocks route their base output through it. A brevity *cue* in
the system prompt truncates the output (dropping trailing content / keypoints), like a model that
obeyed the instruction. Concrete keyless demo on the bundled dataset: **Baseline avg_score=1.000
(recommended) vs Concise avg_score=0.555** — a genuine decision, not a tie.

**Key invariants (do NOT regress):**
- **Verbatim-by-identity:** `_shape_for_prompt` returns the SAME `base` string object (no
  split/join) on the `system_prompt is None` path AND the cue-less `budget>=1.0` path. This is what
  keeps **model-compare byte-identical** — the "100% (5/5)" contract, sample receipts, and sample
  `config_hash 467ddd96c9a5` are untouched (NO sample regeneration needed). A unit test asserts
  `is base` (identity, not equality) — keep it.
- **Deterministic:** pure function of `(base, system_prompt)` — no hashing, no random, no state.
  (The product's thesis is *repeatable* proof; a nondeterministic mock would be a real defect.)
- **mock_bad failure path:** still raises its simulated failure on `_stable_int(input_text) % 5 == 0`
  **before** shaping → failure count invariant to the prompt ("Failure cases (5)" / "simulated
  provider failure" intact).
- **Cue tiers (exact):** strong `b=0.4` = {`as few words as possible`, `fewest`, `terse`,
  `one sentence`, `tl;dr`}; mild `b=0.6` = {`concise`, `brief`, `short`, `minimal`}; no cue →
  `b=1.0`; strongest (smallest b) wins when both present. Truncate to first
  `max(1, ceil(b*word_count))` whitespace-split words.
- **Scope:** ONLY `mock.py` + `tests/unit/test_providers.py` + `tests/integration/test_proof_api.py`
  changed. No receipt schema change, no `RECEIPT_VERSION` bump (still **6**), no frontend change.
- **It's a deliberately small *simulation*** sensitive only to a finite brevity-cue vocabulary;
  providers stay labeled "Mock ·…". Real signal still comes from a real model.

**Verification at close (HEAD `ff399b5`):** `uv run pytest` 223 passed (1 pre-existing 3rd-party
StarletteDeprecationWarning) · `uv run ruff check src tests` clean · `pnpm --dir web test` 83/83
(22 files) · `pnpm --dir web build` clean · `bash scripts/build.sh && pnpm --dir web e2e` 6/6 ·
`config_hash 467ddd96c9a5` present (model-compare byte-identical).

> **NEXT SESSION — pick one (all non-blocking, none is a gate):**
> 1. **Catalog price/source accuracy pass** (roadmap) — a few catalog values UNVERIFIED; a measured
>    receipt cost always outranks a list price, so this is refinement, not a gate.
> 2. **Cross-product (models × prompts)** — compare N models × M prompts in one run; deliberately
>    deferred in #6. Only if a real need appears. Brainstorm FIRST.
> 3. **Set up a git remote + push** — none configured; ALL `main` commits are local.
> 4. **Parametrized cue test (tiny defer-Minor)** — add isolated tests for single-token strong cues
>    (`fewest`/`one sentence`/`tl;dr`). The final review verified all 9 cues directly; redundant with
>    the existing `any()`-scan coverage, so genuinely optional.
> Workflows/RAG remain post-v0. Creative/feature work → brainstorm FIRST.

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001 + ADR-0002 +
ADR-0003, and the latest worklogs: 2026-06-21-prompt-aware-mocks, 2026-06-21-prompt-variant-candidates,
2026-06-21-scoring-section-design-polish).

RECENT WORK (committed to main, not pushed — no git remote configured):
- (this session) PROMPT-AWARE MOCKS — SHIPPED, merge-ready. Keyless mock providers now deterministically
  vary output by candidate.system_prompt so the #6 prompt-compare demo produces a real winner with NO API
  key (was: all variants tied). Pure helper _shape_for_prompt(base, system_prompt) in
  src/orionfold/providers/mock.py; both mocks route base output through it; a brevity cue truncates output
  (drops trailing keypoints). Demo: Baseline 1.000 (recommended) vs Concise 0.555. Opus whole-branch
  review = Ready to merge YES, 0 Critical/0 Important. Spec/plan:
  docs/superpowers/{specs,plans}/2026-06-21-prompt-aware-mocks*. Commits 73ade79..ff399b5 (4).
- (prior) #6 PROMPT-VARIANT CANDIDATES (Compare-by Models|Prompts; system_prompt is a Candidate field;
  RECEIPT_VERSION 6). SCORING-SECTION DESIGN POLISH. MEANING-AWARE SCORING. DECISION RECIPES (#5),
  MODEL PICKER (#4), CATALOG (#1).

>> START HERE — pick one non-blocking option (none is a gate):
   1. Catalog price/source accuracy pass (roadmap refinement).
   2. Cross-product models×prompts (only if a real need appears; deferred in #6). Brainstorm FIRST.
   3. Set up a git remote + push (all main commits are local).
   4. Parametrized cue test for single-token strong cues (tiny optional defer-Minor).
   Workflows/RAG remain post-v0. Creative/feature work → brainstorm FIRST.

Do NOT regress (prompt-aware-mocks invariants): _shape_for_prompt returns the SAME base string object
(no split/join) on system_prompt-is-None AND cue-less (budget>=1.0) paths → model-compare byte-identical
(sample config_hash is 467ddd96c9a5; a unit test asserts `is base`); pure/deterministic (no hash/random/
state); mock_bad raises on _stable_int(input_text)%5==0 BEFORE shaping (failure invariant to prompt);
cue tiers exact (strong 0.4 = as few words as possible/fewest/terse/one sentence/tl;dr; mild 0.6 =
concise/brief/short/minimal; strongest wins); truncate to first max(1, ceil(b*words)) words; mocks are a
labeled SIMULATION, real signal needs a real model; NO receipt-schema change / NO RECEIPT_VERSION bump
(still 6) / NO frontend change.

Plus the #6 invariants: config_hash includes system_prompt ONLY when non-None; RECEIPT_VERSION 6
(prompt_variants additive/optional so old reports deserialize); variant id = {model_id}#{slug} (deduped),
# distinct from the : model split so engine routes on bare provider_id; both run endpoints go through
_resolve_candidates (422 on not-one-model/<2-variants/empty; UnknownCandidateError→400); model-compare
run request carries NO prompt_variants key (toggle defaults to "models"); prompt text is author
instructions, never a secret; frontend helpers are promptVariantsHelpers.ts (NOT promptVariants.ts);
Baseline starter prompt drift-locked to server TASK_SYSTEM_PROMPT by a test.

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
  `--run`). e2e: `pnpm --dir web e2e` (rebuild the embed first). The harness emits STALE TS "cannot find
  module" diagnostics mid-edit — trust `pnpm --dir web build` + the actual test/e2e runs.
- The Playwright e2e uses a fresh DB; a STALE local server/DB can cause a false failure — kill the port +
  delete /tmp/orionfold-e2e.db, rebuild the embed, re-run. The receipt preview iframe is CSP-sandboxed,
  so e2e asserts receipt content via the JSON receipt (page.request.get), not the iframe.
- create-dataset route field is `text` (not `content`): POST /api/datasets {name, format, text}.
- Mocks ignoring system_prompt is NO LONGER TRUE — they are now prompt-aware (this session). But a
  prompt with no brevity cue still returns base verbatim, so model-compare (system_prompt=None) is
  byte-identical and sample receipts need NO regeneration. Regenerate samples only after a receipt
  change: `uv run python scripts/gen_samples.py`.
Start in plan mode for anything substantial; brainstorm creative/feature work first. Verify with
uv run pytest, uv run ruff check src tests, pnpm --dir web test, the Playwright e2e (rebuild embed first),
and a real browser/server check on a free port. Open review-bound markdown in Obsidian one at a time.
Append a docs/worklog entry and overwrite HANDOFF.md.
```

## Where to look (durable context)

- `docs/worklog/2026-06-21-prompt-aware-mocks.md` — this session's evidence (latest).
- `docs/superpowers/specs/2026-06-21-prompt-aware-mocks-design.md` ·
  `docs/superpowers/plans/2026-06-21-prompt-aware-mocks.md` — approved design + 2-task plan.
- `docs/worklog/2026-06-21-prompt-variant-candidates.md` — the #6 feature this builds on.
- `docs/ux/product-design-system.md` — the three-pane target + Theming subsection.
- `docs/adr/0001-…-architecture.md` · `0002-provider-integration-and-credentials.md` ·
  `0003-streaming-run-progress.md` — Accepted.
- `docs/release-charter.md` — v0 scope, journey, acceptance criteria (Accepted; all met).
- `CHANGELOG.md` ([Unreleased] now notes prompt-aware mocks under the prompt-variant entry) ·
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
- Inspect a prompt-compare run: POST /api/runs with `{dataset_id, candidate_ids: ["<model>"],
  prompt_variants: [{name, system_prompt}, …]}`. On a mock model, a brevity cue in a variant's
  system_prompt now lowers its score (keyless differentiation).
- Env knobs: `OPENAI_API_KEY` `OPENROUTER_API_KEY` `GEMINI_API_KEY` `ANTHROPIC_API_KEY` (also
  settable in-app via POST /api/credentials → .env.local); `OLLAMA_HOST` `OPENAI_BASE_URL`
  `OPENROUTER_BASE_URL` `LMSTUDIO_BASE_URL`;
  `ORIONFOLD_{OLLAMA,OPENAI,OPENROUTER,GEMINI,ANTHROPIC,LMSTUDIO}_MODEL` (override catalog default);
  `ORIONFOLD_MAX_TOKENS` (2048) `ORIONFOLD_TIMEOUT_S` (120) `ORIONFOLD_ENV_FILE` `ORIONFOLD_DB`.
