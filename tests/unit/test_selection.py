"""selection_panel merges catalog (which models exist) + registry (which providers are
available) + mocks into one read-only picker structure. No credentials."""

from __future__ import annotations

import pytest

from orionfold.providers.registry import build_candidates
from orionfold.providers.selection import selection_panel


@pytest.fixture(autouse=True)
def _no_keys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def _by_id(panel):
    return {g.provider_id: g for g in panel.providers}


def test_sandbox_off_has_no_mock_group():
    # Mocks are off the customer happy path now; they only appear in Sandbox.
    panel = selection_panel(sandbox=False)
    assert all(g.provider_id != "mock" for g in panel.providers)
    assert all(g.provider_id not in ("mock_good", "mock_bad") for g in panel.providers)


def test_sandbox_on_shows_one_mock_group_with_two_models():
    panel = selection_panel(sandbox=True)
    mock = [g for g in panel.providers if g.provider_id == "mock"]
    assert len(mock) == 1
    g = mock[0]
    assert g.label == "Mock" and g.candidate_id is None and g.supports_custom is False
    by_id = {m.candidate_id: m.display_name for m in g.models}
    assert by_id == {"mock_good": "Good model", "mock_bad": "Bad model"}


def test_mock_ids_stay_bare_and_resolvable():
    # Invariant: the engine still resolves the bare ids the picker now nests under "mock".
    cands = build_candidates(["mock_good", "mock_bad"])
    assert [c.id for c in cands] == ["mock_good", "mock_bad"]
    assert [c.label for c in cands] == ["Mock · good", "Mock · bad"]


def test_catalog_providers_present_with_model_candidate_ids():
    groups = _by_id(selection_panel())
    anthropic = groups["anthropic"]
    assert anthropic.supports_custom is True
    assert anthropic.candidate_id is None
    assert anthropic.models  # populated from the catalog
    sample = anthropic.models[0]
    assert sample.candidate_id == f"anthropic:{sample.model}"


def test_availability_reflects_keys():
    groups = _by_id(selection_panel())
    assert groups["anthropic"].available is False  # no key
    assert groups["ollama"].available is True  # local, keyless


def test_latest_and_recommended_flags_carry_through():
    groups = _by_id(selection_panel())
    anthropic_models = groups["anthropic"].models
    # The catalog marks one latest and at least one recommended for anthropic.
    assert any(m.latest for m in anthropic_models)
    assert any(m.recommended for m in anthropic_models)
