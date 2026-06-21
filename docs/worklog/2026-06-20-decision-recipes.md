# 2026-06-20 — Decision recipes (#5 of the decision-recipes thread)

## Summary

Built **#5 decision recipes** — the strategic bet from the UI-feature-review §Synthesis. Named
comparison presets that turn "pick models" (a blank-canvas chore) into "pick the decision you're
making." Clicking a recipe **pre-fills** the candidate panel + decision question; the user can
still edit everything (hand-editing flips the active recipe to "Custom"). Shipped together with the
operator-mandated **inline `.env.local` key entry** so a greyed cloud provider can be unlocked in
place — its own security review was part of the slice.

The key design move: recipes declare **semantic** intent (family / tier / privacy / provider
filters + a pick strategy), not hardcoded `provider:model` ids. A server-side resolver maps each
selector against the live catalog ∩ availability — the same merge `/api/selection` already does —
so each recipe adapts to whatever the environment makes available. Because the registry always
offers the keyless local providers and only gates the four cloud providers on a key, an **unmet
selector always resolves to a cloud provider needing a key** — exactly what the key-entry flow
handles.

Built brainstorm → spec → plan → subagent-driven execution (11 tasks, fresh implementer + two-stage
review per task, an Opus whole-branch review). The four bundled recipes:
_Cost vs quality for client summaries_ · _Local vs cloud (privacy)_ · _Cheapest model that still
passes_ · _Same model, different providers (arbitrage)_.

What landed (13 commits on `main`, all local — no remote):

- **`recipes/` package** (`a6ebaaf`, `397c0c3`) — `Selector`/`Recipe`/`RecipeBook` schema +
  `recipes.json` (4 recipes) + `@cache`d `load_recipes()` (mirrors `catalog/`); `resolve_recipes()`
  resolves selectors against catalog ∩ `set(_build())` availability into `ResolvedSelector` /
  `UnmetSelector` / `ResolvedRecipe` / `RecipesPanel`. `pick` strategies: recommended / cheapest /
  latest. `candidate_ids` de-duplicated.
- **`CLOUD_KEY_NAMES`** whitelist in `config/keys.py` (`397c0c3`) — provider_id → env-var NAME,
  the single source of truth for the credential whitelist; mocks/locals absent.
- **`config/env_file.py`** (`cfaa23d`) — `set_key_in_env_local()`: atomic (temp + `os.replace`),
  `0o600` (via `os.open` up front — no umask window), preserves other lines / comments / `export`
  prefix, returns the Path only (value never logged/echoed/returned).
- **`GET /api/recipes` + `POST /api/credentials`** (`ad3d55c`) — recipes panel (read-only, no
  secrets); credential write (whitelist → 400 unknown; 422 empty/whitespace; returns
  `{provider_id, available}`; key never echoed).
- **Frontend** — api client + Zod schemas + `setProviderKey` (`6f5484d`); shared nested-form-safe
  `KeyEntry` (`d95f87d`); `RecipeRow` card row + unmet banner (`f58f8d6`, fix `692e70a`); `KeyEntry`
  on greyed cloud groups in the picker (`79a532c`); `ProofCockpit` wiring — recipes query,
  `activeRecipeId`, `onSelectRecipe` seeds candidates + decision question only, custom-on-edit
  (`d740113`).
- **e2e** (`7bfcccd`) — recipe row renders + clicking `provider-arbitrage` pre-fills the question.
- **Security hardening** (`1289cd4`) — see Risks/fix below.

Design rule held throughout: **recipes/resolution/key-entry are SELECTION metadata, never
provenance.** `proof/engine.py` / `receipts/export.py` / `domain/models.py` have **zero** changes;
`config_hash` and `RECEIPT_VERSION` (3) are byte-for-byte untouched (whole-branch review verified).

## Verification

- `uv run pytest -q` → **146 passed**; `uv run ruff check src tests` → clean.
- `pnpm --dir web test` → **44 passed**; `pnpm --dir web build` → clean.
- Playwright e2e (rebuilt embed) → **4/4**.
- TDD throughout (RED→GREEN per task under `.superpowers/sdd/`). Per-task reviews: all Spec✅ /
  Approved. One fix loop (Task 7): a brief-internal contradiction (provider label in both the
  banner sentence and a per-row span → `getByText` double-match) was resolved by dropping the span;
  the review then flagged that multi-distinct-provider recipes (e.g. _cheapest-that-passes_ →
  Anthropic + OpenAI keyless) would lose per-button disambiguation. **Fixed** (`692e70a`): dedupe
  unmet per provider + restored a per-row label + generic banner sentence + two locking tests.
