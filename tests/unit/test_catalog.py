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
