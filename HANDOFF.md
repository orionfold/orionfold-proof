# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-20 · **Model catalog (decision-recipes sub-project #1) SHIPPED & merge-ready.**
A bundled `provider → model → capabilities` catalog — the data foundation the operator chose as the
strategic anchor for the decision-recipes thread (#5) + model-per-candidate (#4). Decomposed into a
sequenced plan: **#1 catalog → #2 model picker → #3 recipes**, inline `.env.local` key-entry as a
cross-cut. Built brainstorm → spec → plan → subagent-driven (3 TDD tasks, per-task spec+quality
reviews, Opus whole-branch review: Ready to merge YES). New `orionfold.catalog` package: `models.py`
(ModelPricing/CatalogModel/CatalogProvider/ModelCatalog; capability fields family/tier/privacy/
context_window/cost_class/pricing/latest/recommended; validator: default_model∈models + unique ids),
`catalog.json` (6 real providers, 13 curated models, cloud prices dated+sourced, local free/null,
mocks excluded), cached `load_catalog()` via importlib.resources. `default_model_for(pid)` is now the
single source of truth for per-provider defaults — registry calls it instead of 4 literal constants;
override precedence (ORIONFOLD_<P>_MODEL > catalog default) UNCHANGED, behavior-preserving (regression
+ drift-guard tests). `GET /api/catalog` read-only endpoint (no secrets, asserted). Catalog is
SELECTION scaffolding, NOT provenance: config_hash + RECEIPT_VERSION (3) untouched (empty diff proven).
`as_of` is a `datetime.date` (rejects malformed; JSON contract unchanged). pytest 114 · ruff clean.
Commits on `main` (NOT pushed — no remote): 459e8ca 0114b05 dcd96a0 9e048c4 beb7cb0 2fc9be2 e7e1e79
(+ spec 2484839, plan 8700395)._

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001 +
ADR-0002 + ADR-0003, and the latest worklogs: 2026-06-20-model-catalog, 2026-06-20-light-theme,
and 2026-06-20-ui-feature-review).

