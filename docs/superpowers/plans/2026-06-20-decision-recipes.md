# Decision Recipes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship named "decision recipes" that pre-fill a coherent candidate panel + decision question from semantic selectors resolved server-side, plus inline `.env.local` key entry to unlock unavailable cloud providers.

**Architecture:** A new `recipes/` package (mirroring `catalog/`) holds a bundled `recipes.json` and a resolver that maps each recipe's selectors onto the live catalog ∩ availability — exactly the merge `providers/selection.py` already performs. Two read-only-shaped endpoints expose it: `GET /api/recipes` (resolved panel, no secrets) and `POST /api/credentials` (writes one key line to `.env.local` via a new atomic writer, never echoing it). The cockpit gains a recipe row above setup and a shared `KeyEntry` component used both on greyed picker groups and on a recipe's unmet banner.

**Tech Stack:** Python 3.12, Pydantic, FastAPI, `importlib.resources`, pytest. Frontend: React, TypeScript, Zod, TanStack Query, Tailwind v4, Vitest, Playwright.

## Global Constraints

- **Provenance untouched:** recipes/resolution are SELECTION metadata only. Do NOT modify `proof/engine.py`, `receipts/export.py`, or `domain/models.py`. `config_hash` and `RECEIPT_VERSION` (3) stay byte-for-byte. Recipes never enter the receipt.
- **Keyless default preserved:** mocks stay pre-selected on load; recipes are opt-in. Recipes only compose real model-bearing composite `provider:model` ids — mocks are not in the catalog, so a recipe can never select a mock (the "mocks stay bare-id" invariant from #4 holds).
- **Secrets:** API keys are NEVER logged, echoed, returned in a response, written to receipts/screenshots, or committed. `.env.local` is gitignored (`.env.*`) and written with mode `0o600`. The credential endpoint accepts only whitelisted provider ids (no arbitrary env writes).
- **Tailwind v4:** CSS vars use the parenthesis shorthand `bg-(--color-x)`, never `bg-[--color-x]`.
- **Test-contract strings unchanged:** heading "Orionfold Proof", "Connected", button copy `Run proof`/`Rerun proof` (lowercase p), regions Leaderboard / Failure cases / Proof Receipt export, "Export Markdown|HTML|JSON".
- **Composite id rule:** a candidate id is `f"{provider_id}:{model_id}"`, split on the FIRST colon (`build_candidates` already does this).
- **Tooling:** Python tests `uv run pytest`; lint `uv run ruff check src tests`; frontend `pnpm --dir web test`, `pnpm --dir web build`; e2e `pnpm --dir web e2e` (rebuild the embed via `bash scripts/build.sh` first). After backend/catalog edits, RESTART `orionfold up` (no hot reload).

## File Structure

**New (backend)**
- `src/orionfold/recipes/__init__.py` — `load_recipes()` (cached), re-exports.
- `src/orionfold/recipes/models.py` — `Selector`, `Recipe`, `RecipeBook` (input schema).
- `src/orionfold/recipes/recipes.json` — the four bundled recipes (ships in the wheel automatically, like `catalog.json`, because it lives inside the package).
- `src/orionfold/recipes/resolution.py` — `resolve_recipes()` + output models `ResolvedSelector`, `UnmetSelector`, `ResolvedRecipe`, `RecipesPanel`.
- `src/orionfold/config/env_file.py` — `set_key_in_env_local(key_name, value)`.

**Modified (backend)**
- `src/orionfold/config/keys.py` — add `CLOUD_KEY_NAMES` whitelist (provider_id → env var NAME).
- `src/orionfold/server/routes.py` — `GET /api/recipes`, `POST /api/credentials`.

**New (frontend)**
- `web/src/features/proof/RecipeRow.tsx`
- `web/src/features/proof/KeyEntry.tsx`

**Modified (frontend)**
- `web/src/lib/api.ts` — recipe types/schemas, `getRecipes`, `setProviderKey`.
- `web/src/features/proof/ProofCockpit.tsx` — recipes query, `activeRecipeId`, `onSelectRecipe`, render `RecipeRow`.
- `web/src/features/proof/CandidatePicker.tsx` — render `KeyEntry` on greyed cloud groups (replace the "coming with recipes" placeholder).
- `web/e2e/proof.spec.ts` — recipe-row assertions.

**Tests**
- `tests/unit/test_recipes.py`, `tests/unit/test_env_file.py`
- `tests/integration/test_recipes_api.py` (recipes + credentials routes)
- `web/src/features/proof/KeyEntry.test.tsx`, `web/src/features/proof/RecipeRow.test.tsx`

---

### Task 1: Recipe schema, bundled JSON, and loader

**Files:**
- Create: `src/orionfold/recipes/models.py`
- Create: `src/orionfold/recipes/recipes.json`
- Create: `src/orionfold/recipes/__init__.py`
- Test: `tests/unit/test_recipes.py`

**Interfaces:**
- Consumes: `orionfold.catalog.Tier`, `orionfold.domain.models.Privacy`.
- Produces: `Selector`, `Recipe`, `RecipeBook` (Pydantic); `load_recipes() -> RecipeBook` (cached).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_recipes.py
"""The bundled recipe book loads and validates; selectors reference legal catalog values."""

from __future__ import annotations

from orionfold.catalog import load_catalog
from orionfold.recipes import load_recipes

LEGAL_TIERS = {"frontier", "balanced", "economy"}
LEGAL_PRIVACY = {"local", "cloud"}


def test_recipe_book_loads_with_four_recipes():
    book = load_recipes()
    ids = [r.id for r in book.recipes]
    assert ids == ["cost-vs-quality", "local-vs-cloud", "cheapest-that-passes", "provider-arbitrage"]
    assert len(ids) == len(set(ids))  # unique


def test_every_recipe_has_a_question_and_selectors():
    for r in load_recipes().recipes:
        assert r.title and r.subtitle and r.decision_question
        assert r.selectors, f"{r.id} has no selectors"
        for s in r.selectors:
            assert s.label
            if s.tier is not None:
                assert s.tier in LEGAL_TIERS
            if s.privacy is not None:
                assert s.privacy in LEGAL_PRIVACY


def test_selector_families_and_providers_exist_in_catalog():
    catalog = load_catalog()
    families = {m.family for p in catalog.providers for m in p.models}
    providers = {p.id for p in catalog.providers}
    for r in load_recipes().recipes:
        for s in r.selectors:
            if s.family is not None:
                assert s.family in families, f"{r.id}: unknown family {s.family}"
            if s.provider is not None:
                assert s.provider in providers, f"{r.id}: unknown provider {s.provider}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_recipes.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'orionfold.recipes'`.

- [ ] **Step 3: Write the schema**

```python
# src/orionfold/recipes/models.py
"""Schema for bundled decision recipes — named comparison presets.

A recipe declares SEMANTIC intent (a family/tier/privacy/provider filter), not hardcoded model
ids, so it resolves against whatever the current environment makes available. Like the catalog,
recipes are pre-run SELECTION scaffolding: they never enter ``config_hash`` or the receipt.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator

from orionfold.catalog import Tier
from orionfold.domain.models import Privacy

PickStrategy = Literal["recommended", "cheapest", "latest"]


class Selector(BaseModel):
    label: str  # human tag shown in the resolved panel, e.g. "Economy", "Cloud frontier"
    family: str | None = None  # catalog family: claude | gpt | gemini | llama
    tier: Tier | None = None
    privacy: Privacy | None = None
    provider: str | None = None  # pin to one provider id (e.g. "ollama")
    pick: PickStrategy = "recommended"


class Recipe(BaseModel):
    id: str
    title: str
    subtitle: str
    decision_question: str
    selectors: list[Selector]

    @model_validator(mode="after")
    def _non_empty(self) -> "Recipe":
        if not self.selectors:
            raise ValueError(f"recipe {self.id} has no selectors")
        return self


class RecipeBook(BaseModel):
    version: int
    recipes: list[Recipe]

    @model_validator(mode="after")
    def _unique_ids(self) -> "RecipeBook":
        ids = [r.id for r in self.recipes]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate recipe id")
        return self
```

- [ ] **Step 4: Write the bundled recipes JSON**

```json
// src/orionfold/recipes/recipes.json
{
  "version": 1,
  "recipes": [
    {
      "id": "cost-vs-quality",
      "title": "Cost vs quality for client summaries",
      "subtitle": "Economy vs frontier of one family",
      "decision_question": "Which model gives me trustworthy client summaries at the lowest cost?",
      "selectors": [
        { "label": "Economy", "family": "claude", "tier": "economy", "pick": "cheapest" },
        { "label": "Frontier", "family": "claude", "tier": "frontier" }
      ]
    },
    {
      "id": "local-vs-cloud",
      "title": "Local vs cloud (privacy)",
      "subtitle": "Private local vs frontier cloud",
      "decision_question": "Can a local model match a frontier cloud model on my task — without sending data out?",
      "selectors": [
        { "label": "Local", "privacy": "local", "tier": "balanced" },
        { "label": "Cloud frontier", "privacy": "cloud", "tier": "frontier", "pick": "cheapest" }
      ]
    },
    {
      "id": "cheapest-that-passes",
      "title": "Cheapest model that still passes",
      "subtitle": "A spread of low-cost models",
      "decision_question": "What's the cheapest model that still passes my bar?",
      "selectors": [
        { "label": "Local", "privacy": "local", "tier": "economy" },
        { "label": "Claude economy", "family": "claude", "tier": "economy" },
        { "label": "GPT economy", "family": "gpt", "tier": "economy" }
      ]
    },
    {
      "id": "provider-arbitrage",
      "title": "Same model, different providers",
      "subtitle": "One model family across providers",
      "decision_question": "Same model, different hosts — who's cheaper and faster for the same quality?",
      "selectors": [
        { "label": "Llama on Ollama", "family": "llama", "provider": "ollama" },
        { "label": "Llama on OpenRouter", "family": "llama", "provider": "openrouter" }
      ]
    }
  ]
}
```

- [ ] **Step 5: Write the loader**

```python
# src/orionfold/recipes/__init__.py
"""Bundled decision recipes — reference data that ships inside the wheel.

Loaded via ``importlib.resources`` (like ``orionfold.catalog``) so it resolves identically from a
source checkout or an installed wheel. Static for the process lifetime, so the load is cached.
"""

from __future__ import annotations

import json
from functools import cache
from importlib import resources

from orionfold.recipes.models import Recipe, RecipeBook, Selector

__all__ = ["Recipe", "RecipeBook", "Selector", "load_recipes"]


@cache
def load_recipes() -> RecipeBook:
    """Load and validate the bundled recipe book (cached)."""
    raw = (resources.files("orionfold.recipes") / "recipes.json").read_text("utf-8")
    return RecipeBook.model_validate(json.loads(raw))
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_recipes.py -v`
Expected: PASS (3 tests).

- [ ] **Step 7: Lint + commit**

```bash
uv run ruff check src tests
git add src/orionfold/recipes tests/unit/test_recipes.py
git commit -m "feat(recipes): bundled recipe schema + book loader"
```

---

### Task 2: The selector resolver

**Files:**
- Modify: `src/orionfold/recipes/resolution.py` (create)
- Test: `tests/unit/test_recipes.py` (append resolver tests)

**Interfaces:**
- Consumes: `load_recipes()`, `load_catalog()`, `orionfold.providers.registry._build`, `Selector`/`Recipe`.
- Produces:
  - `ResolvedSelector(label, candidate_id, display_name, provider_id, cost_class)`
  - `UnmetSelector(label, needs_provider_id, needs_provider_label, key_name)`
  - `ResolvedRecipe(id, title, subtitle, decision_question, candidate_ids: list[str], resolved: list[ResolvedSelector], unmet: list[UnmetSelector])`
  - `RecipesPanel(recipes: list[ResolvedRecipe])`
  - `resolve_recipes() -> RecipesPanel`

Resolution rules (per selector, in order):
1. Filter catalog `(provider, model)` rows by every present constraint (`family`, `tier`, `privacy` from the provider, `provider` id).
2. Partition into **available** (provider id in `set(_build())`) and **unavailable**.
3. If any available: pick by `pick` — `recommended`: first `m.recommended`, else first `m.latest`, else cheapest by `pricing.input_per_mtok` (None price last), else first; `cheapest`: lowest `pricing.input_per_mtok` (local/no-price = 0.0); `latest`: first `m.latest` else first. Emit `ResolvedSelector`.
4. Else if any unavailable: choose the cheapest unavailable by `input_per_mtok` (None last) → emit `UnmetSelector` with that provider's `key_name` from `CLOUD_KEY_NAMES`.
5. Else (no catalog match): skip the selector.
`candidate_ids` = resolved candidate ids in order, de-duplicated.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_recipes.py  (append)

import pytest

from orionfold.recipes.resolution import resolve_recipes


@pytest.fixture()
def keyless(tmp_path, monkeypatch):
    """Clean env: no cloud keys, .env.local confined to an empty tmp dir."""
    monkeypatch.chdir(tmp_path)
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def _recipe(panel, rid):
    return next(r for r in panel.recipes if r.id == rid)


def test_keyless_local_selectors_resolve_cloud_selectors_unmet(keyless):
    panel = resolve_recipes()
    arb = _recipe(panel, "provider-arbitrage")
    # "Llama on Ollama" is local + keyless => resolved; "Llama on OpenRouter" => unmet.
    resolved_labels = {s.label for s in arb.resolved}
    unmet_labels = {s.label for s in arb.unmet}
    assert "Llama on Ollama" in resolved_labels
    assert "Llama on OpenRouter" in unmet_labels
    ollama = next(s for s in arb.resolved if s.label == "Llama on Ollama")
    assert ollama.candidate_id.startswith("ollama:")
    assert ollama.candidate_id in arb.candidate_ids


def test_keyless_cost_vs_quality_is_fully_unmet(keyless):
    panel = resolve_recipes()
    cvq = _recipe(panel, "cost-vs-quality")
    assert cvq.candidate_ids == []  # both selectors target Anthropic, which has no key
    assert {s.key_name for s in cvq.unmet} == {"ANTHROPIC_API_KEY"}


def test_cost_vs_quality_resolves_with_anthropic_key(keyless, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    cvq = _recipe(resolve_recipes(), "cost-vs-quality")
    assert cvq.unmet == []
    assert len(cvq.candidate_ids) == 2
    assert all(cid.startswith("anthropic:") for cid in cvq.candidate_ids)


def test_panel_carries_no_key_values(keyless, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "super-secret-value")
    dumped = resolve_recipes().model_dump_json()
    assert "super-secret-value" not in dumped
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_recipes.py -k "keyless or anthropic or key_values" -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'orionfold.recipes.resolution'`.

- [ ] **Step 3: Implement the resolver**

```python
# src/orionfold/recipes/resolution.py
"""Resolve recipe selectors against the live catalog ∩ availability.

Pure SELECTION metadata: mirrors ``providers.selection`` (catalog + ``_build()`` availability).
Carries no credentials — only provider labels, model ids, and the env-var NAME a provider needs.
"""

from __future__ import annotations

from pydantic import BaseModel

from orionfold.catalog import CostClass, load_catalog
from orionfold.catalog.models import CatalogModel, CatalogProvider
from orionfold.config.keys import CLOUD_KEY_NAMES
from orionfold.providers.registry import _build
from orionfold.recipes import Recipe, Selector, load_recipes


class ResolvedSelector(BaseModel):
    label: str
    candidate_id: str
    display_name: str
    provider_id: str
    cost_class: CostClass


class UnmetSelector(BaseModel):
    label: str
    needs_provider_id: str
    needs_provider_label: str
    key_name: str


class ResolvedRecipe(BaseModel):
    id: str
    title: str
    subtitle: str
    decision_question: str
    candidate_ids: list[str]
    resolved: list[ResolvedSelector]
    unmet: list[UnmetSelector]


class RecipesPanel(BaseModel):
    recipes: list[ResolvedRecipe]


def _price(model: CatalogModel) -> float | None:
    return model.pricing.input_per_mtok if model.pricing else None


def _matches(selector: Selector, provider: CatalogProvider, model: CatalogModel) -> bool:
    if selector.family is not None and model.family != selector.family:
        return False
    if selector.tier is not None and model.tier != selector.tier:
        return False
    if selector.privacy is not None and provider.privacy != selector.privacy:
        return False
    if selector.provider is not None and provider.id != selector.provider:
        return False
    return True


def _pick(selector: Selector, rows: list[tuple[CatalogProvider, CatalogModel]]):
    if selector.pick == "cheapest":
        return min(rows, key=lambda r: _price(r[1]) if _price(r[1]) is not None else 0.0)
    if selector.pick == "latest":
        return next((r for r in rows if r[1].latest), rows[0])
    # "recommended": recommended flag, then latest, then cheapest, then first.
    for r in rows:
        if r[1].recommended:
            return r
    for r in rows:
        if r[1].latest:
            return r
    priced = [r for r in rows if _price(r[1]) is not None]
    if priced:
        return min(priced, key=lambda r: _price(r[1]))
    return rows[0]


def _resolve_one(selector: Selector, available: set[str]):
    catalog = load_catalog()
    matches = [
        (p, m) for p in catalog.providers for m in p.models if _matches(selector, p, m)
    ]
    if not matches:
        return None  # selector references something the catalog no longer carries — skip
    avail = [r for r in matches if r[0].id in available]
    if avail:
        provider, model = _pick(selector, avail)
        return ResolvedSelector(
            label=selector.label,
            candidate_id=f"{provider.id}:{model.id}",
            display_name=model.display_name,
            provider_id=provider.id,
            cost_class=model.cost_class,
        )
    # Unmet: suggest the cheapest unavailable match's provider (must be a known cloud key).
    cloud = [r for r in matches if r[0].id in CLOUD_KEY_NAMES]
    if not cloud:
        return None
    provider, _ = min(
        cloud, key=lambda r: _price(r[1]) if _price(r[1]) is not None else float("inf")
    )
    return UnmetSelector(
        label=selector.label,
        needs_provider_id=provider.id,
        needs_provider_label=provider.label,
        key_name=CLOUD_KEY_NAMES[provider.id],
    )


def _resolve_recipe(recipe: Recipe, available: set[str]) -> ResolvedRecipe:
    resolved: list[ResolvedSelector] = []
    unmet: list[UnmetSelector] = []
    for selector in recipe.selectors:
        outcome = _resolve_one(selector, available)
        if isinstance(outcome, ResolvedSelector):
            resolved.append(outcome)
        elif isinstance(outcome, UnmetSelector):
            unmet.append(outcome)
    seen: set[str] = set()
    candidate_ids: list[str] = []
    for s in resolved:
        if s.candidate_id not in seen:
            seen.add(s.candidate_id)
            candidate_ids.append(s.candidate_id)
    return ResolvedRecipe(
        id=recipe.id,
        title=recipe.title,
        subtitle=recipe.subtitle,
        decision_question=recipe.decision_question,
        candidate_ids=candidate_ids,
        resolved=resolved,
        unmet=unmet,
    )


def resolve_recipes() -> RecipesPanel:
    """Resolve every bundled recipe for the current environment."""
    available = set(_build())
    return RecipesPanel(
        recipes=[_resolve_recipe(r, available) for r in load_recipes().recipes]
    )
```

- [ ] **Step 4: Add the `CLOUD_KEY_NAMES` whitelist (dependency of this task)**

Add to the end of `src/orionfold/config/keys.py`:

```python
# The four cloud providers that resolve on a key, mapped to their env-var NAME. Single source of
# truth for both the registry's availability gate and the credential-entry whitelist. Local
# providers (ollama, lmstudio) and mocks are deliberately absent — they need no key, and the
# credential endpoint rejects any provider id not in this map (no arbitrary env writes).
CLOUD_KEY_NAMES: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_recipes.py -v`
Expected: PASS (all recipe tests, including the new resolver ones).

- [ ] **Step 6: Lint + commit**

```bash
uv run ruff check src tests
git add src/orionfold/recipes/resolution.py src/orionfold/config/keys.py tests/unit/test_recipes.py
git commit -m "feat(recipes): semantic selector resolver over catalog + availability"
```

---

### Task 3: The `.env.local` writer

**Files:**
- Create: `src/orionfold/config/env_file.py`
- Test: `tests/unit/test_env_file.py`

**Interfaces:**
- Consumes: `orionfold.config.keys._env_local_path` (reuse path-finding); `ORIONFOLD_ENV_FILE` override.
- Produces: `set_key_in_env_local(key_name: str, value: str) -> Path` (returns the written path).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_env_file.py
"""The .env.local writer updates one key line atomically, preserving everything else, 0o600,
and never surfacing the value. Confined to a tmp dir via ORIONFOLD_ENV_FILE."""

from __future__ import annotations

import stat

import pytest

from orionfold.config import keys
from orionfold.config.env_file import set_key_in_env_local


@pytest.fixture()
def env_path(tmp_path, monkeypatch):
    path = tmp_path / ".env.local"
    monkeypatch.setenv("ORIONFOLD_ENV_FILE", str(path))
    return path


def test_creates_file_with_the_key_and_strict_perms(env_path):
    returned = set_key_in_env_local("ANTHROPIC_API_KEY", "abc123")
    assert returned == env_path
    assert env_path.read_text() == "ANTHROPIC_API_KEY=abc123\n"
    mode = stat.S_IMODE(env_path.stat().st_mode)
    assert mode == 0o600


def test_resolves_after_write(env_path):
    set_key_in_env_local("ANTHROPIC_API_KEY", "abc123")
    # ORIONFOLD_ENV_FILE points keys.resolve_key at the same file.
    assert keys.resolve_key("ANTHROPIC_API_KEY") == "abc123"


def test_updates_existing_key_and_preserves_other_lines(env_path):
    env_path.write_text(
        "# my keys\nOPENAI_API_KEY=keep-me\nANTHROPIC_API_KEY=old\nOLLAMA_HOST=http://box\n"
    )
    set_key_in_env_local("ANTHROPIC_API_KEY", "new")
    text = env_path.read_text()
    assert "ANTHROPIC_API_KEY=new\n" in text
    assert "ANTHROPIC_API_KEY=old" not in text
    assert "OPENAI_API_KEY=keep-me\n" in text
    assert "OLLAMA_HOST=http://box\n" in text
    assert "# my keys\n" in text


def test_appends_when_key_absent(env_path):
    env_path.write_text("OPENAI_API_KEY=keep-me\n")
    set_key_in_env_local("GEMINI_API_KEY", "g")
    text = env_path.read_text()
    assert "OPENAI_API_KEY=keep-me\n" in text
    assert "GEMINI_API_KEY=g\n" in text


def test_return_value_carries_no_secret(env_path):
    returned = set_key_in_env_local("ANTHROPIC_API_KEY", "topsecret")
    assert "topsecret" not in str(returned)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_env_file.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'orionfold.config.env_file'`.

- [ ] **Step 3: Implement the writer**

```python
# src/orionfold/config/env_file.py
"""Write a single credential line into a repo-root ``.env.local`` (ADR-0002).

Used by the inline key-entry flow. The write is atomic (temp file + ``os.replace``), preserves
every other line/comment, and sets ``0o600`` because the file holds secrets. The value is never
logged or returned — callers receive only the path written.
"""

from __future__ import annotations

import os
from pathlib import Path

from orionfold.config.keys import _ENV_FILE_OVERRIDE, _ENV_LOCAL_FILENAME, _env_local_path


def _target_path() -> Path:
    """Where to write: the explicit override, an existing discovered file, else ``./``."""
    override = os.environ.get(_ENV_FILE_OVERRIDE)
    if override:
        return Path(override)
    existing = _env_local_path()
    return existing if existing is not None else Path.cwd() / _ENV_LOCAL_FILENAME


def set_key_in_env_local(key_name: str, value: str) -> Path:
    """Insert or replace ``key_name=value`` in ``.env.local``; return the path written."""
    path = _target_path()
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    new_line = f"{key_name}={value}"
    replaced = False
    out: list[str] = []
    for raw in lines:
        stripped = raw.strip()
        body = stripped[len("export ") :].strip() if stripped.startswith("export ") else stripped
        if body.partition("=")[0].strip() == key_name:
            out.append(new_line)
            replaced = True
        else:
            out.append(raw)
    if not replaced:
        out.append(new_line)

    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text("\n".join(out) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    return path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_env_file.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Lint + commit**

```bash
uv run ruff check src tests
git add src/orionfold/config/env_file.py tests/unit/test_env_file.py
git commit -m "feat(config): atomic .env.local single-key writer (0600, value never surfaced)"
```

---

### Task 4: API routes — `GET /api/recipes` + `POST /api/credentials`

**Files:**
- Modify: `src/orionfold/server/routes.py`
- Test: `tests/integration/test_recipes_api.py`

**Interfaces:**
- Consumes: `resolve_recipes`, `RecipesPanel`, `set_key_in_env_local`, `CLOUD_KEY_NAMES`, `has_key`.
- Produces: `GET /api/recipes -> RecipesPanel`; `POST /api/credentials` body `{provider_id, key}` → `{provider_id, available}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_recipes_api.py
"""The recipes panel + inline credential endpoint. Keys stay in a tmp .env.local and are never
echoed back."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orionfold.server.app import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Confine .env.local to tmp and clear ambient keys so the panel is hermetic.
    monkeypatch.setenv("ORIONFOLD_ENV_FILE", str(tmp_path / ".env.local"))
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    app = create_app(db_path=tmp_path / "proof.db")
    with TestClient(app) as c:  # triggers lifespan: migrate + seed
        yield c


def test_recipes_panel_shape(client):
    body = client.get("/api/recipes").json()
    ids = [r["id"] for r in body["recipes"]]
    assert "cost-vs-quality" in ids
    cvq = next(r for r in body["recipes"] if r["id"] == "cost-vs-quality")
    assert cvq["candidate_ids"] == []  # keyless => fully unmet
    assert cvq["unmet"][0]["key_name"] == "ANTHROPIC_API_KEY"


def test_credentials_writes_and_flips_availability(client):
    before = client.get("/api/recipes").json()
    cvq_before = next(r for r in before["recipes"] if r["id"] == "cost-vs-quality")
    assert cvq_before["candidate_ids"] == []

    res = client.post("/api/credentials", json={"provider_id": "anthropic", "key": "sk-ant-xyz"})
    assert res.status_code == 200
    data = res.json()
    assert data == {"provider_id": "anthropic", "available": True}
    assert "sk-ant-xyz" not in res.text  # never echoed

    after = client.get("/api/recipes").json()
    cvq_after = next(r for r in after["recipes"] if r["id"] == "cost-vs-quality")
    assert len(cvq_after["candidate_ids"]) == 2  # now resolves


def test_credentials_rejects_unknown_provider(client):
    assert client.post("/api/credentials", json={"provider_id": "ollama", "key": "x"}).status_code == 400
    assert client.post("/api/credentials", json={"provider_id": "mock_good", "key": "x"}).status_code == 400


def test_credentials_rejects_empty_key(client):
    assert client.post("/api/credentials", json={"provider_id": "anthropic", "key": "  "}).status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_recipes_api.py -v`
Expected: FAIL (404 on `/api/recipes` — route not defined yet).

- [ ] **Step 3: Add imports + the routes**

Add to the imports in `src/orionfold/server/routes.py`:

```python
from orionfold.config.env_file import set_key_in_env_local
from orionfold.config.keys import CLOUD_KEY_NAMES, has_key
from orionfold.recipes.resolution import RecipesPanel, resolve_recipes
```

Add the request model near the other `BaseModel`s (after `RunRequest`):

```python
class CredentialRequest(BaseModel):
    provider_id: str
    key: str


class CredentialStatus(BaseModel):
    provider_id: str
    available: bool
```

Add the routes after `get_selection` (near line 138):

```python
@router.get("/recipes")
def get_recipes() -> RecipesPanel:
    """Named decision recipes, resolved against the current environment (catalog ∩ availability).

    Read-only SELECTION metadata: provider labels, model ids, and the env-var NAME a provider
    needs — never a key value, never run provenance.
    """
    return resolve_recipes()


@router.post("/credentials")
def set_credential(body: CredentialRequest) -> CredentialStatus:
    """Write one cloud provider's API key into .env.local so its candidates unlock.

    Whitelisted to the four cloud providers (no arbitrary env writes). The key is written to a
    git-ignored 0o600 file and is NEVER logged or echoed in the response.
    """
    key_name = CLOUD_KEY_NAMES.get(body.provider_id)
    if key_name is None:
        raise HTTPException(status_code=400, detail=f"Unknown cloud provider: {body.provider_id}")
    if not body.key.strip():
        raise HTTPException(status_code=422, detail="Key must not be empty")
    set_key_in_env_local(key_name, body.key.strip())
    return CredentialStatus(provider_id=body.provider_id, available=has_key(key_name))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_recipes_api.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Full backend suite + lint + commit**

```bash
uv run pytest -q
uv run ruff check src tests
git add src/orionfold/server/routes.py tests/integration/test_recipes_api.py
git commit -m "feat(api): GET /api/recipes + POST /api/credentials (key never echoed)"
```

Expected: full suite green (prior 129 + the new recipe/env/api tests).

---

### Task 5: Frontend API client — recipe types + `setProviderKey`

**Files:**
- Modify: `web/src/lib/api.ts`
- Test: `web/src/lib/api.recipes.test.ts` (create)

**Interfaces:**
- Produces: types `ResolvedSelector`, `UnmetSelector`, `ResolvedRecipe`, `RecipesPanel`; `getRecipes(): Promise<RecipesPanel>`; `setProviderKey(providerId: string, key: string): Promise<{provider_id: string; available: boolean}>`.

- [ ] **Step 1: Write the failing test**

```ts
// web/src/lib/api.recipes.test.ts
import { describe, expect, it } from "vitest";
import { recipesPanelSchema } from "./api";

describe("recipesPanelSchema", () => {
  it("parses a resolved recipe with candidate ids and unmet selectors", () => {
    const panel = recipesPanelSchema.parse({
      recipes: [
        {
          id: "cost-vs-quality",
          title: "Cost vs quality",
          subtitle: "Economy vs frontier",
          decision_question: "Which model?",
          candidate_ids: ["anthropic:claude-haiku-4-5"],
          resolved: [
            {
              label: "Economy",
              candidate_id: "anthropic:claude-haiku-4-5",
              display_name: "Claude Haiku 4.5",
              provider_id: "anthropic",
              cost_class: "$",
            },
          ],
          unmet: [
            {
              label: "Frontier",
              needs_provider_id: "anthropic",
              needs_provider_label: "Anthropic",
              key_name: "ANTHROPIC_API_KEY",
            },
          ],
        },
      ],
    });
    expect(panel.recipes[0].candidate_ids).toEqual(["anthropic:claude-haiku-4-5"]);
    expect(panel.recipes[0].unmet[0].key_name).toBe("ANTHROPIC_API_KEY");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test -- api.recipes`
Expected: FAIL (`recipesPanelSchema` is not exported).

- [ ] **Step 3: Add schemas + client functions**

Append to `web/src/lib/api.ts` (after the selection schemas, before `getSelection`'s neighbors as convenient):

```ts
export const resolvedSelectorSchema = z.object({
  label: z.string(),
  candidate_id: z.string(),
  display_name: z.string(),
  provider_id: z.string(),
  cost_class: z.enum(["free", "$", "$$", "$$$"]),
});
export type ResolvedSelector = z.infer<typeof resolvedSelectorSchema>;

export const unmetSelectorSchema = z.object({
  label: z.string(),
  needs_provider_id: z.string(),
  needs_provider_label: z.string(),
  key_name: z.string(),
});
export type UnmetSelector = z.infer<typeof unmetSelectorSchema>;

export const resolvedRecipeSchema = z.object({
  id: z.string(),
  title: z.string(),
  subtitle: z.string(),
  decision_question: z.string(),
  candidate_ids: z.array(z.string()),
  resolved: z.array(resolvedSelectorSchema),
  unmet: z.array(unmetSelectorSchema),
});
export type ResolvedRecipe = z.infer<typeof resolvedRecipeSchema>;

export const recipesPanelSchema = z.object({ recipes: z.array(resolvedRecipeSchema) });
export type RecipesPanel = z.infer<typeof recipesPanelSchema>;

export function getRecipes(): Promise<RecipesPanel> {
  return getJson("/api/recipes", recipesPanelSchema);
}

const credentialStatusSchema = z.object({ provider_id: z.string(), available: z.boolean() });

export async function setProviderKey(
  providerId: string,
  key: string,
): Promise<z.infer<typeof credentialStatusSchema>> {
  const res = await fetch("/api/credentials", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ provider_id: providerId, key }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Saving the key failed (HTTP ${res.status})`);
  }
  return credentialStatusSchema.parse(await res.json());
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --dir web test -- api.recipes`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/api.ts web/src/lib/api.recipes.test.ts
git commit -m "feat(web): recipes API client types + setProviderKey"
```

---

### Task 6: `KeyEntry` — the shared inline key-entry component

**Files:**
- Create: `web/src/features/proof/KeyEntry.tsx`
- Test: `web/src/features/proof/KeyEntry.test.tsx`

**Interfaces:**
- Consumes: `setProviderKey` (mockable), TanStack Query `useQueryClient`.
- Produces: `KeyEntry({ providerId, providerLabel, keyName }: { providerId: string; providerLabel: string; keyName: string })`. On success invalidates `["selection"]` and `["recipes"]`; clears the field.

Mirror `CandidatePicker`'s `CustomChip`: a `div` (NOT a form), button `type="button"`, Enter handled with `preventDefault`/`stopPropagation`, so it never submits the outer `RunSetup` `<form>` (the #4 nested-form regression).

- [ ] **Step 1: Write the failing test**

```tsx
// web/src/features/proof/KeyEntry.test.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { KeyEntry } from "./KeyEntry";
import * as api from "../../lib/api";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient();
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

afterEach(() => vi.restoreAllMocks());

describe("KeyEntry", () => {
  it("submits the typed key to setProviderKey", async () => {
    const spy = vi
      .spyOn(api, "setProviderKey")
      .mockResolvedValue({ provider_id: "anthropic", available: true });
    wrap(<KeyEntry providerId="anthropic" providerLabel="Anthropic" keyName="ANTHROPIC_API_KEY" />);
    fireEvent.click(screen.getByRole("button", { name: /add key/i }));
    fireEvent.change(screen.getByLabelText(/anthropic api key/i), {
      target: { value: "sk-ant-xyz" },
    });
    fireEvent.click(screen.getByRole("button", { name: /save key/i }));
    await waitFor(() => expect(spy).toHaveBeenCalledWith("anthropic", "sk-ant-xyz"));
  });

  it("does not submit an outer form when Save is clicked or Enter pressed", () => {
    vi.spyOn(api, "setProviderKey").mockResolvedValue({ provider_id: "anthropic", available: true });
    const onSubmit = vi.fn((e: React.FormEvent) => e.preventDefault());
    wrap(
      <form aria-label="outer" onSubmit={onSubmit}>
        <KeyEntry providerId="anthropic" providerLabel="Anthropic" keyName="ANTHROPIC_API_KEY" />
      </form>,
    );
    fireEvent.click(screen.getByRole("button", { name: /add key/i }));
    const field = screen.getByLabelText(/anthropic api key/i);
    fireEvent.keyDown(field, { key: "Enter" });
    fireEvent.click(screen.getByRole("button", { name: /save key/i }));
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test -- KeyEntry`
Expected: FAIL (`KeyEntry` not found).

- [ ] **Step 3: Implement `KeyEntry`**

```tsx
// web/src/features/proof/KeyEntry.tsx
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { setProviderKey } from "../../lib/api";

// Inline key entry for an unavailable cloud provider. The key is written to .env.local server-side
// (never echoed); on success we invalidate selection + recipes so availability flips live.
// Nested-form-safe (the #4 lesson): a div, type="button", and Enter handled locally — it must NOT
// submit the surrounding RunSetup <form>. The value lives only in local state and clears on success.
export function KeyEntry({
  providerId,
  providerLabel,
  keyName,
}: {
  providerId: string;
  providerLabel: string;
  keyName: string;
}) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");

  const mutation = useMutation({
    mutationFn: (key: string) => setProviderKey(providerId, key),
    onSuccess: () => {
      setValue("");
      setOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["selection"] });
      void queryClient.invalidateQueries({ queryKey: ["recipes"] });
    },
  });

  function submit() {
    const key = value.trim();
    if (key) mutation.mutate(key);
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-lg border border-dashed border-(--color-panel-line) px-3 py-2 text-xs text-(--color-ink-muted) hover:border-(--color-panel-line-strong)"
      >
        Add key
      </button>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <input
        autoFocus
        type="password"
        autoComplete="off"
        aria-label={`${providerLabel} API key`}
        placeholder={keyName}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            e.stopPropagation();
            submit();
          } else if (e.key === "Escape") {
            setValue("");
            setOpen(false);
          }
        }}
        className="w-52 rounded-lg border border-(--color-panel-line) bg-(--color-panel) px-2 py-1.5 text-(--color-ink)"
      />
      <button
        type="button"
        onClick={submit}
        disabled={mutation.isPending}
        className="rounded-lg bg-(--color-accent-strong) px-2 py-1.5 text-(--color-accent-ink) disabled:opacity-40"
      >
        Save key
      </button>
      {mutation.isError ? (
        <span role="alert" className="text-xs text-rose-300">
          Could not save the key.
        </span>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --dir web test -- KeyEntry`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add web/src/features/proof/KeyEntry.tsx web/src/features/proof/KeyEntry.test.tsx
git commit -m "feat(web): shared KeyEntry component (nested-form-safe, key never lifted)"
```

---

### Task 7: `RecipeRow` — the recipe card row

**Files:**
- Create: `web/src/features/proof/RecipeRow.tsx`
- Test: `web/src/features/proof/RecipeRow.test.tsx`

**Interfaces:**
- Consumes: `RecipesPanel`, `ResolvedRecipe` (types), `KeyEntry`.
- Produces: `RecipeRow({ panel, activeRecipeId, onSelectRecipe }: { panel: RecipesPanel; activeRecipeId: string | null; onSelectRecipe: (r: ResolvedRecipe) => void })`.

- [ ] **Step 1: Write the failing test**

```tsx
// web/src/features/proof/RecipeRow.test.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RecipeRow } from "./RecipeRow";
import type { RecipesPanel } from "../../lib/api";

const PANEL: RecipesPanel = {
  recipes: [
    {
      id: "provider-arbitrage",
      title: "Same model, different providers",
      subtitle: "One model family across providers",
      decision_question: "Same model, different hosts?",
      candidate_ids: ["ollama:llama-4-scout"],
      resolved: [
        {
          label: "Llama on Ollama",
          candidate_id: "ollama:llama-4-scout",
          display_name: "Llama 4 Scout",
          provider_id: "ollama",
          cost_class: "free",
        },
      ],
      unmet: [
        {
          label: "Llama on OpenRouter",
          needs_provider_id: "openrouter",
          needs_provider_label: "OpenRouter",
          key_name: "OPENROUTER_API_KEY",
        },
      ],
    },
  ],
};

function wrap(ui: React.ReactNode) {
  return render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);
}

describe("RecipeRow", () => {
  it("renders a card per recipe with a summary", () => {
    wrap(<RecipeRow panel={PANEL} activeRecipeId={null} onSelectRecipe={vi.fn()} />);
    expect(screen.getByText("Same model, different providers")).toBeInTheDocument();
    expect(screen.getByText(/1 need/i)).toBeInTheDocument(); // "1 needs a key"
  });

  it("calls onSelectRecipe with the recipe when clicked", () => {
    const onSelect = vi.fn();
    wrap(<RecipeRow panel={PANEL} activeRecipeId={null} onSelectRecipe={onSelect} />);
    fireEvent.click(screen.getByRole("button", { name: /Same model, different providers/i }));
    expect(onSelect).toHaveBeenCalledWith(PANEL.recipes[0]);
  });

  it("marks the active recipe as pressed and shows its unmet key entry", () => {
    wrap(<RecipeRow panel={PANEL} activeRecipeId="provider-arbitrage" onSelectRecipe={vi.fn()} />);
    expect(
      screen.getByRole("button", { name: /Same model, different providers/i }),
    ).toHaveAttribute("aria-pressed", "true");
    // Unmet banner exposes a KeyEntry "Add key" affordance for the missing provider.
    expect(screen.getByRole("button", { name: /add key/i })).toBeInTheDocument();
    expect(screen.getByText(/OpenRouter/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test -- RecipeRow`
Expected: FAIL (`RecipeRow` not found).

- [ ] **Step 3: Implement `RecipeRow`**

```tsx
// web/src/features/proof/RecipeRow.tsx
import type { RecipesPanel, ResolvedRecipe } from "../../lib/api";
import { KeyEntry } from "./KeyEntry";

// "Start from a decision recipe": an optional accelerator above the setup form. Clicking a card
// pre-fills the candidate panel + decision question below (pre-fill, not lock). The active recipe
// stays highlighted; hand-editing the panel/question flips it back to "Custom" (handled upstream).
export function RecipeRow({
  panel,
  activeRecipeId,
  onSelectRecipe,
}: {
  panel: RecipesPanel;
  activeRecipeId: string | null;
  onSelectRecipe: (recipe: ResolvedRecipe) => void;
}) {
  if (panel.recipes.length === 0) return null;
  const active = panel.recipes.find((r) => r.id === activeRecipeId) ?? null;

  return (
    <section aria-label="Decision recipes" className="grid gap-3">
      <div className="flex flex-col gap-0.5">
        <h3 className="text-sm font-medium text-(--color-ink)">Start from a decision recipe</h3>
        <p className="text-xs text-(--color-ink-faint)">
          Pick the decision you're making — we'll pre-fill a coherent panel and the question. You
          can still edit everything.
        </p>
      </div>
      <div className="flex flex-wrap gap-3">
        {panel.recipes.map((recipe) => {
          const selected = recipe.id === activeRecipeId;
          return (
            <button
              key={recipe.id}
              type="button"
              aria-pressed={selected}
              onClick={() => onSelectRecipe(recipe)}
              className={
                "grid w-56 gap-1 rounded-xl border p-4 text-left transition-colors " +
                (selected
                  ? "border-(--color-accent)/50 bg-(--color-accent)/10"
                  : "border-(--color-panel-line) hover:border-(--color-panel-line-strong)")
              }
            >
              <span className="font-medium text-(--color-ink)">{recipe.title}</span>
              <span className="text-xs text-(--color-ink-muted)">{recipe.subtitle}</span>
              <span className="mt-1 text-xs text-(--color-ink-faint)">
                {recipe.resolved.length} model{recipe.resolved.length === 1 ? "" : "s"}
                {recipe.unmet.length > 0 ? ` · ${recipe.unmet.length} need a key` : ""}
              </span>
            </button>
          );
        })}
      </div>
      {active && active.unmet.length > 0 ? (
        <div className="grid gap-2 rounded-xl border border-(--color-panel-line) bg-(--color-panel) p-4">
          <p className="text-xs text-(--color-ink-muted)">
            This recipe needs a key for{" "}
            {active.unmet.map((u) => u.needs_provider_label).join(", ")}.
          </p>
          {active.unmet.map((u) => (
            <div key={u.needs_provider_id} className="flex items-center gap-2">
              <span className="text-xs text-(--color-ink-faint)">{u.needs_provider_label}</span>
              <KeyEntry
                providerId={u.needs_provider_id}
                providerLabel={u.needs_provider_label}
                keyName={u.key_name}
              />
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --dir web test -- RecipeRow`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add web/src/features/proof/RecipeRow.tsx web/src/features/proof/RecipeRow.test.tsx
git commit -m "feat(web): RecipeRow card row with unmet key-entry banner"
```

---

### Task 8: Wire `KeyEntry` into the picker's greyed groups

**Files:**
- Modify: `web/src/features/proof/CandidatePicker.tsx:88-95`
- Test: `web/src/features/proof/CandidatePicker.test.tsx` (append)

**Interfaces:**
- Consumes: `KeyEntry`, the `CLOUD_KEY_NAMES`-equivalent mapping. The picker has `SelectionGroup` with `provider_id`, `available`, `supports_custom`. A greyed group is `available === false`. Only cloud providers (`anthropic`/`openai`/`openrouter`/`gemini`) get a key entry; derive `keyName` as `` `${provider_id.toUpperCase()}_API_KEY` `` for those four.

- [ ] **Step 1: Write the failing test**

Add `import { QueryClient, QueryClientProvider } from "@tanstack/react-query";` to the top of the file (the existing imports are `fireEvent, render, screen` from `@testing-library/react` and `expect, test, vi` from `vitest` — use `test`, not `it`). Then append:

```tsx
// web/src/features/proof/CandidatePicker.test.tsx  (append)
test("offers a key entry on a greyed cloud provider", () => {
  const panel = {
    providers: [
      {
        provider_id: "anthropic",
        label: "Anthropic",
        privacy: "cloud" as const,
        available: false,
        supports_custom: true,
        candidate_id: null,
        models: [
          {
            candidate_id: "anthropic:claude-haiku-4-5",
            model: "claude-haiku-4-5",
            display_name: "Claude Haiku 4.5",
            tier: "economy" as const,
            cost_class: "$" as const,
            context_window: 200000,
            latest: false,
            recommended: true,
          },
        ],
      },
    ],
  };
  render(
    <QueryClientProvider client={new QueryClient()}>
      <CandidatePicker panel={panel} selected={[]} onToggle={() => {}} />
    </QueryClientProvider>,
  );
  expect(screen.getByRole("button", { name: /add key/i })).toBeInTheDocument();
});
```

(Ensure the file's existing imports include `screen`, `render` from `@testing-library/react` and `CandidatePicker`. If the existing tests render `CandidatePicker` without a QueryClient, wrap this one as shown — `KeyEntry` needs the provider.)

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test -- CandidatePicker`
Expected: FAIL (no "Add key" button — current code shows the "coming with recipes" text).

- [ ] **Step 3: Replace the placeholder with `KeyEntry`**

In `web/src/features/proof/CandidatePicker.tsx`, add the import:

```tsx
import { KeyEntry } from "./KeyEntry";
```

Add this helper above `ProviderRow`:

```tsx
// The four cloud providers resolve on a key; derive the env-var name the picker prompts for.
const CLOUD_KEY_NAMES: Record<string, string> = {
  anthropic: "ANTHROPIC_API_KEY",
  openai: "OPENAI_API_KEY",
  openrouter: "OPENROUTER_API_KEY",
  gemini: "GEMINI_API_KEY",
};
```

Replace the current unavailable branch (lines 91-95):

```tsx
        {!group.available ? (
          <span className="self-center text-xs text-(--color-ink-faint)">
            Unavailable — add a key (coming with recipes)
          </span>
        ) : null}
```

with:

```tsx
        {!group.available && CLOUD_KEY_NAMES[group.provider_id] ? (
          <div className="flex items-center gap-2">
            <span className="self-center text-xs text-(--color-ink-faint)">
              Unavailable — add a key
            </span>
            <KeyEntry
              providerId={group.provider_id}
              providerLabel={group.label}
              keyName={CLOUD_KEY_NAMES[group.provider_id]}
            />
          </div>
        ) : !group.available ? (
          <span className="self-center text-xs text-(--color-ink-faint)">
            Unavailable — start the local server
          </span>
        ) : null}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pnpm --dir web test -- CandidatePicker`
Expected: PASS (existing tests + the new one).

- [ ] **Step 5: Commit**

```bash
git add web/src/features/proof/CandidatePicker.tsx web/src/features/proof/CandidatePicker.test.tsx
git commit -m "feat(web): inline KeyEntry on greyed cloud providers in the picker"
```

---

### Task 9: Wire recipes into `ProofCockpit`

**Files:**
- Modify: `web/src/features/proof/ProofCockpit.tsx`
- Test: `web/src/features/proof/ProofCockpit.test.tsx` (create, or append if one exists)

**Interfaces:**
- Consumes: `getRecipes`, `RecipeRow`, `ResolvedRecipe`. Adds query `["recipes"]`, state `activeRecipeId`, handler `onSelectRecipe`.
- Behaviour: `onSelectRecipe(r)` → `setSelected(r.candidate_ids)`, `setBrief({ ...effectiveBrief, decision_question: r.decision_question })`, `setActiveRecipeId(r.id)`. `toggleCandidate` and a decision-question edit set `activeRecipeId = null`.

- [ ] **Step 1: Write the failing test**

```tsx
// web/src/features/proof/ProofCockpit.test.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProofCockpit } from "./ProofCockpit";
import * as api from "../../lib/api";

const DATASETS = [{ id: "d1", name: "Sample", description: "", examples: [] }];
const SELECTION = {
  providers: [
    {
      provider_id: "mock_good",
      label: "Mock (good)",
      privacy: "local" as const,
      available: true,
      supports_custom: false,
      candidate_id: "mock_good",
      models: [],
    },
  ],
};
const RECIPES = {
  recipes: [
    {
      id: "provider-arbitrage",
      title: "Same model, different providers",
      subtitle: "One family across providers",
      decision_question: "Same model, different hosts?",
      candidate_ids: ["ollama:llama-4-scout"],
      resolved: [
        {
          label: "Llama on Ollama",
          candidate_id: "ollama:llama-4-scout",
          display_name: "Llama 4 Scout",
          provider_id: "ollama",
          cost_class: "free" as const,
        },
      ],
      unmet: [],
    },
  ],
};

function wrap() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <ProofCockpit report={null} onReport={vi.fn()} />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("ProofCockpit recipes", () => {
  it("pre-fills the decision question when a recipe is clicked", async () => {
    vi.spyOn(api, "getDatasets").mockResolvedValue(DATASETS as never);
    vi.spyOn(api, "getSelection").mockResolvedValue(SELECTION as never);
    vi.spyOn(api, "getRecipes").mockResolvedValue(RECIPES as never);
    wrap();
    await waitFor(() => screen.getByText("Same model, different providers"));
    fireEvent.click(screen.getByRole("button", { name: /Same model, different providers/i }));
    await waitFor(() =>
      expect((screen.getByLabelText(/decision question/i) as HTMLInputElement).value).toBe(
        "Same model, different hosts?",
      ),
    );
  });
});
```

(`getDatasets`/`getSelection`/`getRecipes` are already `export function`s in `api.ts`, so `vi.spyOn(api, ...)` works directly — no refactor needed.)

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test -- ProofCockpit`
Expected: FAIL (no recipe card rendered — `RecipeRow` not wired in).

- [ ] **Step 3: Wire the query, state, handler, and render**

In `web/src/features/proof/ProofCockpit.tsx`:

Add to the imports from `../../lib/api`: `getRecipes`, and type `ResolvedRecipe`. Add `import { RecipeRow } from "./RecipeRow";`.

Add the query beside `selection` (line ~43):

```tsx
  const recipes = useQuery({ queryKey: ["recipes"], queryFn: getRecipes });
```

Add state beside the others (line ~52):

```tsx
  const [activeRecipeId, setActiveRecipeId] = useState<string | null>(null);
```

Make `toggleCandidate` clear the active recipe (hand-edit → Custom):

```tsx
  const toggleCandidate = (id: string) => {
    setActiveRecipeId(null);
    const base = resolvedSelected;
    setSelected(base.includes(id) ? base.filter((c) => c !== id) : [...base, id]);
  };
```

Make `handleBriefChange` clear the active recipe when the decision question is edited. Update the existing `handleBriefChange`:

```tsx
  const handleBriefChange = (next: ProofBrief) => {
    if (next.task_name !== effectiveBrief.task_name) setTaskNameTouched(true);
    if (next.decision_question !== effectiveBrief.decision_question) setActiveRecipeId(null);
    setBrief(next);
  };
```

Add the recipe handler (near `toggleCandidate`):

```tsx
  const onSelectRecipe = (recipe: ResolvedRecipe) => {
    setSelected(recipe.candidate_ids);
    setBrief({ ...effectiveBrief, decision_question: recipe.decision_question });
    setActiveRecipeId(recipe.id);
  };
```

Render `RecipeRow` just above `<RunSetup ...>` inside `<main>` (after the `<header>`), guarded on data:

```tsx
        {recipes.data ? (
          <RecipeRow
            panel={recipes.data}
            activeRecipeId={activeRecipeId}
            onSelectRecipe={onSelectRecipe}
          />
        ) : null}
```

Keep the loading guard tolerant: recipes are an accelerator, so do NOT block the whole cockpit on `recipes.isLoading` — leave the existing `datasets`/`selection` loading guard as-is.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pnpm --dir web test -- ProofCockpit`
Expected: PASS.

- [ ] **Step 5: Full frontend suite + build + commit**

```bash
pnpm --dir web test
pnpm --dir web build
git add web/src/features/proof/ProofCockpit.tsx web/src/features/proof/ProofCockpit.test.tsx web/src/lib/api.ts
git commit -m "feat(web): recipe row pre-fills the panel + decision question in the cockpit"
```

Expected: all vitest green (prior 34 + new); build clean.

---

### Task 10: e2e smoke + full verification

**Files:**
- Modify: `web/e2e/proof.spec.ts`

**Interfaces:**
- Consumes: the running embedded cockpit (rebuild first). Keyless env, so cloud recipes are unmet; `provider-arbitrage`'s local arm pre-fills.

- [ ] **Step 1: Add the failing e2e assertions**

Append to the existing proof spec a block (adjust the surrounding `test(...)` to match the file's style):

```ts
test("decision recipes pre-fill the setup", async ({ page }) => {
  await page.goto("/");
  // The recipe row renders above setup.
  await expect(page.getByRole("heading", { name: "Start from a decision recipe" })).toBeVisible();
  // A recipe with a keyless local arm pre-fills the decision question.
  const recipe = page.getByRole("button", { name: /Same model, different providers/i });
  await expect(recipe).toBeVisible();
  await recipe.click();
  await expect(page.getByLabel(/decision question/i)).toHaveValue(/different hosts/i);
});
```

- [ ] **Step 2: Rebuild the embed, then run e2e**

```bash
bash scripts/build.sh
pnpm --dir web e2e
```

Expected: the new test passes alongside the existing ones (keyless; no real key submitted).

- [ ] **Step 3: Full verification sweep**

```bash
uv run pytest -q
uv run ruff check src tests
pnpm --dir web test
pnpm --dir web build
pnpm --dir web e2e
```

Expected: backend green, ruff clean, vitest green, build clean, e2e green.

- [ ] **Step 4: Security review gate (REQUIRED before treating done)**

Run the `security-secrets-review` skill against this slice. Confirm: no key value is logged, echoed in any response, written to a receipt/screenshot, or committed; `.env.local` is gitignored and written `0o600`; the credential endpoint rejects non-whitelisted providers. Address any finding before committing the e2e.

- [ ] **Step 5: Commit**

```bash
git add web/e2e/proof.spec.ts
git commit -m "test(e2e): decision recipes pre-fill the setup (keyless)"
```

---

### Task 11: Live browser check + docs

**Files:**
- Modify: `CHANGELOG.md` ([Unreleased]), `docs/worklog/2026-06-20-decision-recipes.md` (create), `HANDOFF.md` (overwrite).

- [ ] **Step 1: Live browser check on a free port**

Per `browser-visual-verification`: rebuild embed, start `orionfold up` on a PROVABLY-FREE port (assert the listener PID is yours), open the cockpit, screenshot the recipe row, click `provider-arbitrage` (verify the panel + question pre-fill and the row highlights), and verify a greyed cloud provider shows "Add key." Do NOT submit a real key in screenshots. Restart the server after any backend edit (no hot reload). List visual diffs vs. the design; fix scoped ones.

- [ ] **Step 2: Update the changelog**

Add under `[Unreleased]` in `CHANGELOG.md`: decision recipes (semantic selectors resolved server-side; pre-fill panel + question), inline `.env.local` key entry on greyed cloud providers, `GET /api/recipes`, `POST /api/credentials`.

- [ ] **Step 3: Worklog + handoff**

Write `docs/worklog/2026-06-20-decision-recipes.md` (Summary · Verification · Product impact · Risks · Next recommended step). Overwrite `HANDOFF.md` with the new state and paste prompt. Note: #5 done; next candidates are #6 prompt-variant candidates or the catalog price/source verification pass.

- [ ] **Step 4: Commit**

```bash
git add CHANGELOG.md docs/worklog/2026-06-20-decision-recipes.md HANDOFF.md
git commit -m "docs: decision recipes worklog + changelog + handoff"
```

---

## Self-Review

**Spec coverage:**
- Recipe schema + bundled JSON + loader → Task 1. ✓
- Semantic selector resolver (filters, pick strategies, unmet = cloud key) → Task 2. ✓
- `CLOUD_KEY_NAMES` whitelist → Task 2 (consumed by Tasks 4, 8). ✓
- `.env.local` atomic writer (0o600, value never surfaced) → Task 3. ✓
- `GET /api/recipes` (no secrets) + `POST /api/credentials` (whitelist, never echoes, flips availability) → Task 4. ✓
- Frontend client + types → Task 5. ✓
- Shared `KeyEntry`, nested-form-safe, invalidates selection+recipes → Task 6. ✓
- `RecipeRow` (cards, summary, active highlight, unmet banner) → Task 7. ✓
- `KeyEntry` on greyed picker groups → Task 8. ✓
- `ProofCockpit` wiring (query, activeRecipeId, onSelectRecipe, custom-on-edit, render row) → Task 9. ✓
- e2e + full verification + security review → Task 10. ✓
- Live browser check + docs → Task 11. ✓
- Guardrails (provenance untouched, keyless default, Tailwind v4, test-contract strings) → Global Constraints + respected per task (no edits to engine/export/domain). ✓
- Seeds = candidate panel + decision question only (not task name/dataset/rubric) → Task 9 `onSelectRecipe`. ✓

**Placeholder scan:** No "TBD"/"add validation"/"similar to" — every code step shows full code; `decision_question` copy is concrete in `recipes.json`. ✓

**Type consistency:** `candidate_id` (snake) in API/Python ↔ TS schema; `ResolvedRecipe`/`RecipesPanel`/`ResolvedSelector`/`UnmetSelector` names identical across Tasks 2/4/5/7/9; `set_key_in_env_local(key_name, value)` signature identical in Tasks 3/4; `CLOUD_KEY_NAMES` keys identical in Tasks 2/8; `setProviderKey(providerId, key)` identical in Tasks 5/6. ✓

**Note for executor:** Task 9's test relies on `getDatasets`/`getSelection`/`getRecipes` being `vi.spyOn`-able — they are already `export function`s in `api.ts`, so no refactor is needed. Verify `recipes.json` is picked up by the wheel build (it ships automatically because it lives inside `src/orionfold/recipes/`, like `catalog.json`); confirm with `python -c "from importlib import resources; print((resources.files('orionfold.recipes') / 'recipes.json').exists())"` after Task 1.
