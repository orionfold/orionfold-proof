"""The bundled model catalog loads, validates, and is internally consistent."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from orionfold.catalog import default_model_for, load_catalog
from orionfold.catalog.models import CatalogModel, CatalogProvider, ModelCatalog
from orionfold.providers import anthropic as _anthropic
from orionfold.providers import gemini as _gemini
from orionfold.providers import ollama as _ollama

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


def test_provider_rejects_default_model_not_in_models():
    good = CatalogModel(
        id="m1", display_name="M1", family="x", tier="economy", cost_class="free"
    )
    with pytest.raises(ValidationError):
        CatalogProvider(
            id="p", label="P", privacy="local", default_model="missing", models=[good]
        )


def test_provider_rejects_duplicate_model_ids():
    a = CatalogModel(id="dup", display_name="A", family="x", tier="economy", cost_class="free")
    b = CatalogModel(id="dup", display_name="B", family="x", tier="economy", cost_class="free")
    with pytest.raises(ValidationError):
        CatalogProvider(
            id="p", label="P", privacy="local", default_model="dup", models=[a, b]
        )


# The curated per-provider defaults (each provider's cheap "first-click" starter). Pinned so a
# catalog content edit that moves a default is a deliberate, reviewed change — and so the
# registry and direct instantiation never silently diverge.
_CURRENT_DEFAULTS = {
    "openai": "gpt-5.4-nano",
    "openrouter": "meta-llama/llama-3.1-8b-instruct",
    "lmstudio": "local-model",
    "ollama": "llama3.2",
    "gemini": "gemini-3.1-flash-lite",
    "anthropic": "claude-haiku-4-5",
}


@pytest.mark.parametrize("provider_id,expected", sorted(_CURRENT_DEFAULTS.items()))
def test_default_model_for_matches_current_defaults(provider_id, expected):
    assert default_model_for(provider_id) == expected


def test_default_model_for_unknown_provider_raises():
    with pytest.raises(KeyError):
        default_model_for("does-not-exist")


def test_fable_5_not_in_catalog():
    catalog = load_catalog()
    ids = [m.id for p in catalog.providers for m in p.models]
    assert "claude-fable-5" not in ids


def test_anthropic_frontier_is_opus_and_flagged_latest():
    catalog = load_catalog()
    anthropic = next(p for p in catalog.providers if p.id == "anthropic")
    frontier = [m for m in anthropic.models if m.tier == "frontier"]
    assert [m.id for m in frontier] == ["claude-opus-4-8"]
    assert frontier[0].latest is True


def test_provider_module_defaults_match_catalog():
    # The provider modules' __init__ fallbacks must agree with the catalog so direct
    # instantiation and the registry never diverge.
    assert _ollama.DEFAULT_MODEL == default_model_for("ollama")
    assert _gemini.DEFAULT_MODEL == default_model_for("gemini")
    assert _anthropic.DEFAULT_MODEL == default_model_for("anthropic")