RECENT WORK (committed to main, not pushed — no git remote configured):
- (this session) MODEL CATALOG (#1 of the decision-recipes thread). Full-stack data foundation,
  3 TDD tasks, merge-ready. New orionfold.catalog package (src/orionfold/catalog/{models.py,
  __init__.py,catalog.json}): ModelCatalog→CatalogProvider→CatalogModel→ModelPricing; @cache
  load_catalog() via importlib.resources (wheel-safe like datasets); default_model_for(pid) is the
  single source of truth for per-provider defaults. registry.py rewired to default_model_for()
  (deleted _OPENAI/_OPENROUTER/_LMSTUDIO_DEFAULT; provider-module DEFAULT_MODEL constants kept +
  drift-guarded; precedence ORIONFOLD_<P>_MODEL > catalog default preserved). routes.py:
  GET /api/catalog returns ModelCatalog (read-only, no secrets). as_of is datetime.date.
  config_hash + RECEIPT_VERSION (3) UNTOUCHED — catalog is selection metadata, never provenance.
- (prior today) LIGHT THEME + SWITCHER (#1 of the UI review). DATASET IMPORT (#9), in-app receipt
  preview (#8), sticky rail footer (#2), Task-name sync, streamed run progress (SSE). v0 is
  feature-complete against the charter.

THE DECISION-RECIPES THREAD (operator's strategic bet; decomposed, sequenced). Done: #1 catalog.
REMAINING, in build order:
- #4 MODEL-PER-CANDIDATE PICKER (next natural build on the catalog) — a per-provider
  "recommended models" dropdown sourced from GET /api/catalog (latest/recommended marked) + a
  free-text "custom model" escape hatch; candidates carry a chosen model into the run. The run path
  must accept a custom model for an available provider (model becomes part of candidate identity →
  feeds config_hash, which already handles it). NEEDS ITS OWN SPEC/PLAN.
- #5 DECISION RECIPES — named presets that compose a coherent candidate panel (using #4) + seed the
  decision question (+ optional dataset/rubric). Operator chose: unavailable providers SHOW greyed
  + offer INLINE KEY ENTRY (writes to .env.local) — that cross-cut needs its own security review
  (use security-secrets-review). Recipes are best a bundled catalog-like JSON served by an endpoint
  (resolve availability server-side), pre-fill not lock. BRAINSTORM before plan/code.
- OPERATOR PRICE/SOURCE VERIFICATION PASS for catalog.json (deferred review finding I2): verify each
  input/output price against the source URL; OpenRouter `source` should be per-model anchors, not the
  models list page. Bump each pricing as_of when a value changes. Optional: a lint/test that flags a
  non-per-model OpenRouter source so "verify at implementation" doesn't rot.
- DEFERRED (do when a consumer needs it): re-export Tier/CostClass from orionfold.catalog.__init__.

Operator's call which slice; #4 is the natural next build, #5 needs a brainstorm first.

Also pending whenever wanted: set up a git remote + PUSH (none configured; ALL main commits — this
session + the whole backlog — are local only).

Do NOT regress: keyless mock default; Proof Run is the DEFAULT view; the 3-format receipt; both run
endpoints (batch + stream); dataset routes; Task-name sync; sticky rail footer; the THEME system;
the MODEL CATALOG (catalog is selection-only, NEVER provenance — config_hash/RECEIPT_VERSION=3 stay
untouched; default_model_for is the single source of truth; ORIONFOLD_<P>_MODEL override precedence;
the drift-guard ties provider-module DEFAULT_MODEL constants to the catalog; /api/catalog leaks no
secrets; mocks are excluded from the catalog). Test-contract strings (heading "Orionfold Proof",
"Connected", button /Run proof/, regions Leaderboard / Failure cases / Proof Receipt export,
"Export Markdown|HTML|JSON", "100% (5/5)", "Failure cases (5)", "simulated provider failure").
Tailwind v4: CSS vars use the PARENTHESIS shorthand bg-(--color-x), never bg-[--color-x].

NOTES (non-blocking):
- A sibling orionfold-proof-codex checkout runs its own servers; leave its processes alone and bind a
  PROVABLY-FREE port (assert the listener PID is yours). uvicorn does NOT hot-reload backend code:
  restart `orionfold up` after backend changes. The embedded cockpit is served from
  src/orionfold/server/static (gitignored; rebuilt by `bash scripts/build.sh` — REBUILD before any
  e2e or browser check). catalog.json ships in the wheel automatically (under packages=src/orionfold).
- The harness emits STALE TS "cannot find module / @playwright/test" diagnostics mid-edit — false
  alarms; trust pnpm test + build + the actual e2e run as truth.
- create-dataset route field is `text` (not `content`): POST /api/datasets {name, format, text}.
- Button copy is "Run proof"/"Rerun proof" (lowercase p) for the test contract.
Start in plan mode for anything substantial; brainstorm creative/feature work first. Verify with
uv run pytest, uv run ruff check, pnpm --dir web test, the Playwright e2e (rebuild embed first), and
a real browser check on a free port. Open review-bound markdown in Obsidian one at a time. Append a
docs/worklog entry and overwrite HANDOFF.md.
```

## Where to look (durable context)

- `docs/worklog/2026-06-20-model-catalog.md` — this session's catalog evidence (latest).
- `docs/superpowers/specs/2026-06-20-model-catalog-design.md` · `…/plans/2026-06-20-model-catalog.md`
  — design + 3-task plan (decomposition rationale for the whole decision-recipes thread lives here).
- `docs/worklog/2026-06-20-ui-feature-review.md` — the 10-finding operator review + the §Synthesis
  "decision recipes" big idea (#5+#7+#4).
- `docs/worklog/2026-06-20-light-theme.md` — prior session (theme system).
- `docs/ux/product-design-system.md` — the three-pane target + Theming subsection.
- `docs/adr/0001-…-architecture.md` · `0002-provider-integration-and-credentials.md` ·
  `0003-streaming-run-progress.md` — Accepted.
- `docs/release-charter.md` — v0 scope, journey, acceptance criteria (Accepted; all met).
- `CHANGELOG.md` ([Unreleased] now covers the model catalog too) · `docs/demo-script.md`.
- `.claude/rules/{providers,receipts,storage}.md` — enforced constraints.
- `CLAUDE.md` — operating guide and release gates.

## Ship-candidate quick reference

- Build wheel: `bash scripts/build.sh` → `dist/orionfold_proof-0.1.0-py3-none-any.whl`
  (cockpit + dataset embedded, RECEIPT_VERSION=3, catalog.json bundled). dist/ and
  src/orionfold/server/static are gitignored.
- Clean-install check: `uv venv /tmp/x && uv pip install --python /tmp/x/bin/python dist/*.whl`
  then `/tmp/x/bin/orionfold up --port <free>` — bind a PROVABLY-FREE port; confirm the listener
  PID is yours (a stale prior-session server can shadow a port and serve old code).
- Dev: `uv run orionfold dev` + `pnpm --dir web dev`. Tests: `uv run pytest` · `uv run ruff check
  src tests` · `pnpm --dir web test` · `pnpm --dir web e2e` (rebuild embed first). Frontend build:
  `pnpm --dir web build`.
- Regenerate sample receipts after any receipt change: `uv run python scripts/gen_samples.py`.
- Inspect the catalog live: `curl -s localhost:<port>/api/catalog | python -m json.tool | head`.
- Env knobs: `OPENAI_API_KEY` `OPENROUTER_API_KEY` `GEMINI_API_KEY` `ANTHROPIC_API_KEY`;
  `OLLAMA_HOST` `OPENAI_BASE_URL` `OPENROUTER_BASE_URL` `LMSTUDIO_BASE_URL`;
  `ORIONFOLD_{OLLAMA,OPENAI,OPENROUTER,GEMINI,ANTHROPIC,LMSTUDIO}_MODEL` (override catalog default);
  `ORIONFOLD_MAX_TOKENS` (2048) `ORIONFOLD_TIMEOUT_S` (120) `ORIONFOLD_ENV_FILE` `ORIONFOLD_DB`.
