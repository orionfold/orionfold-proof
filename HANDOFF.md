# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-21 · **PHASES A + B BOTH DONE.** A: OpenAI `max_tokens`→`max_completion_tokens`
bug FIXED (commit `9ffbb90` on `main`, NOT pushed — no remote). B: comprehensive REAL-WORLD paid browser
smoke PASSED — every built feature verified with live providers; OpenAI fix confirmed end-to-end with
real paid calls. **One non-code env gotcha for the operator (stale shell OPENAI key); see below.**_

## ✅ PHASE A — COMPLETE (commit `9ffbb90`)

> Evidence: `docs/worklog/2026-06-21-phase-a-openai-token-param-fix.md`. Verified keyless:
> `uv run pytest` 226 · `ruff` clean · `pnpm --dir web test` 84 · `pnpm --dir web e2e` 6/6.

1. **🐞 Issue 1 — FIXED.** OpenAI GPT-5.x rejects `max_tokens` (HTTP 400 → use
   `max_completion_tokens`); blocked ALL OpenAI runs + the OpenAI hosted judge. Added per-profile
   `token_param` to `OpenAICompatibleProvider`; OpenAI profile → `max_completion_tokens`, OpenRouter +
   LM Studio keep `max_tokens`. Judge inherits via `get_provider`. +3 backend tests.
2. **Issue 2 — already handled; no change needed.** The Hosted judge default never lands on an
   unkeyed provider — `filterJudgeModels` gates unavailable providers to hint-rows. Issue 2's symptom
   was Issue 1 firing on the auto-picked OpenAI judge (mis-attributed to Anthropic). +1 frontend guard.
3. **Issue 3 — deferred.** Raw error bodies already capped at 500 chars + redacted; no secret leak;
   verbatim body is useful for debugging. Left as-is.

## ✅ PHASE B — COMPLETE (real-world paid browser smoke, verification-only, no code change)

> Evidence: `docs/worklog/2026-06-21-phase-b-realworld-browser-smoke.md`. Ran a real server on free
> port 8811 (fresh throwaway DB, freshly rebuilt embed) with live OpenAI/Gemini/OpenRouter/Anthropic
> keys via Claude-in-Chrome + a few API runs for precise evidence. Server + DB + temp files cleaned up.

- **OpenAI fix confirmed end-to-end with real money:** cross-provider model-compare → 0 errors, OpenAI
  Recommended; OpenAI hosted judge → 0 errors, judge cost separated. The old `max_tokens` 400 is gone.
