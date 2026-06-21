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