- **Security review** (Opus `security-reviewer`): one **Important** finding — FastAPI's
  auto-generated **422 echoed the raw request body** (incl. the key) in its `input` field. The
  handler itself was clean; the leak was framework-level, reachable by any non-app caller (curl /
  proxy). **Fixed** (`1289cd4`): a global `RequestValidationError` handler strips `input` from every
  error (preserving `type`/`loc`/`msg`/`url`); a regression test POSTs a sentinel key with a missing
  field and asserts it's absent (proved RED→GREEN). Also hardened the `.env.local` temp file to
  `os.open(..., 0o600)` to close the umask window. All other secret-surface checks passed.
- **Final whole-branch review** (Opus, `fa51558..1289cd4`): **Ready to merge YES** — 0 Critical,
  0 Important; all six binding constraints verified (provenance untouched, keyless default, secrets
  never echoed/logged + 422 regression test, Tailwind v4 shorthand, unmet→cloud invariant by
  construction, composite-id format matches `build_candidates`). Packaging confirmed (`recipes.json`
  ships like `catalog.json`). Only cosmetic Minors (see below).
- **Live server check** (keyless, free port, own PID): all four recipes resolved as designed —
  `cost-vs-quality` fully unmet `[]` (→ Anthropic), `local-vs-cloud`/`cheapest-that-passes`/
  `provider-arbitrage` resolve their local arm and mark cloud arms unmet with the right `key_name`.
  Exercised the full key-entry flow: `POST /api/credentials` (fake Anthropic key) returned
  `{available: true}` with **no key echoed**, and `cost-vs-quality` flipped live to
  `[anthropic:claude-haiku-4-5, anthropic:claude-fable-5]` — **no restart**. `.env.local` written
  `0o600`; the key appears in **neither** the response **nor** the server log. The `422` path did
  not echo a sentinel key; a local-provider credential POST was rejected `400`.

## Product impact

This is the product thesis made literal: instead of assembling a candidate panel from a blank
canvas, the consultant picks the *decision they're making* and gets a coherent, environment-aware
panel + a framed question in one click — then proves it with the existing leaderboard + receipt.
Inline key entry removes the "edit a dotfile and restart" friction that otherwise blocks a recipe
the moment it needs a cloud model. Recipes compose #4's model-bearing composite candidates, so the
whole decision-recipes thread (#1 catalog → #4 picker → #5 recipes) now reads as one coherent
flow.

## Risks

- **Cosmetic Minors only** (whole-branch review, non-blocking): `_pick`/`_resolve_one` lack
  return-type annotations; two redundant quoted annotations under `from __future__`; new `routes.py`
  imports not in strict isort order (ruff isort not enforced). Optional follow-up to keep
  pyright/ruff output pristine.
- **`CLOUD_KEY_NAMES` is duplicated** (Python in `keys.py`; a small TS literal in
  `CandidatePicker.tsx`) because the selection panel doesn't carry `key_name`. Acceptable; a future
  cleanup could surface `key_name` on the `SelectionGroup` to delete the second copy.
- **Catalog price/source freshness** remains a roadmap refinement (a few values UNVERIFIED), not a
  gate — a measured receipt cost always outranks a catalog list price downstream.
- **Frontier `pick` default** chose `claude-fable-5` over `claude-opus-4-8` for the cost-vs-quality
  "Frontier" arm (latest frontier when none flagged recommended). Sensible default; the user can
  still adjust. Worth a glance if a recipe should pin a specific frontier model.

## Bug surfaced in live review (NOT a recipes regression — pre-existing leaderboard logic)

During the operator's live click-through of the shipped recipes, running **Cost vs quality** (which
selects `claude-haiku-4-5` + `claude-fable-5`) exposed a **leaderboard recommendation bug**. Fable 5
is not available on the account, so it **errored gracefully** on all 5 examples (0/5, **0 ms,
$0.00**, 5 failures) — the provider boundary worked correctly, no crash. But the leaderboard then
crowned **claude-fable-5 as "RECOMMENDED"** over `claude-haiku-4-5` (which actually ran: avg score
0.05, 3716 ms, $0.01, also 0/5 under the strict rubric).

