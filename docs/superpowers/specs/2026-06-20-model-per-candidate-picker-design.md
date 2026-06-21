# Model-per-candidate picker (#4) — design

- **Status:** Approved (operator, 2026-06-20)
- **Thread:** decision-recipes — sub-project #4 (the model picker that builds on the
  shipped model catalog, #1). Precedes #5 decision recipes.
- **Sources:** UI/feature review finding #4 (`docs/worklog/2026-06-20-ui-feature-review.md`),
  model-catalog spec (`docs/superpowers/specs/2026-06-20-model-catalog-design.md`),
  `HANDOFF.md` "START HERE — #4".

## Primary user story (the why)

> "I'm running Claude Opus for client summaries. Can I drop to a cheaper, faster model —
> Haiku — and still pass my own bar?"

The operator framed this precisely: **multiple models from the same provider is a genuine
proof case** — *"I want to bring down my cost, improve latency. Will my prompt work as
well?"* The user adds **both Opus and Haiku as candidates of the same provider**, runs them
against their own dataset + rubric, and the leaderboard + Proof Receipt show the
cost / latency / quality trade-off as provable evidence. That is the product thesis: not
"watch AI run" but "decide what AI to trust."

## What ships

A per-provider model picker in the run setup:

- Each `(provider, model)` pair is a candidate with a composite id `provider:model`
  (e.g. `anthropic:claude-opus-4-8`). **Mocks stay bare** (`mock_good`, `mock_bad`,
  `model=None`).
- Per **available** provider: the curated catalog models as toggle chips (★ latest /
  recommended marked) **plus a free-text custom-model escape hatch**. Toggle several chips
  on one provider to compare its models in a single run.
- **Unavailable** providers (no key / not reachable) render **greyed + disabled** with a
  quiet note. **No inline key entry in #4** — that cross-cut (writing `.env.local` + its own
  security review) is deferred to #5 by operator decision.
- A run can mix any number of these candidates across providers. `config_hash` already
  distinguishes them.

## Why this is mostly a UI + validation task (current state)

