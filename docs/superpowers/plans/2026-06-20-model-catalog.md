# Model Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a bundled `provider → model → capabilities` catalog (schema + data + loader + read-only endpoint) and consolidate the scattered default-model constants to read from it, with identical runtime behavior.

**Architecture:** A new `orionfold.catalog` package mirrors the existing `orionfold.data` datasets pattern: a bundled `catalog.json`, a Pydantic schema (`ModelCatalog → CatalogProvider → CatalogModel → ModelPricing`), and a cached `load_catalog()` loader. A `default_model_for(provider_id)` helper becomes the single source of truth for per-provider default models; the provider registry calls it instead of literal constants. A read-only `GET /api/catalog` endpoint surfaces the catalog for later sub-projects (#2 model picker, #3 recipes) to consume. Nothing consumes the new capability fields yet except the endpoint.

**Tech Stack:** Python 3.12+, Pydantic v2, FastAPI, `importlib.resources`, pytest, `uv`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-20-model-catalog-design.md`. Every task implicitly inherits its requirements.
- **No provenance impact:** `config_hash` (`src/orionfold/proof/engine.py`) and `RECEIPT_VERSION` (`src/orionfold/receipts/export.py`) MUST remain untouched. The `Candidate` model and the run path MUST be unchanged.
- **Behavior-preserving consolidation:** per-provider default models after consolidation MUST equal today's values, and env override precedence (`ORIONFOLD_<P>_MODEL` env/`.env.local` > catalog default) MUST be preserved exactly.
- **Current default models (the regression target):** `openai → gpt-4o-mini`, `openrouter → openai/gpt-4o-mini`, `lmstudio → local-model`, `ollama → llama3.2`, `gemini → gemini-2.5-flash`, `anthropic → claude-haiku-4-5`.
- **Pricing honesty:** every `pricing` block carries `as_of` (ISO date) + `source` (URL). Local models set `pricing: null`, `cost_class: "free"`. Prices are list prices, dated and sourced — never a claim.
- **Secrets:** the catalog contains zero credentials; the endpoint must leak none. Never log/print keys.
- Tests run keyless/offline: `uv run pytest`. No network in unit tests.
- Run from repo root: `/Users/manavsehgal/orionfold-proof-claude`.

---

### Task 1: Catalog schema, bundled data, and cached loader

**Files:**
- Create: `src/orionfold/catalog/__init__.py`
- Create: `src/orionfold/catalog/models.py`
- Create: `src/orionfold/catalog/catalog.json`
- Test: `tests/unit/test_catalog.py`

**Interfaces:**
- Consumes: `orionfold.domain.models.Privacy` (a `Literal["local","cloud"]`).
- Produces:
  - `orionfold.catalog.models.ModelPricing(input_per_mtok: float, output_per_mtok: float, currency: str = "USD", as_of: str, source: str)`
  - `orionfold.catalog.models.CatalogModel(id: str, display_name: str, family: str, tier: Literal["frontier","balanced","economy"], context_window: int | None = None, cost_class: Literal["free","$","$$","$$$"], pricing: ModelPricing | None = None, latest: bool = False, recommended: bool = False)`
  - `orionfold.catalog.models.CatalogProvider(id: str, label: str, privacy: Privacy, default_model: str, models: list[CatalogModel])` — validates `default_model ∈ {m.id}` and unique model ids.
  - `orionfold.catalog.models.ModelCatalog(version: int, as_of: str, providers: list[CatalogProvider])`
  - `orionfold.catalog.load_catalog() -> ModelCatalog` (cached).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_catalog.py`:

```python
"""The bundled model catalog loads, validates, and is internally consistent."""

from __future__ import annotations

from orionfold.catalog import load_catalog
from orionfold.catalog.models import ModelCatalog

# The six real, model-bearing providers the catalog must cover (mocks are excluded —
# they carry model=None and are special-cased in the registry).
_EXPECTED_PROVIDERS = {"openai", "openrouter", "lmstudio", "ollama", "gemini", "anthropic"}


def test_catalog_loads_and_validates():
    catalog = load_catalog()
    assert isinstance(catalog, ModelCatalog)
    assert catalog.version >= 1
    assert catalog.as_of  # non-empty snapshot date


def test_catalog_covers_the_real_providers():
    ids = {p.id for p in load_catalog().providers}
    assert _EXPECTED_PROVIDERS <= ids


def test_default_model_is_one_of_the_listed_models():
    for provider in load_catalog().providers:
        model_ids = {m.id for m in provider.models}
        assert provider.default_model in model_ids, provider.id


def test_model_ids_unique_per_provider():
    for provider in load_catalog().providers:
        ids = [m.id for m in provider.models]
        assert len(ids) == len(set(ids)), provider.id


def test_pricing_blocks_are_dated_and_sourced():
    for provider in load_catalog().providers:
        for model in provider.models:
            if model.pricing is not None:
                assert model.pricing.as_of, f"{provider.id}/{model.id} missing as_of"
                assert model.pricing.source, f"{provider.id}/{model.id} missing source"


def test_local_models_are_free_and_unpriced():
    for provider in load_catalog().providers:
        if provider.privacy == "local":
            for model in provider.models:
                assert model.cost_class == "free", f"{provider.id}/{model.id}"
                assert model.pricing is None, f"{provider.id}/{model.id}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_catalog.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'orionfold.catalog'`.

- [ ] **Step 3: Write the schema**

Create `src/orionfold/catalog/models.py`:

```python
"""Schema for the bundled model catalog (provider → model → capabilities).

The catalog is pre-run *selection* scaffolding — it informs which models to compare. It is NOT
run provenance: it never enters ``config_hash`` or the receipt. Prices are dated, sourced LIST
prices, never a claim the receipt is meant to prove (a measured receipt cost always outranks a
catalog list price downstream).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator

from orionfold.domain.models import Privacy

Tier = Literal["frontier", "balanced", "economy"]
CostClass = Literal["free", "$", "$$", "$$$"]


class ModelPricing(BaseModel):
    input_per_mtok: float  # USD per 1M input tokens — a LIST price, not a claim
    output_per_mtok: float
    currency: str = "USD"
    as_of: str  # ISO date the price was recorded
    source: str  # provider pricing-page URL


class CatalogModel(BaseModel):
    id: str  # exact string sent to the provider API (e.g. "claude-opus-4-8")
    display_name: str
    family: str  # "claude" | "gpt-4o" | "gemini" | "llama" — enables "same family across providers"
    tier: Tier
    context_window: int | None = None
    cost_class: CostClass  # stable selection signal; local = "free"
    pricing: ModelPricing | None = None  # None for local models
    latest: bool = False
    recommended: bool = False


class CatalogProvider(BaseModel):
    id: str  # matches provider registry ids: anthropic, openai, ollama, ...
    label: str
    privacy: Privacy
    default_model: str  # must equal one models[].id (validated)
    models: list[CatalogModel]

    @model_validator(mode="after")
    def _check(self) -> "CatalogProvider":
        ids = [m.id for m in self.models]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate model id in provider {self.id}")
        if self.default_model not in ids:
            raise ValueError(
                f"default_model {self.default_model!r} not in provider {self.id} models"
            )
        return self


class ModelCatalog(BaseModel):
    version: int  # catalog schema version (starts at 1)
    as_of: str  # catalog-wide snapshot date
    providers: list[CatalogProvider]
```

- [ ] **Step 4: Write the loader**

Create `src/orionfold/catalog/__init__.py`:

```python
"""Bundled model catalog — reference data that ships inside the wheel.

Loaded via ``importlib.resources`` (like ``orionfold.data`` datasets) so it resolves identically
from a source checkout or an installed wheel. The data is static for the process lifetime, so the
load is cached.
"""

from __future__ import annotations

import json
from functools import cache
from importlib import resources

from orionfold.catalog.models import ModelCatalog


@cache
def load_catalog() -> ModelCatalog:
    """Load and validate the bundled catalog (cached)."""
    raw = (resources.files("orionfold.catalog") / "catalog.json").read_text("utf-8")
    return ModelCatalog.model_validate(json.loads(raw))
```

- [ ] **Step 5: Write the bundled catalog data**

> Before committing, verify each `input_per_mtok` / `output_per_mtok` against the provider's live pricing page (the `source` URL) and update `as_of` if you change a value. The numbers below are a dated starting point; an evidence-first product must not ship a knowingly-wrong list price.

Create `src/orionfold/catalog/catalog.json`:

```json
{
  "version": 1,
  "as_of": "2026-06-20",
  "providers": [
    {
      "id": "anthropic",
      "label": "Anthropic",
      "privacy": "cloud",
      "default_model": "claude-haiku-4-5",
      "models": [
        {
          "id": "claude-haiku-4-5",
          "display_name": "Claude Haiku 4.5",
          "family": "claude",
          "tier": "economy",
          "context_window": 200000,
          "cost_class": "$",
          "recommended": true,
          "pricing": {
            "input_per_mtok": 1.0,
            "output_per_mtok": 5.0,
            "currency": "USD",
            "as_of": "2026-06-20",
            "source": "https://www.anthropic.com/pricing"
          }
        },
        {
          "id": "claude-sonnet-4-6",
          "display_name": "Claude Sonnet 4.6",
          "family": "claude",
          "tier": "balanced",
          "context_window": 200000,
          "cost_class": "$$",
          "pricing": {
            "input_per_mtok": 3.0,
            "output_per_mtok": 15.0,
            "currency": "USD",
            "as_of": "2026-06-20",
            "source": "https://www.anthropic.com/pricing"
          }
        },
        {
          "id": "claude-opus-4-8",
          "display_name": "Claude Opus 4.8",
          "family": "claude",
          "tier": "frontier",
          "context_window": 200000,
          "cost_class": "$$$",
          "latest": true,
          "pricing": {
            "input_per_mtok": 15.0,
            "output_per_mtok": 75.0,
            "currency": "USD",
            "as_of": "2026-06-20",
            "source": "https://www.anthropic.com/pricing"
          }
        }
      ]
    },
    {
      "id": "openai",
      "label": "OpenAI",
      "privacy": "cloud",
      "default_model": "gpt-4o-mini",
      "models": [
        {
          "id": "gpt-4o-mini",
          "display_name": "GPT-4o mini",
          "family": "gpt-4o",
          "tier": "economy",
          "context_window": 128000,
          "cost_class": "$",
          "recommended": true,
          "pricing": {
            "input_per_mtok": 0.15,
            "output_per_mtok": 0.6,
            "currency": "USD",
            "as_of": "2026-06-20",
            "source": "https://openai.com/api/pricing/"
          }
        },
        {
          "id": "gpt-4o",
          "display_name": "GPT-4o",
          "family": "gpt-4o",
          "tier": "balanced",
          "context_window": 128000,
          "cost_class": "$$",
          "pricing": {
            "input_per_mtok": 2.5,
            "output_per_mtok": 10.0,
            "currency": "USD",
            "as_of": "2026-06-20",
            "source": "https://openai.com/api/pricing/"
          }
        }
      ]
    },
    {
      "id": "gemini",
      "label": "Gemini",
      "privacy": "cloud",
      "default_model": "gemini-2.5-flash",
      "models": [
        {
          "id": "gemini-2.5-flash",
          "display_name": "Gemini 2.5 Flash",
          "family": "gemini",
          "tier": "economy",
          "context_window": 1000000,
          "cost_class": "$",
          "recommended": true,
          "pricing": {
            "input_per_mtok": 0.3,
            "output_per_mtok": 2.5,
            "currency": "USD",
            "as_of": "2026-06-20",
            "source": "https://ai.google.dev/gemini-api/docs/pricing"
          }
        },
        {
          "id": "gemini-2.5-pro",
          "display_name": "Gemini 2.5 Pro",
          "family": "gemini",
          "tier": "frontier",
          "context_window": 1000000,
          "cost_class": "$$",
          "latest": true,
          "pricing": {
            "input_per_mtok": 1.25,
            "output_per_mtok": 10.0,
            "currency": "USD",
            "as_of": "2026-06-20",
            "source": "https://ai.google.dev/gemini-api/docs/pricing"
          }
        }
      ]
    },
    {
      "id": "openrouter",
      "label": "OpenRouter",
      "privacy": "cloud",
      "default_model": "openai/gpt-4o-mini",
      "models": [
        {
          "id": "openai/gpt-4o-mini",
          "display_name": "GPT-4o mini (via OpenRouter)",
          "family": "gpt-4o",
          "tier": "economy",
          "context_window": 128000,
          "cost_class": "$",
          "recommended": true,
          "pricing": {
            "input_per_mtok": 0.15,
            "output_per_mtok": 0.6,
            "currency": "USD",
            "as_of": "2026-06-20",
            "source": "https://openrouter.ai/models"
          }
        },
        {
          "id": "anthropic/claude-haiku-4-5",
          "display_name": "Claude Haiku 4.5 (via OpenRouter)",
          "family": "claude",
          "tier": "economy",
          "context_window": 200000,
          "cost_class": "$",
          "pricing": {
            "input_per_mtok": 1.0,
            "output_per_mtok": 5.0,
            "currency": "USD",
            "as_of": "2026-06-20",
            "source": "https://openrouter.ai/models"
          }
        },
        {
          "id": "meta-llama/llama-3.3-70b-instruct",
          "display_name": "Llama 3.3 70B Instruct (via OpenRouter)",
          "family": "llama",
          "tier": "balanced",
          "context_window": 128000,
          "cost_class": "$",
          "pricing": {
            "input_per_mtok": 0.12,
            "output_per_mtok": 0.3,
            "currency": "USD",
            "as_of": "2026-06-20",
            "source": "https://openrouter.ai/models"
          }
        }
      ]
    },
    {
      "id": "ollama",
      "label": "Ollama",
      "privacy": "local",
      "default_model": "llama3.2",
      "models": [
        {
          "id": "llama3.2",
          "display_name": "Llama 3.2 (local)",
          "family": "llama",
          "tier": "economy",
          "context_window": 128000,
          "cost_class": "free",
          "recommended": true,
          "pricing": null
        },
        {
          "id": "llama3.3",
          "display_name": "Llama 3.3 (local)",
          "family": "llama",
          "tier": "balanced",
          "context_window": 128000,
          "cost_class": "free",
          "pricing": null
        }
      ]
    },
    {
      "id": "lmstudio",
      "label": "LM Studio",
      "privacy": "local",
      "default_model": "local-model",
      "models": [
        {
          "id": "local-model",
          "display_name": "Loaded LM Studio model",
          "family": "unknown",
          "tier": "economy",
          "context_window": null,
          "cost_class": "free",
          "recommended": true,
          "pricing": null
        }
      ]
    }
  ]
}
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_catalog.py -v`
Expected: PASS (6 tests).

- [ ] **Step 7: Verify the catalog ships in the wheel (resource resolution)**

Run: `uv run python -c "from importlib import resources; print((resources.files('orionfold.catalog') / 'catalog.json').read_text('utf-8')[:40])"`
Expected: prints the first ~40 chars of the JSON (`{` ... `"version": 1`). Confirms hatchling bundles it under the package, like the datasets. The `packages = ["src/orionfold"]` wheel config already covers `catalog.json` since it lives inside the package, so no `pyproject.toml` change should be needed. Investigate only if this step fails.

- [ ] **Step 8: Commit**

```bash
git add src/orionfold/catalog/ tests/unit/test_catalog.py
git commit -m "feat(catalog): bundled provider→model→capabilities catalog + cached loader

New orionfold.catalog package: ModelCatalog/CatalogProvider/CatalogModel/ModelPricing
schema, a bundled catalog.json (six real providers, curated models, dated+sourced
list prices, local models free/unpriced), and a cached load_catalog(). Mirrors the
datasets pattern. Nothing consumes it yet (endpoint + consolidation follow).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `default_model_for()` + registry consolidation (behavior-preserving)

**Files:**
- Modify: `src/orionfold/catalog/__init__.py` (add `default_model_for`)
- Modify: `src/orionfold/providers/registry.py:29-95` (replace literal default constants with `default_model_for` calls)
- Test: `tests/unit/test_catalog.py` (add consolidation tests), `tests/unit/test_registry.py` (unchanged — must still pass)

**Interfaces:**
- Consumes: `orionfold.catalog.load_catalog()` (Task 1).
- Produces: `orionfold.catalog.default_model_for(provider_id: str) -> str` — returns the catalog `default_model` for a provider; raises `KeyError` if the provider id is absent.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_catalog.py`:

```python
import pytest

from orionfold.catalog import default_model_for

# The behavior-preserving regression target: these are the exact defaults the registry used
# before consolidation. They MUST NOT change.
_CURRENT_DEFAULTS = {
    "openai": "gpt-4o-mini",
    "openrouter": "openai/gpt-4o-mini",
    "lmstudio": "local-model",
    "ollama": "llama3.2",
    "gemini": "gemini-2.5-flash",
    "anthropic": "claude-haiku-4-5",
}


@pytest.mark.parametrize("provider_id,expected", sorted(_CURRENT_DEFAULTS.items()))
def test_default_model_for_matches_current_defaults(provider_id, expected):
    assert default_model_for(provider_id) == expected


def test_default_model_for_unknown_provider_raises():
    with pytest.raises(KeyError):
        default_model_for("does-not-exist")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_catalog.py -k default_model_for -v`
Expected: FAIL — `ImportError: cannot import name 'default_model_for'`.

- [ ] **Step 3: Add `default_model_for` to the loader**

Append to `src/orionfold/catalog/__init__.py`:

```python
def default_model_for(provider_id: str) -> str:
    """The catalog's default model for a provider — the single source of truth.

    Raises ``KeyError`` if the provider id has no catalog entry, so the registry and catalog can
    never silently drift.
    """
    for provider in load_catalog().providers:
        if provider.id == provider_id:
            return provider.default_model
    raise KeyError(f"no catalog entry for provider {provider_id!r}")
```

- [ ] **Step 4: Rewire the registry to source defaults from the catalog**

In `src/orionfold/providers/registry.py`:

Add the import (after the existing `from orionfold.config.keys import has_key, resolve` line):

```python
from orionfold.catalog import default_model_for
```

Delete the three literal constants (lines 29-33):

```python
# Default models per profile. Each is overridable with the matching env / .env.local var so an
# operator can prove a different model without code changes.
_OPENAI_DEFAULT = "gpt-4o-mini"
_OPENROUTER_DEFAULT = "openai/gpt-4o-mini"
_LMSTUDIO_DEFAULT = "local-model"
```

Replace them with a short comment:

```python
# Default models are sourced from the bundled catalog (single source of truth). Each remains
# overridable with the matching env / .env.local var so an operator can prove a different model
# without code changes: ORIONFOLD_<PROVIDER>_MODEL > catalog default.
```

Then update each `resolve(...)` fallback to call `default_model_for(...)`:

- Line ~48 (ollama): `ollama_model = resolve("ORIONFOLD_OLLAMA_MODEL", default_model_for("ollama"))`
- Line ~52 (lmstudio): `lmstudio_model = resolve("ORIONFOLD_LMSTUDIO_MODEL", default_model_for("lmstudio"))`
- Line ~67 (openai): `model = resolve("ORIONFOLD_OPENAI_MODEL", default_model_for("openai"))`
- Line ~79 (openrouter): `model = resolve("ORIONFOLD_OPENROUTER_MODEL", default_model_for("openrouter"))`
- Line ~91 (gemini): `model = resolve("ORIONFOLD_GEMINI_MODEL", default_model_for("gemini"))`
- Line ~94 (anthropic): `model = resolve("ORIONFOLD_ANTHROPIC_MODEL", default_model_for("anthropic"))`

> The provider modules (`ollama.py`, `gemini.py`, `anthropic.py`) keep their own `DEFAULT_MODEL` constants — they are only `__init__` fallbacks for direct instantiation; the registry no longer reads them. Step 5 adds a test that pins them equal to the catalog so they cannot drift.

- [ ] **Step 5: Add a drift-guard test (provider-module constants == catalog)**

Append to `tests/unit/test_catalog.py`:

```python
from orionfold.providers import anthropic as _anthropic
from orionfold.providers import gemini as _gemini
from orionfold.providers import ollama as _ollama


def test_provider_module_defaults_match_catalog():
    # The provider modules' __init__ fallbacks must agree with the catalog so direct
    # instantiation and the registry never diverge.
    assert _ollama.DEFAULT_MODEL == default_model_for("ollama")
    assert _gemini.DEFAULT_MODEL == default_model_for("gemini")
    assert _anthropic.DEFAULT_MODEL == default_model_for("anthropic")
```

- [ ] **Step 6: Run the regression + new tests**

Run: `uv run pytest tests/unit/test_catalog.py tests/unit/test_registry.py -v`
Expected: PASS. In particular `tests/unit/test_registry.py` (unchanged) still passes — the keyless listing is still `{mock_good, mock_bad, ollama, lmstudio}` and `ollama` still carries its default model — proving behavior is preserved.

- [ ] **Step 7: Run the full suite to confirm no regressions**

Run: `uv run pytest -q`
Expected: all green (the prior baseline was 95 passing; this adds catalog tests, removes none).

- [ ] **Step 8: Commit**

```bash
git add src/orionfold/catalog/__init__.py src/orionfold/providers/registry.py tests/unit/test_catalog.py
git commit -m "refactor(providers): source default models from the catalog (single source of truth)

Registry now calls catalog.default_model_for() instead of literal constants; env
override precedence (ORIONFOLD_<P>_MODEL > catalog default) is unchanged. Behavior
preserved — defaults identical, locked by regression + drift-guard tests.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `GET /api/catalog` endpoint

**Files:**
- Modify: `src/orionfold/server/routes.py` (add import + route, near the `get_candidates` route ~line 109)
- Test: `tests/integration/test_proof_api.py` (add a catalog endpoint test)

**Interfaces:**
- Consumes: `orionfold.catalog.load_catalog()` (Task 1), `orionfold.catalog.models.ModelCatalog`.
- Produces: `GET /api/catalog` → `ModelCatalog` (FastAPI serializes the Pydantic model to JSON). Read-only, no params.

- [ ] **Step 1: Write the failing test**

Append to `tests/integration/test_proof_api.py`:

```python
def test_catalog_endpoint_returns_validated_catalog(client):
    resp = client.get("/api/catalog")
    assert resp.status_code == 200
    body = resp.json()

    # Parses back into the schema (shape contract).
    from orionfold.catalog.models import ModelCatalog

    catalog = ModelCatalog.model_validate(body)
    assert catalog.version >= 1

    providers = {p.id: p for p in catalog.providers}
    assert {"anthropic", "openai", "gemini", "openrouter", "ollama", "lmstudio"} <= providers.keys()
    # Privacy boundary is representable (cloud vs local) for the UI/recipes to label.
    assert providers["anthropic"].privacy == "cloud"
    assert providers["ollama"].privacy == "local"


def test_catalog_endpoint_leaks_no_secrets(client, monkeypatch):
    # Even with keys present in the environment, the catalog body must contain no credential-ish
    # strings — it is static reference data with no key fields.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-never-appear-in-catalog")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-never-appear")
    text = client.get("/api/catalog").text
    assert "sk-should-never-appear-in-catalog" not in text
    assert "sk-ant-should-never-appear" not in text
    assert "API_KEY" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_proof_api.py -k catalog -v`
Expected: FAIL — `GET /api/catalog` returns 404 (route not defined).

- [ ] **Step 3: Add the route**

In `src/orionfold/server/routes.py`, add the import alongside the other `orionfold` imports (e.g. after the `from orionfold.proof...` imports):

```python
from orionfold.catalog import load_catalog
from orionfold.catalog.models import ModelCatalog
```

Add the route immediately after the `get_candidates` route (after line ~111):

```python
@router.get("/catalog")
def get_catalog() -> ModelCatalog:
    """The bundled model catalog (provider → model → capabilities). Read-only reference data.

    Consumed by the model picker and decision recipes (later sub-projects). Contains no
    credentials — purely static selection metadata.
    """
    return load_catalog()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/integration/test_proof_api.py -k catalog -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add src/orionfold/server/routes.py tests/integration/test_proof_api.py
git commit -m "feat(api): read-only GET /api/catalog endpoint

Surfaces the bundled model catalog for the upcoming model picker (#4) and decision
recipes (#5). Static reference data; carries no credentials (asserted).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Post-implementation verification

- [ ] `uv run pytest -q` — full suite green.
- [ ] `uv run ruff check src tests` and `uv run pyright` (or the project's configured lint/type commands) — clean.
- [ ] Manual endpoint smoke (optional): `uv run orionfold dev` then `curl -s localhost:<port>/api/catalog | python -m json.tool | head` shows the catalog.
- [ ] Confirm `git status` is clean and `config_hash` / `RECEIPT_VERSION` are untouched (`git diff <base> -- src/orionfold/proof/engine.py src/orionfold/receipts/export.py` is empty).

## Out of scope (next sub-projects)

- #2 model-per-candidate picker UI (consumes `/api/catalog`).
- #3 decision recipes (compose a panel + seed the decision question).
- Inline `.env.local` key entry; receipt-driven catalog re-ranking.
