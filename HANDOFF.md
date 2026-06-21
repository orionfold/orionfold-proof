# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-20 · **Model-per-candidate picker (#4 of the decision-recipes thread)
SHIPPED & merge-ready**, plus three operator follow-ups from a live review. The Proof Run now lets
you pick a specific model per provider and compare several models of the same provider in one run
(the cost/latency-vs-quality proof). Built brainstorm → spec → plan → subagent-driven (4 TDD tasks,
per-task reviews, Opus whole-branch review: Ready to merge YES). New `build_candidates()` widens run
validation to composite `provider:model` ids (keyless-safe, back-compat, first-colon split, mocks
stay bare-id); new read-only `GET /api/selection` (server-merged availability + catalog models +
mocks-first, no secrets); new `CandidatePicker` (provider-grouped chips, ★ latest, cost badge,
multi-select per provider, custom-model escape hatch, greyed unavailable). Follow-ups: (a) FIXED a
nested-`<form>` bug in the custom-model entry caught in the real browser; (b) CATALOG REFRESHED to
current mid-2026 models with dated sources (OpenAI GPT-5.x, Gemini 3.x, Claude incl. Fable 5, Llama
4 Scout) + FIXED Opus list price 15/75→5/25 and Sonnet/Opus context 200K→1M, dropped "(via
OpenRouter)" suffix; (c) PROVIDER LOGOS replace the availability bullet (simple-icons CC0, dimmed
when unavailable). config_hash + RECEIPT_VERSION (3) UNTOUCHED (final review verified empty diff on
engine/export/domain). pytest 129 · vitest 34 · ruff clean · build clean · e2e 3/3 · live-browser
verified. Commits on `main` (NOT pushed — no remote): 6479d66 6275102 8a5b96a 69b6e6e 0d9bd30
18346af 7991ae2 1568dde (+ spec 217aee4, plan bed2f58)._
>
> **NEXT SESSION: build #5 DECISION RECIPES.** Full creative/feature work → brainstorm → spec →
> plan → subagent-driven, same loop. Assume #4 has shipped (recipes compose model-bearing
> candidates using the picker). Operator decided 2026-06-20 to power through — catalog
> price/source accuracy is a roadmap refinement, NOT a gate on #5._

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001 +
ADR-0002 + ADR-0003, and the latest worklogs: 2026-06-20-model-per-candidate-picker,
2026-06-20-model-catalog, 2026-06-20-ui-feature-review).