- **Every checklist item passed:** custom dataset import (CSV in UI: paste→preview→freeze→listed) ·
  real cross-provider compare · decision recipe pre-fill (#5) · model picker/catalog/local providers
  (#1,#4) · all 4 scoring cards incl. a **live REAL Anthropic Haiku judge** · prompt-variant compare on
  a **REAL** model (#6: real score variation, receipt v6 `prompt_variants`) · streaming progress
  (ADR-0003) · leaderboard/recommendation/verdict · failure-case browser (chips + inspector) · receipt
  export MD/HTML/JSON with **secret scan CLEAN** · Candidates + Receipts views · keyless regression
  guard (`config_hash 467ddd96c9a5` reproduced; prompt-aware mocks Baseline 1.000 > Concise 0.483).

## ⚠️ OPERATOR ACTION (env, NOT code) — stale shell `OPENAI_API_KEY` shadows `.env.local`

Key precedence is **system env first, then `.env.local`** (intentional 12-factor design in
`config/keys.py`). A **stale** exported `OPENAI_API_KEY` (suffix `_0MA`) shadowed the good topped-up
key in `.env.local` (suffix `qVYA`) → a misleading `HTTP 401 Incorrect API key` on every OpenAI call
until the server was relaunched with `env -u OPENAI_API_KEY`. **Fix: clear/refresh the stale
`OPENAI_API_KEY` in your shell profile** (or unset it and rely on `.env.local`). Optional product
idea (defer, low priority): surface the *source* of a resolved key, or let the in-app credential flow
override a shell key. Not a bug — precedence is by design — but a real operational trap (no UI signal).

## ⚠️ ISSUES (original notes — all resolved/triaged above; kept for context)

> Ran the last 3 feature releases through Claude-in-Chrome. Keyless smoke = all PASS (see "Positives"
> below). Then ran the **real-paid route** (user keys in env: OPENAI/GEMINI/OPENROUTER; ANTHROPIC
> unset) — which is what surfaced these. Evidence in
> `docs/worklog/2026-06-21-browser-smoke-last-three-releases.md`.

1. **🐞 BUG (code) — OpenAI provider sends `max_tokens`; GPT-5.x rejects it.**
   `src/orionfold/providers/openai_compatible.py:56` sends `"max_tokens"`. Every OpenAI candidate (and
   the OpenAI *Hosted judge*) errors with: `HTTP 400: "Unsupported parameter: 'max_tokens' is not
   supported with this model. Use 'max_completion_tokens' instead."` Affects ONLY the OpenAI profile —
   OpenRouter + LM Studio share the class but accept `max_tokens` (verified: OpenRouter Llama 3.1 8B ran
   fine). **Fix (TDD, NO paid calls needed):** add `token_param: str = "max_tokens"` to
   `OpenAICompatibleProvider`; set it to `"max_completion_tokens"` for the OpenAI profile in the provider
   factory (find where the OpenAI profile is constructed — grep the factory/registry); payload becomes
   `{self.token_param: max_output_tokens()}`. Unit test: OpenAI payload uses `max_completion_tokens`,
   OpenRouter/LM Studio keep `max_tokens`. ⚠️ User TOPPED UP OpenAI billing (new key in `.env.local`),
   so the old `429 insufficient_quota` is resolved — but **this 400 bug still blocks OpenAI until fixed.**

2. **UX gap — Hosted LLM-judge defaults to Claude Haiku · Anthropic, which errors when no Anthropic key.**
   With scoring=LLM judge + Run on=Hosted, the judge dropdown defaults to "Claude Haiku 4.5 · Anthropic".
   With `ANTHROPIC_API_KEY` unset the whole judge step errors. The candidate picker gates paid models, but
   the judge dropdown does NOT signal missing keys. Consider defaulting the judge to a keyed/available
   provider, or surfacing a "no key" hint on judge options. Confirm intended behavior (not a hard bug).

3. **Minor — raw provider error JSON rendered verbatim in failure cases + receipt.**
   The full provider error body (e.g. OpenAI 400/429 JSON) shows in the UI failure browser and is stored
   in the receipt. **No secret leak** (scanned receipts against the actual env key VALUES → zero key
   material; the `redacted at the boundary` contract holds). Verbose but arguably useful for debugging;
   consider truncating/normalizing. Low priority.

**Provider/billing status observed (no code, no further tests):** Gemini ✅ working · OpenRouter ✅ working ·
OpenAI was 429 (user topped up; new key in `.env.local`) + blocked by Issue 1 · Anthropic key UNSET (add a
key if you want it tested). Real cost/latency capture, judge-cost separation, errored-candidate exclusion
from recommendation, and honest verdicts ("Keep testing" @40% vs "Ship" @100%) all WORK under real providers.

**Positives verified (don't re-investigate):** all 3 recent releases smoke-passed keyless — scoring-section
polish (cards-in-row + LLM-judge single-row stepper), #6 prompt variants (toggle/editor/leaderboard/receipt
v6 `prompt_variants`), prompt-aware mocks (Baseline 1.00 RECOMMENDED vs Concise 0.48, a real keyless winner).
**Model-compare byte-identity intact** — config_hash `467ddd96c9a5` reproduced exactly with empty
`prompt_variants`. No secret leakage in any receipt.

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

> **NEXT SESSION — Phases A + B are DONE.** v0 is real-world-verified end to end. What remains is the
> non-blocking backlog plus one tiny operator chore:
>
> 0. **(Operator) Refresh the stale shell `OPENAI_API_KEY`** so the good `.env.local` key resolves
>    without `env -u OPENAI_API_KEY` (see the OPERATOR ACTION box above). One-time, no code.
> 1. **Catalog price/source accuracy pass** — verify list prices + context windows against current
>    provider docs (use `current-docs-check`). Non-blocking.
> 2. **Cross-product models×prompts** — compare N models × M prompts in one run. **Brainstorm FIRST**
>    (`superpowers:brainstorming`) — it's a new feature surface (#6 today is one-model × N-prompts).
> 3. **git remote + push** — no remote is configured; `main` holds `9ffbb90` (Phase A) unpushed.
> 4. Optional low-priority product ideas surfaced by Phase B: (a) surface the *source* of a resolved
>    key / let the in-app credential flow override a shell key; (b) Markdown-paste import live check;
>    (c) `+ custom` model entry live check. None are bugs.
>
> Workflows/RAG remain post-v0. Any creative/feature work → **brainstorm FIRST**.

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001 + ADR-0002 +
ADR-0003, and the latest worklogs: 2026-06-21-prompt-aware-mocks, 2026-06-21-prompt-variant-candidates,
2026-06-21-scoring-section-design-polish).

RECENT WORK (committed to main, not pushed — no git remote configured):
- (latest) PHASE A — OpenAI max_tokens FIX, SHIPPED (commit 9ffbb90). GPT-5.x rejects "max_tokens"
  (HTTP 400 → use "max_completion_tokens"); it blocked ALL OpenAI runs + the OpenAI hosted judge.
  Per-profile token_param on OpenAICompatibleProvider (OpenAI → max_completion_tokens; OpenRouter +
  LM Studio keep max_tokens); judge inherits via get_provider. +3 backend tests, +1 frontend judge-
  default guard. Issue 2 was already handled by judge gating; Issue 3 (verbose errors) deferred
  (already capped+redacted). Evidence: docs/worklog/2026-06-21-phase-a-openai-token-param-fix.md.
- (latest) PHASE B — comprehensive REAL-WORLD paid browser smoke, PASSED (verification-only, no code).
  OpenAI fix confirmed end-to-end with real money; every built feature verified with live providers;
  receipt secret scan CLEAN; keyless guard (config_hash 467ddd96c9a5) intact. Evidence:
  docs/worklog/2026-06-21-phase-b-realworld-browser-smoke.md. ONE operator chore surfaced: a stale
  shell OPENAI_API_KEY shadows the good .env.local key (precedence is system-env-first by design).
- (prior) PROMPT-AWARE MOCKS (ff399b5); #6 PROMPT-VARIANT CANDIDATES (RECEIPT_VERSION 6); SCORING-
  SECTION POLISH; MEANING-AWARE SCORING; DECISION RECIPES (#5); MODEL PICKER (#4); CATALOG (#1).

>> START HERE — Phases A + B are DONE; v0 is real-world-verified. Remaining work is non-blocking:
   0. (Operator) refresh the stale shell OPENAI_API_KEY so .env.local's good key resolves without
      `env -u OPENAI_API_KEY` (see OPERATOR ACTION box in HANDOFF.md). One-time, no code.
   1. Catalog price/source accuracy pass (use current-docs-check).
   2. Cross-product models×prompts — NEW feature surface; BRAINSTORM FIRST.
   3. git remote + push (main holds 9ffbb90 unpushed).
   Workflows/RAG remain post-v0. Any creative/feature work → brainstorm FIRST.

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