Root cause — `src/orionfold/proof/leaderboard.py:48-50`:
```python
entries.sort(key=lambda e: (-e.pass_rate, e.avg_latency_ms, e.total_estimated_cost_usd))
if entries:
    entries[0].recommended = True
```
1. **The tiebreak rewards errors.** At a 0%-pass tie, the tiebreak is lowest latency then lowest
   cost — an errored candidate reports **0 ms / $0.00**, so it *wins ties because it failed fastest
   and cheapest*.
2. **`recommended` is set unconditionally** even when the top candidate passed 0/5 — the product
   crowns a "winner" that produced nothing, defeating the "what to trust" thesis.

Proposed fix (its own slice — touches the core proof output, so brainstorm + tests +
`receipt-quality-review`):
- Sort `(-pass_rate, -avg_score, avg_latency_ms, total_estimated_cost_usd)` so any signal beats an
  error-to-zero and quality breaks pass-rate ties.
- Mark `recommended` only when `entries[0].pass_count > 0`; otherwise mark none.
- `ProofCockpit` `DecisionSummary` + `receipts/export.py`: when no entry is recommended, show a calm
  *"No candidate passed — every option failed the rubric"* state instead of badging a loser.
- Consider distinguishing an **error** (no output) from a **fail** (low-scoring output) so an
  all-errors candidate always ranks last; regenerate sample receipts.

Evidence: a second live run (recipe **Cheapest model that still passes** → `ollama:llama3.2` +
`openai:gpt-5.4-nano` + `anthropic:claude-haiku-4-5`) reproduced it independently — **Ollama
llama3.2 was Recommended** at 0/5, 0ms, $0.00, with the failure case showing
`ProviderError: ollama HTTP 404: model 'llama3.2' not found`. The product recommended a model that
returns 404 on every example. The failure-case browser correctly surfaces the error text, and
`ResultRow` distinguishes an errored row from a low-scoring one — so the fix can rank errored rows
last using data already captured.

## Finding 2 — Similarity rubric fails correct-but-reformatted summaries (rubric weakness)

In the same run, Haiku **actually ran** and produced a factually complete summary (Example 1: a
clean Markdown table capturing $48.2M / 22% YoY / 118% NRR / 79% margin + drivers — arguably better
than the terse prose `Expected`) yet scored **0.12 / Fail**. Root cause: the v0 rubric is
**string-similarity with threshold 0.8** against the expected prose, so a correct answer in a
different *format* (table vs sentence) scores low. The rubric rewards matching the expected text's
phrasing, not meaning. For summarization this is too crude. Real fix: a **semantic / LLM-as-judge
rubric** (the charter flagged LLM-as-judge as "optional, later" — this run is the evidence it's
needed). Lower-effort interim: lower the default threshold and/or document that similarity scoring
is format-sensitive.

## Finding 3 — `claude-fable-5` should leave the catalog (or be tagged unavailable)

The catalog lists `claude-fable-5` (anthropic, frontier, ★ latest), but it errors on the operator's
account (not available) — which is what made the cost-vs-quality "Frontier" arm resolve to a model
that 404s, then get recommended (Finding 1). The static catalog can't know per-account availability,
so the fix is to **remove `claude-fable-5` from `src/orionfold/catalog/catalog.json`** (operator
decision 2026-06-20) — or, if kept, tag it preview/unavailable so the resolver/picker doesn't treat
it as a selectable default. Removing it also makes the cost-vs-quality "Frontier" selector resolve to
`claude-opus-4-8` (the real frontier). Keep the `default_model_for("anthropic")` drift-guard in sync
and re-pin `test_catalog.py` defaults if the latest-frontier changes.

## Next recommended step

Three live-review findings to address next (operator decision 2026-06-20 — log, ship recipes as-is):
1. **Leaderboard recommendation bug** (Finding 1) — highest priority; defeats the "what to trust"
   promise. Its own slice (brainstorm + tests + `receipt-quality-review`; touches `leaderboard.py`,
   `DecisionSummary`, `receipts/export.py`, sample-receipt regen).
2. **`claude-fable-5` catalog removal / unavailable tag** (Finding 3) — small, unblocks cleaner
   recipe resolution; pairs naturally with the catalog price/source pass.
3. **Similarity-rubric weakness** (Finding 2) — larger; points toward an LLM-as-judge / semantic
   rubric (charter "optional, later"). Scope its own brainstorm.
- Then **#6 prompt-variant candidates** — the next candidate axis (same model, different system
  prompt; still text-in/text-out, no new provider machinery).
- Non-blocking debt: set up a git remote + push (none configured; all `main` commits are local),
  and the optional annotation/import polish above.
