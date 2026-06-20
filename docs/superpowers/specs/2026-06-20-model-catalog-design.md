# Model Catalog — Design Spec

_Date: 2026-06-20 · Status: **proposed** (awaiting operator spec review) · Sub-project #1 of the
"decision recipes" strategic thread (review finding #5, entangled with #4)._

> Origin: `docs/worklog/2026-06-20-ui-feature-review.md` findings #4/#5/#7. The operator chose to
> pursue **decision recipes plus model-per-candidate (#4)**, and to anchor both on a comprehensive
> **provider → model → capabilities catalog** that "a lot of future features" can hang off.

## Problem

The Proof Run candidate panel offers exactly **one candidate per available provider**, each pinned to
a single hardcoded default model. There is no way to:

- compare two models *within* the same provider (cost↔quality, latest↔incumbent), or
- compose a *coherent, named panel* that maps to a real decision a consultant is making.

Underneath that, the per-provider default models are **hardcoded in four separate places**
(`registry.py`, `ollama.py`, `gemini.py`, `anthropic.py`), so there is no single source of truth for
"what models exist and what are they like." Any richer model-selection feature (model picker, decision
recipes, smarter leaderboard labels) needs that source of truth first.

## Goal of this sub-project (#1)

Establish the **model catalog** as the substrate the rest of the thread builds on, as a thin,
behavior-preserving vertical slice:

1. A bundled `catalog.json` describing `provider → model → capabilities`.
2. A Pydantic schema + cached loader (mirrors the existing `datasets` pattern).
3. A read-only `GET /api/catalog` endpoint that surfaces it.
4. **Consolidation:** the scattered default-model constants become *sourced from the catalog* — single
   source of truth, with identical runtime behavior (proven by a regression test).

### Non-goals (deferred to later sub-projects, each its own spec → plan → implementation)

- **#2 Model-per-candidate** — picker UI over the catalog; candidates carry a chosen model; the run
  path accepts custom models. _Nothing in #1 changes the `Candidate` shape or the run path._
- **#3 Decision recipes** — named presets that compose a panel from the catalog + seed a decision
  question, with graceful degradation for unavailable providers.
- **Inline key entry** — writing a provider key to `.env.local` from the UI (its own security review).
- **Receipt-driven re-ranking** — the future loop where measured receipts refine the catalog. The
  schema is designed to *accommodate* it; #1 does **not** build it.

In #1, **nothing consumes the new capability fields except the endpoint.** That is intentional: it
keeps the slice foundational and low-risk.

## Decomposition & build order (context)

```
        ┌─────────────────────────────────────────────┐
        │  #1  MODEL CATALOG  (data + schema + endpoint)│  ← THIS SPEC
        │      provider → model → capabilities          │
        └───────────────┬───────────────────────────────┘
                        │ consumed by
        ┌───────────────┼───────────────┬───────────────┐
        ▼               ▼               ▼               ▼
   #2 Model-per-   #3 Decision     leaderboard /   (future) receipt-
   candidate       recipes         label polish    driven re-ranking
   picker UI       compose panel
        └─ inline key entry hooks in where a provider is unavailable
```

Build order: **#1 → #2 → #3**, with inline-key-entry as a cross-cut added when #2/#3 surface an
unavailable provider.

## Design — the catalog as a living, evidence-validated artifact

The catalog begins as a vendor **spec sheet** (including list prices). The product already measures
**real cost & latency** on every run. The strategic intent (future sub-project) is that **measured
receipts become the source of truth that refines the catalog** — closing the product's core loop:
the catalog says what vendors *claim*, the receipt proves what's *true on your task*, and the proof
feeds back to re-rank the catalog.

This frames a hard rule that #1 must respect so the catalog never undermines the thesis:

> **The catalog informs *selection*; the receipt delivers *truth*.** A measured receipt cost always
> visually and semantically outranks a catalog list price. A catalog price is a dated, sourced
> reference — never a claim the receipt was meant to prove.

### File layout (mirrors the `datasets` pattern)

```
src/orionfold/catalog/
  __init__.py      # load_catalog() -> ModelCatalog (cached); default_model_for(provider_id) -> str
  models.py        # Pydantic schema (below)
  catalog.json     # bundled reference data
```

`load_catalog()` reads `catalog.json` via `importlib.resources` and validates into `ModelCatalog`,
exactly as `data/__init__.py:load_dataset()` does for datasets. It is cached (`functools.cache`) since
the data is static for the process lifetime.

### Schema

```python
# src/orionfold/catalog/models.py
from typing import Literal
from pydantic import BaseModel, model_validator
from orionfold.domain.models import Privacy   # Literal["local", "cloud"]

class ModelPricing(BaseModel):
    input_per_mtok: float          # USD per 1M input tokens — a LIST price, not a claim
    output_per_mtok: float
    currency: str = "USD"
    as_of: str                     # ISO date the price was recorded
    source: str                    # provider pricing-page URL

class CatalogModel(BaseModel):
    id: str                        # exact string sent to the provider API (e.g. "claude-opus-4-8")
    display_name: str              # "Claude Opus 4.8"
    family: str                    # "claude" | "gpt-4o" | "gemini" | "llama" — enables "same family across providers"
    tier: Literal["frontier", "balanced", "economy"]   # quality tier — drives cost↔quality recipes
    context_window: int | None = None
    cost_class: Literal["free", "$", "$$", "$$$"]       # stable selection signal; local = "free"
    pricing: ModelPricing | None = None                 # None for local models
    latest: bool = False           # newest in its family
    recommended: bool = False      # curated "good default to compare"

class CatalogProvider(BaseModel):
    id: str                        # matches provider registry ids: anthropic, openai, ollama, ...
    label: str
    privacy: Privacy
    default_model: str             # MUST equal one models[].id (validated)
    models: list[CatalogModel]

    @model_validator(mode="after")
    def _check(self) -> "CatalogProvider":
        ids = [m.id for m in self.models]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate model id in provider {self.id}")
        if self.default_model not in ids:
            raise ValueError(f"default_model {self.default_model!r} not in provider {self.id} models")
        return self

class ModelCatalog(BaseModel):
    version: int                   # catalog schema version (starts at 1)
    as_of: str                     # catalog-wide snapshot date
    providers: list[CatalogProvider]
```

Design notes:

- **`privacy` decouples local-vs-cloud from `tier`.** A small local model is still
  `tier:"economy"`, `privacy:"local"`, `cost_class:"free"`. This keeps the two future recipe axes
  ("local vs cloud" and "cost↔quality") independent.
- **`family` + `tier`** are the fields that make later recipes expressive: cost↔quality sorts by
  `tier`/`cost_class`; "same weights across providers" groups by `family`; "local vs cloud" splits on
  `privacy`.
- **`pricing` is optional and always carries `as_of` + `source`.** Local models set `pricing: null`
  and `cost_class: "free"`.
- **Mocks stay out of the catalog.** `mock_good`/`mock_bad` have `model=None` and no capabilities;
  they remain special-cased in the registry exactly as today.

### Pricing honesty mechanism

Exact prices are **content, not design.** The spec fixes the *shape* and the *honesty mechanism*
(every `pricing` block carries `as_of` + `source`). The actual numbers are filled against live
provider pricing pages **during implementation** and verified — never invented as fact. The
catalog-wide `as_of` makes overall staleness visible at a glance.

### Consolidation (behavior-preserving refactor)

Default models are currently hardcoded in four places:

| Provider | Current default | Where |
| --- | --- | --- |
| openai | `gpt-4o-mini` | `registry.py:_OPENAI_DEFAULT` |
| openrouter | `openai/gpt-4o-mini` | `registry.py:_OPENROUTER_DEFAULT` |
| lmstudio | `local-model` | `registry.py:_LMSTUDIO_DEFAULT` |
| ollama | `llama3.2` | `ollama.py:DEFAULT_MODEL` |
| gemini | `gemini-2.5-flash` | `gemini.py:DEFAULT_MODEL` |
| anthropic | `claude-haiku-4-5` | `anthropic.py:DEFAULT_MODEL` |

#1 introduces `default_model_for(provider_id) -> str` (in `catalog/__init__.py`) that reads the
catalog, and rewires those call sites to use it.

- **Override precedence is preserved exactly:** `ORIONFOLD_<PROVIDER>_MODEL` env var > catalog
  `default_model`. The env-var resolution logic is unchanged; only the *fallback constant* now comes
  from the catalog.
- The seeded `default_model` per provider **equals the current constant**, so runtime behavior is
  identical. A regression test locks this for all six providers.
- `default_model_for` raises if a provider id is absent from the catalog, so the registry and catalog
  can never silently drift.

### Endpoint

`GET /api/catalog` returns the full `ModelCatalog` as JSON. Read-only, no params. The catalog
contains zero credentials (asserted in a test). This is what #2's picker and #3's recipes will consume.

### Seed coverage (starter content; finalized + price-verified at implementation)

A **small curated set** per provider (the default + 1–2 others spanning tiers) — *not* an exhaustive
list. The free-text "custom model" escape hatch (built in #2) covers anything not listed, which is how
"comprehensive in dimensions" is achieved without an unmaintainable "comprehensive in model count"
list. Indicative starter set (exact ids/prices verified at build time):

- **anthropic** (cloud): `claude-haiku-4-5` (economy, default, recommended), `claude-sonnet-4-6`
  (balanced), `claude-opus-4-8` (frontier, latest).
- **openai** (cloud): `gpt-4o-mini` (economy, default), `gpt-4o` (balanced).
- **gemini** (cloud): `gemini-2.5-flash` (economy, default), `gemini-2.5-pro` (frontier).
- **openrouter** (cloud): `openai/gpt-4o-mini` (default) + 1–2 cross-family entries to demonstrate the
  "same family across providers" axis.
- **ollama** (local): `llama3.2` (default), 1 larger local model. `cost_class:"free"`, `pricing:null`.
- **lmstudio** (local): `local-model` (default placeholder; user-loaded). `cost_class:"free"`.

## Data flow

```
catalog.json ──load_catalog()──▶ ModelCatalog (validated, cached)
                                      │
                  ┌───────────────────┼─────────────────────┐
                  ▼                                          ▼
       default_model_for(pid)                        GET /api/catalog
        (registry + provider                          (read-only JSON;
         modules call this as                          consumed by #2/#3
         their fallback constant)                      later)
```

## Error handling

- Malformed `catalog.json` fails fast at load with a clear Pydantic validation error — caught by
  tests, never reaches users.
- `default_model_for(unknown_provider)` raises `KeyError`/`ValueError` (guards registry/catalog drift).
- The endpoint cannot leak secrets: the catalog is static reference data with no credential fields.

## Testing (proof for #1)

1. **Schema/data integrity:** `catalog.json` loads and validates; per provider `default_model ∈
   {model ids}`; model ids unique; every `pricing` block has non-empty `as_of` and `source`.
2. **Regression lock:** `default_model_for(p)` returns the *current* constant for all six real
   providers (openai, openrouter, lmstudio, ollama, gemini, anthropic).
3. **Override precedence:** with `ORIONFOLD_<P>_MODEL` set, the env value wins over the catalog
   default; unset, the catalog default is used.
4. **Endpoint:** `GET /api/catalog` → 200, body parses into `ModelCatalog`, provider `privacy` values
   correct, and the serialized body contains no key-like strings (defense-in-depth assertion).

## Risks & mitigations

- **Stale prices** (an evidence-first product asserting wrong numbers). _Mitigation:_ `as_of` + `source`
  on every price; catalog-wide `as_of`; the hard rule that measured receipt cost outranks list price;
  prices verified against source pages at implementation.
- **Catalog/registry drift.** _Mitigation:_ `default_model_for` raises on unknown provider; regression
  test pins defaults.
- **Scope creep toward an exhaustive model list.** _Mitigation:_ curated small set + escape hatch (in
  #2); "comprehensive in dimensions, not model count."
- **Provenance impact.** None: `config_hash`/`RECEIPT_VERSION` are untouched — the catalog is
  pre-run selection scaffolding, not run identity. (Confirmed against `proof/engine.py:config_hash`.)

## Acceptance

- `catalog.json` + schema + cached loader exist and validate.
- Default models for all six providers are sourced from the catalog with identical runtime behavior
  (env override precedence preserved), proven by tests.
- `GET /api/catalog` returns the validated catalog and leaks no secrets.
- `Candidate` shape, the run path, `config_hash`, and `RECEIPT_VERSION` are unchanged.
- `uv run pytest` green; no regressions in existing provider/run tests.
