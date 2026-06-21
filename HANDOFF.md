# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-20 · **Decision recipes (#5 of the decision-recipes thread) SHIPPED &
merge-ready.** Named comparison presets that turn "pick models" into "pick the decision you're
making": a recipe row above the Proof setup pre-fills the candidate panel + decision question from
**semantic** selectors (family/tier/privacy/provider) resolved server-side against the live catalog
∩ availability. Shipped together with operator-mandated **inline `.env.local` key entry** (greyed
cloud providers + a recipe's "needs a key" banner) — its own security review was part of the slice.
Built brainstorm → spec → plan → subagent-driven (11 TDD tasks, per-task reviews, Opus whole-branch
review: Ready to merge YES; 0 Critical/0 Important). New `recipes/` package (schema + `recipes.json`
+ resolver), `CLOUD_KEY_NAMES` whitelist, atomic `0o600` `config/env_file.py` writer, `GET
/api/recipes` (no secrets) + `POST /api/credentials` (whitelist; key never echoed), `RecipeRow` +
nested-form-safe `KeyEntry` + picker/cockpit wiring. A security-review fix (`1289cd4`) closed a
FastAPI-422 key-echo vector with a global `input`-stripping handler + regression test. config_hash +
RECEIPT_VERSION (3) UNTOUCHED (whole-branch review verified zero diff on engine/export/domain).
pytest 146 · vitest 44 · ruff clean · build clean · e2e 4/4 · live-server verified (key-entry flow
unlocks a recipe with no restart; key in neither response nor log). Commits on `main` (NOT pushed —
no remote): a6ebaaf 397c0c3 cfaa23d ad3d55c 6f5484d d95f87d f58f8d6 692e70a 79a532c d740113 7bfcccd
1289cd4 (+ spec b… see git log, plan)._
>
> **NEXT SESSION: three findings from the live operator review (2026-06-20) take priority over #6.**
> (1) **Leaderboard recommendation bug** — `leaderboard.py:48-50` recommends an ERRORED candidate
> because a 0/5 error reports 0ms/$0.00 and wins the tiebreak; verified twice live (it crowned a
> model that returned HTTP 404). Fix the sort `(-pass_rate, -avg_score, latency, cost)` + only mark
> `recommended` when `pass_count>0` + a "no clear winner" UI/receipt state. Its own slice (touches
> the receipt output → `receipt-quality-review`). (2) **Remove `claude-fable-5` from catalog.json**
> (or tag unavailable) — it errors (not available) and the cost-vs-quality "Frontier" arm resolves to
> it; removing it makes Frontier resolve to `claude-opus-4-8`. (3) **Similarity rubric too crude** —
> @0.8 fails a correct Markdown-table summary (scored 0.12) because it's format-sensitive; points to
> an LLM-as-judge/semantic rubric (charter "optional, later"). THEN #6 prompt-variant candidates.
> Full creative/feature work → brainstorm → spec → plan → subagent-driven, same loop._

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001 +
ADR-0002 + ADR-0003, and the latest worklogs: 2026-06-20-decision-recipes,
2026-06-20-model-per-candidate-picker, 2026-06-20-ui-feature-review).