The catalog work (#1) and the v3 receipt schema already made *model* a first-class part of
candidate identity and provenance. Confirmed in code:

- `domain/models.py` — `Candidate.model: str | None` is "part of the candidate's identity and
  feeds the run's `config_hash`."
- `proof/engine.py:config_hash` already hashes `{id, provider_id, privacy, model}` per
  candidate → two runs differing only by model already produce different hashes.
- Providers already do `model = candidate.model or self.default_model`
  (e.g. `providers/anthropic.py`). The model-per-candidate hook already exists.
- `domain/models.py:LeaderboardEntry.model` already records model per candidate;
  `RECEIPT_VERSION = 3` already carries it.

The **only** real gaps:

1. `providers/registry.py:available_candidates()` returns **one candidate per provider**
   (its default model). There is no way to select a non-default model.
2. `server/routes.py` `create_run` / `create_run_stream` validate `candidate_ids` against
   that fixed one-per-provider set, so a composite/custom id is rejected.
3. The frontend (`web/src/features/proof/RunSetup.tsx`) renders a flat checkbox list from
   `GET /api/candidates` and never consumes `GET /api/catalog`.

## Hard invariants (must not regress)

- **`config_hash` payload and `RECEIPT_VERSION = 3` are untouched.** The catalog and the
  picker are *selection* scaffolding, never *provenance*. We do not change what `config_hash`
  hashes.
- **Mocks keep bare ids** (`mock_good`, `mock_bad`). Therefore every existing mock-based run
  and the whole test contract (`config_hash` value, "100% (5/5)", "Failure cases (5)",
  "simulated provider failure") is byte-identical. Only *real* providers gain composite ids;
  there are no persisted real-provider receipts to preserve.
- **Keyless-safe.** A custom model on an unavailable provider is rejected at run time. Cloud
  providers are only "available" when their key resolves (existing `_build()` rule).
- **No secrets** in `GET /api/selection` (asserted in tests, mirroring `/api/catalog`).
- Mocks carry `model=None` and ignore model (unchanged).
- The default keyless mock proof path, the Proof-Run-default view, the 3-format receipt, both
  run endpoints, dataset routes, the theme system, and the model catalog (selection-only)
  all stay intact.

## Backend design (thin)

### 1. `build_candidates(candidate_ids) -> list[Candidate]` (in `providers/registry.py`)

The single source of truth for turning request ids into validated candidates, used by **both**
`create_run` and `create_run_stream`.

Rules, per id:

- **Bare id already in `available_candidates()`** (a mock, or a real provider's default) →
  use that candidate as-is. *Backward compatible:* old bare-id requests (and `/api/candidates`)
  keep working unchanged.
- **Composite `provider:model`** → split on the **first** colon (`str.partition(":")`, so
  `ollama:llama3.1:8b` → provider `ollama`, model `llama3.1:8b`). Accept iff the provider is
  **available** (`provider_id in _build()`) **and** `model` is a non-empty string. Construct:

  ```python
  provider, _ = _build()[provider_id]
  Candidate(
      id=cid,                                  # composite, e.g. "anthropic:claude-opus-4-8"
      label=f"{provider.label} · {model}",
      provider_id=provider_id,                 # BARE provider id — engine calls get_provider(provider_id)
      privacy=provider.privacy,
      model=model,
  )
  ```

- **Anything else** (unknown provider, unavailable provider, empty model, malformed) →
  collected and raised as `UnknownCandidateError(unknown_ids)`.

Notes:
- `provider_id` is the **parsed** provider, never the composite id — the engine does
  `get_provider(candidate.provider_id)` and the provider does `candidate.model or default_model`,
  so composite candidates route and run correctly.
- A custom model is just a string the user typed; it is sent verbatim to an *available*
  provider's API. No validation of model existence (the provider call surfaces a graceful
  `ProviderResult` error if the model is wrong — the existing `safe_generate` boundary).

### 2. `selection_panel() -> SelectionPanel` (new `providers/selection.py`)

Server-side merge of `load_catalog()` (all models) + `_build()` / `available_candidates()`
(availability + mocks). This is the one thing the picker reads; #5 reuses the same
server-side availability resolution.

Pydantic response models (colocated in `providers/selection.py`):

```python
class SelectionModel(BaseModel):
    candidate_id: str          # e.g. "anthropic:claude-opus-4-8"
    model: str                 # "claude-opus-4-8"
    display_name: str
    tier: Tier
    cost_class: CostClass
    context_window: int | None = None
    latest: bool = False
    recommended: bool = False

class SelectionGroup(BaseModel):
    provider_id: str           # "anthropic", "mock_good", ...
    label: str                 # provider label (raw, no "· model" suffix)
    privacy: Privacy
    available: bool
    supports_custom: bool      # real providers True; mocks False
    candidate_id: str | None   # set for mocks (group itself is one candidate); None for model providers
    models: list[SelectionModel]   # empty for mocks

class SelectionPanel(BaseModel):
    providers: list[SelectionGroup]
```

Build rules:
- **Catalog providers** (anthropic, openai, gemini, openrouter, ollama, lmstudio) → one group
  each, `available = provider_id in _build()`, `supports_custom = True`, `candidate_id = None`,
  `models` from the catalog (each `candidate_id = f"{provider_id}:{model.id}"`).
- **Mocks** (`mock_good`, `mock_bad`, present in `_build()` but not the catalog) → one group
  each, `available = True`, `supports_custom = False`, `candidate_id = <mock id>`, `models = []`.
- Group ordering: mocks first (the default keyless path), then catalog providers in catalog
  order. Available providers need not be sorted ahead of unavailable — the UI greys in place.
- **No credentials** anywhere in the payload (no key values; provider labels and model ids
  only). `Tier` / `CostClass` re-exported from `orionfold.catalog` so the module can type them
  (the deferred re-export from the catalog spec — a consumer now exists).

### 3. Routes (`server/routes.py`)

- **New `GET /api/selection`** → returns `selection_panel()`. Read-only, no secrets.
- **`create_run` / `create_run_stream`**: replace the inline
  `available = {c.id: c for c in available_candidates()}` lookup with:
  - keep the empty check → 400 `"Select at least one candidate"`.
  - `candidates = build_candidates(body.candidate_ids)`; on `UnknownCandidateError` → 400
    `f"Unknown candidate(s): {unknown}"` (preserves the existing message shape).
- `/api/candidates` is **unchanged** (kept for backward compat + the read-only CandidatesView).

## Frontend design

- **`web/src/lib/api.ts`** — add `getSelection()` calling `GET /api/selection` with a Zod
  schema mirroring `SelectionPanel`.
- **New `web/src/features/proof/CandidatePicker.tsx`** — provider-grouped chips (approved
  layout). For each group:
  - **mock** group → a single toggle chip (label), value = `group.candidate_id`.
  - **available model provider** → a chip per `models[]` (display_name, ★ for `latest`,
    a subtle mark for `recommended`, `cost_class`), value = `model.candidate_id`; plus a
    "+ custom" affordance that reveals a text field → on submit adds a chip with
    `candidate_id = ${provider_id}:${text.trim()}`.
  - **unavailable** provider → models rendered greyed + disabled (not toggleable) with a quiet
    "Unavailable — add a key (coming with recipes)" note. No key entry.
  - Selection state = a `Set<string>` of `candidate_id`s, passed through to the run request as
    today's `candidate_ids` (no request-schema change).
- **`RunSetup.tsx`** — swap the flat checkbox `fieldset` for `<CandidatePicker>`; keep the
  selected-ids → `candidate_ids` wiring and the run-submit path unchanged.
- States: loading / error / populated; greyed unavailable; chips keyboard-toggleable
  (charter: core action keyboard-accessible). Tailwind v4 CSS-var parenthesis shorthand
  (`bg-(--color-x)`), never `bg-[--color-x]`.
- `CandidatesView.tsx` (read-only reference) may stay on `/api/candidates` for now.

## Testing strategy

**Backend (TDD, RED→GREEN):**
- `build_candidates`:
  - bare mock id → unchanged candidate (back-compat).
  - bare real-default id (when available) → unchanged candidate.
  - composite `provider:model` for an available provider → candidate with `provider_id`
    parsed, `model` set, composite `id`, label `"<label> · <model>"`.
  - colon-in-model (`ollama:llama3.1:8b`) → model preserved whole.
  - custom model string on an available provider → accepted.
  - composite on an **unavailable** provider (no key) → `UnknownCandidateError` (keyless-safe).
  - empty model (`anthropic:`) / unknown provider / malformed → `UnknownCandidateError`.
- `selection_panel()` / `GET /api/selection`:
  - shape: mocks first with `models == []` and `supports_custom False`; catalog providers with
    populated `models` and correct `candidate_id` format.
  - availability reflects `_build()` (mocks + local available; cloud only with key).
  - **no-secrets** assertion over the serialized payload (mirrors the `/api/catalog` test).
- **Regression:** a mock-only run's `config_hash` equals the pre-change value (mocks unchanged).
- Provider tests still skip gracefully without credentials.

**Frontend (Vitest):**
- picker renders groups from a `SelectionPanel` fixture; mock chip + model chips.
- toggling a model chip selects the right `candidate_id`; toggling several on one provider
  yields multiple ids.
- custom field builds `${provider_id}:${text}`.
- unavailable provider chips are disabled.

**e2e (Playwright):** pick a model chip (mock path stays keyless), run a proof, leaderboard
renders — preserving the test-contract strings (heading "Orionfold Proof", "Connected",
button /Run proof/, "Leaderboard", "100% (5/5)", "Failure cases (5)").

## Verification (gate before done)

`uv run pytest` · `uv run ruff check src tests` · `pnpm --dir web test` · `pnpm --dir web build`
· rebuild embed (`bash scripts/build.sh`) + Playwright e2e · real-browser check on a
provably-free port. Open review-bound markdown in Obsidian one at a time.

## Out of scope (explicit)

- Inline `.env.local` key entry for unavailable providers → **#5** (own security review).
- Decision recipes / named presets → **#5**.
- Searchable/giant model lists (OpenRouter long tail) → custom escape hatch covers it for now.
- Prompt-variant candidates (#6), URL routing (#10).
- Changing `config_hash`, `RECEIPT_VERSION`, or receipt schema.
- Operator price/source verification pass for `catalog.json` (separate, non-blocking).
