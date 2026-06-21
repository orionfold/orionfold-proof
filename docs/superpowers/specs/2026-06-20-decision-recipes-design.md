# Decision Recipes — Design (#5 of the decision-recipes thread)

- **Status:** Approved (operator-approved 2026-06-20)
- **Date:** 2026-06-20
- **Builds on:** #1 model catalog (`src/orionfold/catalog/`), #4 model-per-candidate picker
  (`providers/selection.py`, `build_candidates()`), ADR-0002 (credential resolution).
- **Thesis:** Turn "pick models" (a blank-canvas chore) into "pick the decision you're making."

## Problem

The picker (#4) lets a user assemble a panel of `provider:model` candidates by hand. That is
still a blank canvas. The leveraged move (UI-review §Synthesis) is **named comparison presets**
that map to a real question a consultant asks and auto-select a *coherent* candidate panel.

The example recipes are **semantic, not literal**: "Local vs cloud" means "a local model AND a
cloud model" — which specific ones depends on what is available right now. So a recipe cannot
hardcode `provider:model` ids; it declares intent and the server resolves it against the live
catalog ∩ availability (the same merge `/api/selection` already performs).

## Locked decisions (operator, 2026-06-20)

1. **One slice**: recipes **and** inline `.env.local` key entry ship together (key entry gets its
   own `security-secrets-review`).
2. **Semantic selectors** resolved server-side (not pinned ids, not hybrid).
3. **UI**: a recipe **row above** the existing Proof setup; clicking a recipe pre-fills the setup
   below. The active recipe stays highlighted; hand-editing flips it to "Custom."
4. **Seeds**: a recipe pre-fills the **candidate panel + decision question only** — NOT task name,
   NOT dataset, NOT rubric. (Datasets are the user's own imported data; forcing one fights the
   import. Task name keeps its existing dataset-name mirroring.)
5. **Key entry**: a **shared** component used in two places — greyed picker groups AND a recipe's
   unmet-selector banner. On submit: **write to `.env.local` + re-resolve availability, no network
   verification**. A bad key fails gracefully at run time via the existing `safe_generate` path.

## Why availability makes this clean

`config/keys.py` parses `.env.local` **fresh on every `resolve_key` call** (no cache), and
`providers/registry.py` rebuilds via `_build()` on every call. So writing a key to `.env.local`
flips that provider's availability on the **next** `/api/selection` / `/api/recipes` call — no
server restart. Precedence is **system-env-first**, so a provider is only ever "unavailable" when
its key is absent from the system env; writing to `.env.local` unlocks it with no precedence
conflict.

The registry **always** offers the keyless local providers (`ollama`, `lmstudio`) and the mocks,
and gates only the four **cloud** providers (`openai`, `openrouter`, `gemini`, `anthropic`) on key
presence. Therefore **an unmet selector always resolves to a cloud provider needing a key** — which
is exactly what the key-entry flow handles. Local selectors never go "unmet" at selection time
(their runtime may still fail if the local server is down — handled by `safe_generate`, unchanged).

## Architecture

### Backend — new `src/orionfold/recipes/` package (mirrors `catalog/`)

**`recipes/models.py` — schema (Pydantic)**

```
Selector:
  label: str            # human tag shown in the resolved panel ("Economy", "Cloud frontier")
  family: str | None    # catalog family: "claude" | "gpt" | "gemini" | "llama"
  tier:   Tier | None   # "frontier" | "balanced" | "economy"
  privacy: Privacy | None  # "local" | "cloud"
  provider: str | None  # pin to a specific provider id (e.g. "ollama")
  pick: Literal["recommended","cheapest","latest"] = "recommended"

Recipe:
  id: str
  title: str
  subtitle: str
  decision_question: str
  selectors: list[Selector]   # >= 1

RecipeBook:
  version: int
  recipes: list[Recipe]
```

Validation: `selectors` non-empty; `family`/`tier`/`privacy` values constrained by the same
`Literal`s the catalog uses; recipe `id`s unique.

**`recipes/recipes.json` — the four bundled recipes**

| id | title | selectors |
|----|-------|-----------|
| `cost-vs-quality` | Cost vs quality for client summaries | `{label:"Economy", family:claude, tier:economy}` · `{label:"Frontier", family:claude, tier:frontier}` |
| `local-vs-cloud` | Local vs cloud (privacy) | `{label:"Local", privacy:local}` · `{label:"Cloud frontier", privacy:cloud, tier:frontier}` |
| `cheapest-that-passes` | Cheapest model that still passes | `{label:"Local", privacy:local}` · `{label:"Claude economy", family:claude, tier:economy}` · `{label:"GPT economy", family:gpt, tier:economy}` |
| `provider-arbitrage` | Same model, different providers | `{label:"Llama on Ollama", family:llama, provider:ollama}` · `{label:"Llama on OpenRouter", family:llama, provider:openrouter}` |

(`decision_question` per recipe, e.g. cost-vs-quality → "Which model gives me trustworthy client
summaries at the lowest cost?" Exact copy finalized in the plan; must read as a real consultant
question.)

**`recipes/resolution.py` — the resolver**

`resolve_recipes() -> RecipesPanel`:
- Load the catalog and build the same availability set `selection_panel()` uses
  (`set(_build())`).
- Flatten catalog into `(provider, model)` rows.
- For each selector, in order:
  1. Filter rows by every present constraint (`family`, `tier`, `privacy`, `provider`).
  2. Partition into **available** (provider in availability set) and **unavailable**.
  3. If any available match: pick one by `pick` strategy (`recommended` → `recommended` flag then
     `latest`; `cheapest` → lowest `pricing.input_per_mtok`, locals `$0` first; `latest` →
     `latest` flag). Emit **resolved** `{label, candidate_id: f"{provider.id}:{model.id}",
     display_name, provider_id, cost_class}`.
  4. Else if any unavailable match: emit **unmet** `{label, needs_provider_id,
     needs_provider_label, key_name}` (provider of the cheapest unavailable match).
  5. Else (no catalog match at all): drop the selector (a recipe referencing a family the catalog
     no longer carries simply contributes nothing — logged at debug, never crashes).
- `candidate_ids` = the resolved candidate ids, de-duplicated, order preserved.

**Pydantic output models** (`recipes/resolution.py` or `models.py`):

```
ResolvedSelector { label, candidate_id, display_name, provider_id, cost_class }
UnmetSelector    { label, needs_provider_id, needs_provider_label, key_name }
ResolvedRecipe   { id, title, subtitle, decision_question, candidate_ids[],
                   resolved: ResolvedSelector[], unmet: UnmetSelector[] }
RecipesPanel     { recipes: ResolvedRecipe[] }
```

Carries **no secrets** — provider labels, model ids, and `key_name` (the env var NAME, never a
value).

**`config/env_file.py` — the `.env.local` writer**

`set_key_in_env_local(key_name: str, value: str) -> None`:
- Resolve the target path: `ORIONFOLD_ENV_FILE` override if set, else `<cwd-or-project-root>/.env.local`
  (reuse the project-root location logic in `keys.py`; create the file if absent).
- Read existing lines; replace the line defining `key_name` if present, else append
  `KEY_NAME=value`. **Preserve all other lines, comments, and ordering.**
- **Atomic write**: write a temp file in the same dir, `os.replace` over the target.
- **`chmod 0o600`** on the file (keys are sensitive).
- The value is **never** logged, echoed, or returned.

**Credential whitelist** — add `CLOUD_KEY_NAMES: dict[str, str]` (provider_id → key env name) as a
single source of truth (`config/keys.py` or `providers/registry.py`), used by the credential
endpoint as an allow-list and re-usable by the registry. Maps exactly:
`anthropic→ANTHROPIC_API_KEY, openai→OPENAI_API_KEY, openrouter→OPENROUTER_API_KEY,
gemini→GEMINI_API_KEY`. (Local/mock providers are absent → rejected.)

**Endpoints (`server/routes.py`)**

- `GET /api/recipes -> RecipesPanel` — read-only, resolved for the current environment. No secrets.
- `POST /api/credentials` — body `{ provider_id: str, key: str }`:
  - Look up `key_name = CLOUD_KEY_NAMES[provider_id]`; **404/400** if provider_id not in the
    whitelist (no arbitrary env writes).
  - Reject empty/whitespace key (**422**).
  - `set_key_in_env_local(key_name, key)`.
  - Return `{ provider_id, available: has_key(key_name) }` — **never** the key.

### Frontend

- **`lib/api.ts`**: `getRecipes(): Promise<RecipesPanel>`, `setProviderKey(providerId, key):
  Promise<{provider_id, available}>`, plus the `RecipesPanel`/`ResolvedRecipe`/`ResolvedSelector`/
  `UnmetSelector` types.
- **`features/proof/RecipeRow.tsx`**: a horizontal row of recipe cards above `RunSetup`, under a
  "Start from a decision recipe" heading. Each card: `title`, `subtitle`, and a one-line summary
  (`{resolved.length} models` · `{unmet.length} need a key` when unmet > 0). The active recipe card
  carries the accent highlight. Clicking calls `onSelectRecipe(recipe)`. When a recipe is active and
  has unmet selectors, a small banner under the row names the provider(s) and renders `KeyEntry`.
- **`features/proof/KeyEntry.tsx`** (shared): `{ providerId, providerLabel, keyName }` →
  `type="password"` input + "Save key" button. On submit: `setProviderKey`, then invalidate the
  `["selection"]` and `["recipes"]` queries; clear the field on success; show a terse inline error
  on failure. **Nested-`<form>`-safe** (the #4 lesson): a `div`, button `type="button"`, Enter
  handled via `onKeyDown` with `preventDefault`/`stopPropagation` so it never submits `RunSetup`'s
  outer `<form>`. `autoComplete="off"`. The field value lives only in local component state and is
  cleared on success — never lifted, logged, or persisted.
- **`features/proof/CandidatePicker.tsx`**: each **greyed/unavailable** cloud provider group gains
  an "Add key" expander that renders the shared `KeyEntry`. (Local providers and mocks: unchanged.)
- **`features/proof/ProofCockpit.tsx`** wiring:
  - New query: `recipes` via `getRecipes` (`queryKey: ["recipes"]`).
  - New state: `activeRecipeId: string | null`.
  - `onSelectRecipe(r)` → `setSelected(r.candidate_ids)`,
    `setBrief({ ...effectiveBrief, decision_question: r.decision_question })`,
    `setActiveRecipeId(r.id)`.
  - `toggleCandidate` and `handleBriefChange` (decision_question edits) set `activeRecipeId = null`
    → the row shows "Custom."
  - Render `RecipeRow` above `RunSetup`, passing `recipes.data`, `activeRecipeId`, `onSelectRecipe`.
  - A fully-unmet recipe sets `selected = []` → `canRun` stays false (Run disabled); the unmet
    banner guides the user to add a key. After a key is saved, `["recipes"]` refetches; the user
    **re-clicks** the recipe to get the now-complete panel (deliberately explicit, not auto-magic,
    to avoid fighting hand-edits).

## Guardrails (non-regression)

- **Provenance untouched**: recipes + resolution are SELECTION metadata only. `proof/engine.py`,
  `receipts/export.py`, `domain/models.py` unchanged. `config_hash` and `RECEIPT_VERSION` (3) stay
  byte-for-byte. Recipes never enter the receipt.
- **Keyless default preserved**: mocks stay pre-selected on load; recipes are opt-in. Recipes only
  ever compose real model-bearing composite ids — mocks are not in the catalog, so a recipe can
  never select a mock (keeps the "mocks stay bare-id" invariant from #4 intact).
- **Security** (own `security-secrets-review`): keys never logged / echoed / committed / written to
  receipts or screenshots; `.env.local` is gitignored (`.env.*`) and written `0o600`; the
  provider→key whitelist blocks arbitrary env writes; the credential endpoint returns only a
  boolean availability flag.
- **Tailwind v4**: CSS vars use the parenthesis shorthand `bg-(--color-x)`, never `bg-[--color-x]`.
- **Test-contract strings** (headings, button copy, region labels) unchanged.

## Testing

**Backend (pytest)**
- `recipes/recipes.json` loads and validates; every selector's `family`/`tier`/`privacy` is a legal
  catalog value; recipe ids unique.
- Resolver under a **keyless** env (`ORIONFOLD_ENV_FILE` → empty temp file): local selectors
  resolve to `ollama`/`lmstudio` candidate ids; cloud selectors emit **unmet** with the right
  `key_name`; `cost-vs-quality` is fully unmet → `candidate_ids == []`.
- Resolver **with** a temp `.env.local` carrying `ANTHROPIC_API_KEY`: `cost-vs-quality` resolves to
  `anthropic:<economy>` + `anthropic:<frontier>` composite ids.
- `GET /api/recipes` response contains **no** secret-shaped substrings (assert no key values; the
  env has none anyway — assert structure + `key_name` is a NAME).
- `config/env_file.set_key_in_env_local`: creates a new file; updates an existing key in place;
  preserves other lines/comments; sets `0o600`; the written value never appears in any return value
  or log. Idempotent on repeat.
- `POST /api/credentials`: writes the key (temp `ORIONFOLD_ENV_FILE`), flips `has_key`, returns
  `available: true`, **never** echoes the key; unknown/local/mock `provider_id` → 4xx; empty key →
  422.

**Frontend (Vitest)**
- `RecipeRow`: renders a card per recipe with summary; clicking calls `onSelectRecipe` with the
  recipe; the active recipe card is highlighted; an unmet recipe shows the "needs a key" hint.
- `KeyEntry`: typing + Save calls `setProviderKey(providerId, value)`; rendered **inside a
  `<form>`**, Save does **not** submit the outer form and Enter in the field does not either
  (regression mirroring #4's nested-form fix); field clears on success.
- `ProofCockpit`/integration: selecting a recipe sets the candidate selection + decision question;
  editing a candidate or the question flips the active recipe to Custom.

**e2e (Playwright, keyless)**
- The recipe row renders above setup.
- Clicking a recipe whose selectors are satisfiable keyless (e.g. `provider-arbitrage`'s local arm,
  or a local-only recipe) pre-fills candidates + the decision question.
- A cloud recipe shows greyed/unmet "needs a key" affordance (no real key submitted in e2e).

## Out of scope (explicit)

- No network key verification (write + re-resolve only).
- No editing/creating recipes in-app (recipes are bundled JSON, like the catalog).
- Recipes do not touch dataset, rubric, or task name.
- No change to provenance, the receipt, or `config_hash`.
- Prompt-variant candidates (#6) remain the separate next axis.

## File-by-file summary

**New**
- `src/orionfold/recipes/__init__.py` (`load_recipes`, re-exports)
- `src/orionfold/recipes/models.py` (`Selector`, `Recipe`, `RecipeBook`)
- `src/orionfold/recipes/recipes.json`
- `src/orionfold/recipes/resolution.py` (`resolve_recipes`, output models)
- `src/orionfold/config/env_file.py` (`set_key_in_env_local`)
- `web/src/features/proof/RecipeRow.tsx`
- `web/src/features/proof/KeyEntry.tsx`
- tests: `tests/test_recipes.py`, `tests/test_env_file.py`, `tests/test_credentials_route.py`,
  `tests/test_recipes_route.py`; `web/src/features/proof/RecipeRow.test.tsx`,
  `web/src/features/proof/KeyEntry.test.tsx`

**Modified**
- `src/orionfold/config/keys.py` *or* `providers/registry.py` — add `CLOUD_KEY_NAMES` whitelist.
- `src/orionfold/server/routes.py` — `GET /api/recipes`, `POST /api/credentials`.
- `web/src/lib/api.ts` — `getRecipes`, `setProviderKey`, types.
- `web/src/features/proof/ProofCockpit.tsx` — recipes query, `activeRecipeId`, `onSelectRecipe`,
  render `RecipeRow`.
- `web/src/features/proof/CandidatePicker.tsx` — `KeyEntry` on greyed cloud groups.
- packaging: ensure `recipes.json` ships in the wheel (mirror how `catalog.json` is bundled).
- `web/e2e/proof.spec.ts` — recipe-row assertions.