RECENT WORK (committed to main, not pushed — no git remote configured):
- (this session) DECISION RECIPES (#5), merge-ready. New orionfold.recipes package:
  models.py (Selector{label,family?,tier?,privacy?,provider?,pick} / Recipe / RecipeBook),
  recipes.json (4 recipes), __init__ load_recipes() (@cache, mirrors catalog/). resolution.py
  resolve_recipes() resolves each selector against load_catalog() ∩ set(_build()) availability →
  ResolvedSelector / UnmetSelector / ResolvedRecipe{candidate_ids, resolved, unmet} / RecipesPanel;
  pick = recommended|cheapest|latest; UNMET ALWAYS = a cloud provider needing a key (locals always
  available). CLOUD_KEY_NAMES whitelist in config/keys.py (provider_id→ENV NAME; the single source
  for the credential whitelist). config/env_file.py set_key_in_env_local: atomic os.replace, 0o600
  via os.open up front, preserves other lines/export prefix, returns Path only (value never
  logged/echoed). Routes: GET /api/recipes (read-only, no secrets), POST /api/credentials
  ({provider_id,key}→whitelist 400 / empty 422 / {provider_id,available}, key NEVER echoed — a
  GLOBAL RequestValidationError handler in server/app.py strips `input` from 422s so the framework
  can't echo a posted key). Frontend: RecipeRow.tsx (cards pre-fill candidates + decision question;
  active highlight; unmet banner dedup'd per provider with a per-row label + KeyEntry), KeyEntry.tsx
  (shared, nested-form-safe: div/type=button/Enter preventDefault+stopPropagation; key in local
  state only, type=password, cleared on success; onSuccess invalidates ["selection"]+["recipes"]),
  CandidatePicker greyed CLOUD groups render KeyEntry (locals get "start the local server").
  ProofCockpit: recipes query + activeRecipeId; onSelectRecipe seeds candidates + decision_question
  ONLY (not task name/dataset/rubric); hand-editing → "Custom". e2e asserts recipe row + pre-fill.
- (prior) MODEL-PER-CANDIDATE PICKER (#4): build_candidates() composite provider:model ids; GET
  /api/selection; CandidatePicker. MODEL CATALOG (#1): orionfold.catalog, default_model_for, GET
  /api/catalog. LIGHT THEME. DATASET IMPORT (#9). Receipt preview (#8).

THE DECISION-RECIPES THREAD (operator's strategic bet). Done: #1 catalog, #4 picker, #5 recipes.

>> START HERE — THREE LIVE-REVIEW FINDINGS (2026-06-20) BEFORE #6 (details in
   docs/worklog/2026-06-20-decision-recipes.md §Findings):
   (1) LEADERBOARD RECOMMENDATION BUG (highest priority) — src/orionfold/proof/leaderboard.py:48-50
       sorts (-pass_rate, avg_latency_ms, total_cost) and unconditionally marks entries[0]
       recommended. An errored candidate reports 0ms/$0.00 so it WINS the 0%-pass tiebreak and gets
       "RECOMMENDED" — verified twice live (crowned claude-fable-5 then ollama:llama3.2, the latter a
       404 "model not found"). Fix: sort (-pass_rate, -avg_score, avg_latency_ms, total_cost); mark
       recommended ONLY if entries[0].pass_count>0; add a "no candidate passed" state to
       DecisionSummary (ProofCockpit.tsx) + receipts/export.py. ResultRow already carries the error,
       so errored rows can rank last. Own slice; regenerate sample receipts; receipt-quality-review.
   (2) REMOVE claude-fable-5 FROM src/orionfold/catalog/catalog.json (or tag unavailable) — it errors
       (not available on the account); the cost-vs-quality "Frontier" selector resolves to it.
       Removing → Frontier resolves to claude-opus-4-8. Keep default_model_for("anthropic") +
       test_catalog.py pinned defaults in sync (drift-guard). Small; pairs with the price/source pass.
   (3) SIMILARITY RUBRIC TOO CRUDE — default similarity@0.8 fails a correct Markdown-table summary
       (Haiku scored 0.12) because it matches phrasing/format, not meaning. Points to an
       LLM-as-judge/semantic rubric (charter "optional, later"); interim = lower threshold / document
       format-sensitivity. Own brainstorm.
   THEN #6 PROMPT-VARIANT CANDIDATES (same model, different system prompt — next candidate axis;
   composes with recipes/picker), and the CATALOG PRICE/SOURCE pass. Workflows/RAG remain post-v0.
   BRAINSTORM before plan/code.

OTHER (non-blocking — do NOT gate #6 on these):
- CATALOG PRICE/SOURCE accuracy is a ROADMAP item (a few values approximate/UNVERIFIED: OpenAI
  cached-input/long-context surcharges; Gemini gemini-3.x preview tier; OpenRouter :free slug). A
  measured receipt cost always outranks a catalog list price downstream, so it never blocks the
  proof loop. Bump pricing as_of when a value is updated.
- COSMETIC POLISH (whole-branch-review Minors): recipes/resolution.py _pick/_resolve_one lack
  return annotations; two redundant quoted annotations under `from __future__`; routes.py new
  imports not strict-isort-ordered (ruff isort not enforced). CLOUD_KEY_NAMES is duplicated
  (keys.py + a TS literal in CandidatePicker.tsx) — could surface key_name on SelectionGroup to
  delete the copy.
- Set up a git remote + PUSH (none configured; ALL main commits are local only).

Do NOT regress: keyless mock default (mocks pre-selected, opt-in recipes); mocks stay bare-id +
model=None (composite ids ONLY for real model-bearing providers — recipes can't select a mock since
mocks aren't in the catalog); Proof Run is the DEFAULT view; the 3-format receipt; both run
endpoints route through build_candidates; /api/selection + /api/catalog + /api/recipes leak NO
secrets; /api/credentials NEVER echoes/logs a key and writes ONLY whitelisted cloud providers to a
0o600 .env.local; the global 422 input-stripping handler stays; recipes/key-entry are SELECTION
metadata, NEVER provenance (config_hash/RECEIPT_VERSION=3 untouched; default_model_for single source
of truth; ORIONFOLD_<P>_MODEL override precedence; catalog drift-guard). Test-contract strings
(heading "Orionfold Proof", "Connected", button /Run proof/, regions Leaderboard / Failure cases /
Proof Receipt export, "Export Markdown|HTML|JSON", "100% (5/5)", "Failure cases (5)", "simulated
provider failure"). Tailwind v4: CSS vars use the PARENTHESIS shorthand bg-(--color-x), never
bg-[--color-x].

NOTES (non-blocking):
- A sibling orionfold-proof-codex checkout runs its own servers; leave its processes alone and bind a
  PROVABLY-FREE port (assert the listener PID is yours). uvicorn does NOT hot-reload backend code OR
  the @cache load_catalog()/load_recipes() data — RESTART `orionfold up` after backend/catalog/recipe
  changes. BUT note: .env.local KEY resolution is NOT cached (resolve_key reads it fresh each call),
  so inline key entry flips availability live with no restart — verified. The embedded cockpit is
  served from src/orionfold/server/static (gitignored; rebuilt by `bash scripts/build.sh` — REBUILD
  before any e2e or browser check). catalog.json AND recipes.json ship in the wheel automatically
  (checked-in files under the package, like catalog.json).
- The harness emits STALE TS "cannot find module / @playwright/test" diagnostics mid-edit — false
  alarms; trust pnpm test + build + the actual e2e run as truth.
- create-dataset route field is `text` (not `content`): POST /api/datasets {name, format, text}.
- Button copy is "Run proof"/"Rerun proof" (lowercase p) for the test contract.
- Recipe pre-fill seeds candidates + decision_question ONLY (operator decision). Recipe selectors
  are SEMANTIC (resolve to whatever's available); unavailable cloud arms show greyed + inline key
  entry. Recipe row stays visible; hand-edit → "Custom".
- POST /api/credentials body: {provider_id, key}; the frontend client is web/src/lib/api.ts
  setProviderKey(providerId, key).
Start in plan mode for anything substantial; brainstorm creative/feature work first. Verify with
uv run pytest, uv run ruff check, pnpm --dir web test, the Playwright e2e (rebuild embed first), and
a real browser/server check on a free port (RESTART the server after catalog/backend edits; key
entry needs no restart). Open review-bound markdown in Obsidian one at a time. Append a docs/worklog
entry and overwrite HANDOFF.md.
```

## Where to look (durable context)

- `docs/worklog/2026-06-20-decision-recipes.md` — this session's evidence (latest).
- `docs/superpowers/specs/2026-06-20-decision-recipes-design.md` ·
  `docs/superpowers/plans/2026-06-20-decision-recipes.md` — design + 11-task plan.
- `docs/worklog/2026-06-20-model-per-candidate-picker.md` — the picker (#4) recipes compose on.
- `docs/worklog/2026-06-20-ui-feature-review.md` — the 10-finding review + §Synthesis
  "decision recipes" big idea (#5+#7+#4).
- `docs/ux/product-design-system.md` — the three-pane target + Theming subsection.
- `docs/adr/0001-…-architecture.md` · `0002-provider-integration-and-credentials.md` ·
  `0003-streaming-run-progress.md` — Accepted.
- `docs/release-charter.md` — v0 scope, journey, acceptance criteria (Accepted; all met).
- `CHANGELOG.md` ([Unreleased] now covers recipes + inline key entry) · `docs/demo-script.md`.
- `.claude/rules/{providers,receipts,storage}.md` — enforced constraints.
- `CLAUDE.md` — operating guide and release gates.

## Ship-candidate quick reference

- Build wheel: `bash scripts/build.sh` → `dist/orionfold_proof-0.1.0-py3-none-any.whl`
  (cockpit + dataset embedded, RECEIPT_VERSION=3, catalog.json + recipes.json bundled). dist/ and
  src/orionfold/server/static are gitignored.
- Clean-install check: `uv venv /tmp/x && uv pip install --python /tmp/x/bin/python dist/*.whl`
  then `/tmp/x/bin/orionfold up --port <free>` — bind a PROVABLY-FREE port; confirm the listener
  PID is yours.
- Dev: `uv run orionfold dev` + `pnpm --dir web dev`. Tests: `uv run pytest` · `uv run ruff check
  src tests` · `pnpm --dir web test` · `pnpm --dir web e2e` (rebuild embed first). Frontend build:
  `pnpm --dir web build`.
- Regenerate sample receipts after any receipt change: `uv run python scripts/gen_samples.py`
  (NOT needed this session — receipts unchanged).
- Inspect recipes live: `curl -s localhost:<port>/api/recipes | python -m json.tool`. Picker panel:
  `curl -s localhost:<port>/api/selection | python -m json.tool`.
- Env knobs: `OPENAI_API_KEY` `OPENROUTER_API_KEY` `GEMINI_API_KEY` `ANTHROPIC_API_KEY` (now also
  settable in-app via POST /api/credentials → .env.local); `OLLAMA_HOST` `OPENAI_BASE_URL`
  `OPENROUTER_BASE_URL` `LMSTUDIO_BASE_URL`;
  `ORIONFOLD_{OLLAMA,OPENAI,OPENROUTER,GEMINI,ANTHROPIC,LMSTUDIO}_MODEL` (override catalog default);
  `ORIONFOLD_MAX_TOKENS` (2048) `ORIONFOLD_TIMEOUT_S` (120) `ORIONFOLD_ENV_FILE` `ORIONFOLD_DB`.
