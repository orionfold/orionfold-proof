"""The bundled recipe book loads and validates; selectors reference legal catalog values."""

from __future__ import annotations

import pytest

from orionfold.catalog import load_catalog
from orionfold.recipes import load_recipes
from orionfold.recipes.resolution import resolve_recipes

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
