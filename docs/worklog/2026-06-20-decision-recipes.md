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

## Next recommended step

- **#6 prompt-variant candidates** — the next candidate axis (same model, different system prompt;
  still text-in/text-out, no new provider machinery). OR the catalog price/source verification pass.
- Non-blocking debt: set up a git remote + push (none configured; all `main` commits are local),
  and the optional annotation/import polish above.
