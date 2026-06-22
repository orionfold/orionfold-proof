# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-21 · **BROWSER SMOKE E2E (Claude-in-Chrome) — last 3 releases PASS keyless;
REAL-PAID route surfaced 1 confirmed code bug + 2 issues to fix next session.** No code changed this
session (verification only). Prior shipped state below still stands: prompt-aware mocks merge-ready,
4 commits `73ada79..ff399b5` on `main` (NOT pushed — no remote)._

## ⚠️ ISSUES FOUND — fix next session (browser smoke + real-paid route)

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

> **NEXT SESSION — two phases: (A) fix known issues, then (B) comprehensive real-world browser smoke.**
>
> **PHASE A — fix the known issues (start here):**
> 1. **FIX Issue 1 (OpenAI `max_tokens` → `max_completion_tokens`)** — confirmed bug, blocks ALL OpenAI
>    runs. TDD, per-profile `token_param`, no paid calls to verify.
> 2. **Triage Issue 2 (Hosted judge defaults to Anthropic w/o key)** — default to a keyed judge, or
>    gate/hint missing-key judge options. Small frontend (+ maybe selection-endpoint) change.
> 3. **Consider Issue 3 (verbose raw provider errors)** — truncate/normalize. Low priority.
>
> **PHASE B — comprehensive REAL-WORLD end-to-end browser smoke** (Claude-in-Chrome, real providers;
> OpenAI billing topped up + new key in `.env.local`; Gemini + OpenRouter healthy; add an Anthropic key
> if you want it covered). Rebuild embed (`bash scripts/build.sh`), `orionfold up` on a PROVABLY-FREE
> port (sibling checkout holds 8787/8790/51xx), fresh throwaway DB. Drive each feature and capture
> evidence; note + fix any new issues. **Feature checklist (everything built so far):**
> - [ ] **Custom dataset import** — paste each format (JSONL · CSV · Markdown), Preview, save, verify examples render.
> - [ ] **Model-compare, real cross-provider** — OpenAI (now fixed) + Gemini + OpenRouter in one run; confirm all succeed, real cost/latency.
> - [ ] **Decision recipes (#5)** — each of the 4 recipes pre-fills candidates + question correctly.
> - [ ] **Model picker / catalog (#1, #4)** — tiers/cost-classes, `+ custom` model entry, local providers (Ollama/LM Studio if available — else note unavailable).
> - [ ] **All 4 scoring methods** on a real run — Auto · Keypoint · Similarity · LLM judge with a REAL judge model (and the Run-on/Optimize/Judge stepper).
> - [ ] **Prompt-variant compare (#6) on a REAL model** — Baseline vs a custom real-world prompt; real (not simulated) score variation; receipt v6 `prompt_variants`.
> - [ ] **Streaming progress (ADR-0003)** — live per-candidate/per-example bars.
> - [ ] **Leaderboard + recommendation + verdict** — ranking, recommended badge, verdict vocabulary incl. "No clear winner" / "Keep testing" / "Ship".
> - [ ] **Failure-case browser** — select a case, inspect input/expected/output in the inspector.
> - [ ] **Receipt export** — Markdown · HTML · JSON; verify content, "Scored by" + "Run cost" lines, prompt-variant section; **secret scan** (no key material).
> - [ ] **Candidates view + Receipts view** — past receipts list/open.
> - [ ] **Keyless regression guard** — model-compare still byte-identical (config_hash `467ddd96c9a5`); prompt-aware mocks Baseline>Concise.
>
> Then prior backlog (non-blocking): catalog price/source accuracy pass · cross-product models×prompts
> (brainstorm first) · git remote + push. Workflows/RAG remain post-v0. Creative/feature → brainstorm FIRST.

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

>> START HERE — two phases (see "⚠️ ISSUES FOUND" + the PHASE A/B plan in HANDOFF.md and
   docs/worklog/2026-06-21-browser-smoke-last-three-releases.md):
   PHASE A — fix known issues:
   1. FIX OpenAI provider bug: openai_compatible.py:56 sends max_tokens; GPT-5.x needs
      max_completion_tokens (HTTP 400 blocks ALL OpenAI runs). TDD, per-profile token_param, no paid
      calls to verify. OpenAI billing topped up (new key in .env.local).
   2. Triage: Hosted LLM-judge defaults to Claude Haiku · Anthropic and errors when ANTHROPIC_API_KEY
      is unset — default to a keyed judge or hint missing keys in the judge dropdown.
   3. Minor: raw provider error JSON shown verbatim in failure cases/receipt (no secret leak verified) —
      consider truncating.
   PHASE B — comprehensive REAL-WORLD end-to-end browser smoke (Claude-in-Chrome, real providers) of
   EVERY feature built so far: custom dataset import (JSONL/CSV/Markdown) · real cross-provider
   model-compare (OpenAI+Gemini+OpenRouter) · decision recipes · model picker/catalog/custom model ·
   all 4 scoring methods incl. a REAL LLM judge · prompt-variant compare on a REAL model · streaming
   progress · leaderboard/recommendation/verdict · failure-case browser · receipt export (MD/HTML/JSON)
   + secret scan · Candidates/Receipts views · keyless regression guard (config_hash 467ddd96c9a5).
   Rebuild embed first; PROVABLY-FREE port; fresh throwaway DB; note + fix any new issues.
   Then backlog: catalog accuracy pass · cross-product models×prompts (brainstorm first) · git remote +
   push. Workflows/RAG remain post-v0. Creative/feature work → brainstorm FIRST.

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