RECENT WORK (committed to main, not pushed — no git remote configured):
- (this session) MODEL-PER-CANDIDATE PICKER (#4 of the decision-recipes thread), merge-ready.
  build_candidates() (registry.py) widens run validation to composite provider:model ids — bare ids
  still resolve (back-compat); composite resolves only for AVAILABLE, MODEL-BEARING providers +
  non-empty model (split on FIRST colon); mocks excluded from composite (stay bare-id + model=None);
  unavailable/unknown → UnknownCandidateError (400). Both run endpoints use it. GET /api/selection
  (providers/selection.py): server-merged panel = catalog models + live availability + mocks-first,
  read-only, no secrets, re-exports Tier/CostClass. CandidatePicker.tsx: provider-grouped chips
  (★ latest, cost badge), multi-select per provider, custom-model escape hatch, greyed unavailable;
  ProviderLogo.tsx swaps the availability bullet for the provider's brand logo. ProofCockpit/RunSetup
  read /api/selection; mocks pre-selected by default.
- (this session, follow-ups) Nested-<form> fix in CustomChip (Add was submitting RunSetup's outer
  form). Catalog refresh to current models + Opus price/context fix + dropped "(via OpenRouter)"
  suffix (gemini.py DEFAULT_MODEL + test_catalog.py defaults + pricing.py updated in lockstep).
  Provider logos.
- (prior) MODEL CATALOG (#1): orionfold.catalog package, default_model_for() single source of
  truth, GET /api/catalog. LIGHT THEME + switcher. DATASET IMPORT (#9). Receipt preview (#8).

THE DECISION-RECIPES THREAD (operator's strategic bet). Done: #1 catalog, #4 picker.

>> START HERE — #5 DECISION RECIPES. Named presets that compose a coherent candidate panel (USING
   #4's model-bearing composite candidates) + seed the decision question (+ optional dataset/rubric).
   Operator decisions locked: unavailable providers SHOW greyed + offer INLINE KEY ENTRY (writes to
   .env.local) — that cross-cut needs its OWN security review (use security-secrets-review; NEVER
   log/echo/commit keys). Recipes are best a bundled catalog-like JSON served by an endpoint (resolve
   availability server-side, like /api/selection already does), pre-fill not lock. Example recipes:
   "Cost vs quality for client summaries", "Local vs cloud (privacy)", "Cheapest model that still
   passes", "Same model, different providers (arbitrage)". BRAINSTORM before plan/code.

OTHER (non-blocking — operator decided 2026-06-20 to POWER THROUGH; do NOT gate #5 on these):
- CATALOG PRICE/SOURCE accuracy is a ROADMAP item, refined opportunistically as we find better
  sources — NOT a near-term verification gate. Current prices are researched list prices dated
  2026-06-20 with per-model source URLs; a few values are approximate/UNVERIFIED (OpenAI
  cached-input/long-context surcharges; Gemini gemini-3.1-pro-preview is a PREVIEW id — swap to
  gemini-3.5-flash if a GA-only frontier is ever wanted; OpenRouter :free slug). A measured receipt
  cost always outranks a catalog list price downstream, so this never blocks the proof loop. Bump
  pricing as_of when a value is updated.
- Set up a git remote + PUSH (none configured; ALL main commits — this session + the whole backlog —
  are local only).

Do NOT regress: keyless mock default; mocks stay bare-id + model=None (composite ids ONLY for real
model-bearing providers); Proof Run is the DEFAULT view; the 3-format receipt; both run endpoints
(batch + stream) route through build_candidates; /api/selection leaks no secrets; /api/catalog +
/api/candidates still served; dataset routes; Task-name sync; sticky rail footer; the THEME system;
the MODEL CATALOG + PICKER (SELECTION-only, NEVER provenance — config_hash/RECEIPT_VERSION=3 stay
untouched; default_model_for is the single source of truth; ORIONFOLD_<P>_MODEL override precedence;
the drift-guard ties provider-module DEFAULT_MODEL constants to the catalog). Test-contract strings
(heading "Orionfold Proof", "Connected", button /Run proof/, regions Leaderboard / Failure cases /
Proof Receipt export, "Export Markdown|HTML|JSON", "100% (5/5)", "Failure cases (5)", "simulated
provider failure"). Tailwind v4: CSS vars use the PARENTHESIS shorthand bg-(--color-x), never
bg-[--color-x].

NOTES (non-blocking):
- A sibling orionfold-proof-codex checkout runs its own servers; leave its processes alone and bind a
  PROVABLY-FREE port (assert the listener PID is yours). uvicorn does NOT hot-reload backend code OR
  the @cache load_catalog() data — RESTART `orionfold up` after backend/catalog changes (a stale
  server serves the OLD catalog even after build.sh). The embedded cockpit is served from
  src/orionfold/server/static (gitignored; rebuilt by `bash scripts/build.sh` — REBUILD before any
  e2e or browser check). catalog.json ships in the wheel automatically.
- The harness emits STALE TS "cannot find module / @playwright/test" diagnostics mid-edit — false
  alarms; trust pnpm test + build + the actual e2e run as truth.
- create-dataset route field is `text` (not `content`): POST /api/datasets {name, format, text}.
- Button copy is "Run proof"/"Rerun proof" (lowercase p) for the test contract.
- Run-request contract UNCHANGED: POST /api/runs(/stream) takes candidate_ids: string[] — composite
  provider:model ids (or bare mock ids) are just strings; the server resolves them via
  build_candidates. The frontend custom field builds `${provider_id}:${text.trim()}`.
Start in plan mode for anything substantial; brainstorm creative/feature work first. Verify with
uv run pytest, uv run ruff check, pnpm --dir web test, the Playwright e2e (rebuild embed first), and
a real browser check on a free port (RESTART the server after catalog/backend edits). Open
review-bound markdown in Obsidian one at a time. Append a docs/worklog entry and overwrite HANDOFF.md.
```

## Where to look (durable context)

- `docs/worklog/2026-06-20-model-per-candidate-picker.md` — this session's evidence (latest).
- `docs/superpowers/specs/2026-06-20-model-per-candidate-picker-design.md` ·
  `…/plans/2026-06-20-model-per-candidate-picker.md` — design + 4-task plan.
- `docs/worklog/2026-06-20-model-catalog.md` — the catalog foundation (#1).
- `docs/worklog/2026-06-20-ui-feature-review.md` — the 10-finding review + the §Synthesis
  "decision recipes" big idea (#5+#7+#4).
- `docs/ux/product-design-system.md` — the three-pane target + Theming subsection.
- `docs/adr/0001-…-architecture.md` · `0002-provider-integration-and-credentials.md` ·
  `0003-streaming-run-progress.md` — Accepted.
- `docs/release-charter.md` — v0 scope, journey, acceptance criteria (Accepted; all met).
- `CHANGELOG.md` ([Unreleased] now covers the picker + catalog refresh) · `docs/demo-script.md`.
- `.claude/rules/{providers,receipts,storage}.md` — enforced constraints.
- `CLAUDE.md` — operating guide and release gates.

## Ship-candidate quick reference

- Build wheel: `bash scripts/build.sh` → `dist/orionfold_proof-0.1.0-py3-none-any.whl`
  (cockpit + dataset embedded, RECEIPT_VERSION=3, catalog.json bundled). dist/ and
  src/orionfold/server/static are gitignored.
- Clean-install check: `uv venv /tmp/x && uv pip install --python /tmp/x/bin/python dist/*.whl`
  then `/tmp/x/bin/orionfold up --port <free>` — bind a PROVABLY-FREE port; confirm the listener
  PID is yours (a stale prior-session server can shadow a port and serve old code/catalog).
- Dev: `uv run orionfold dev` + `pnpm --dir web dev`. Tests: `uv run pytest` · `uv run ruff check
  src tests` · `pnpm --dir web test` · `pnpm --dir web e2e` (rebuild embed first). Frontend build:
  `pnpm --dir web build`.
- Regenerate sample receipts after any receipt change: `uv run python scripts/gen_samples.py`
  (NOT needed this session — receipts unchanged).
- Inspect the picker panel live: `curl -s localhost:<port>/api/selection | python -m json.tool`.
- Env knobs: `OPENAI_API_KEY` `OPENROUTER_API_KEY` `GEMINI_API_KEY` `ANTHROPIC_API_KEY`;
  `OLLAMA_HOST` `OPENAI_BASE_URL` `OPENROUTER_BASE_URL` `LMSTUDIO_BASE_URL`;
  `ORIONFOLD_{OLLAMA,OPENAI,OPENROUTER,GEMINI,ANTHROPIC,LMSTUDIO}_MODEL` (override catalog default);
  `ORIONFOLD_MAX_TOKENS` (2048) `ORIONFOLD_TIMEOUT_S` (120) `ORIONFOLD_ENV_FILE` `ORIONFOLD_DB`.
