"""selection_panel merges catalog (which models exist) + registry (which providers are
available) + mocks into one read-only picker structure. No credentials."""

from __future__ import annotations

import pytest

from orionfold.providers.selection import selection_panel


@pytest.fixture(autouse=True)
def _no_keys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def _by_id(panel):
    return {g.provider_id: g for g in panel.providers}


def test_mocks_come_first_with_no_models_and_no_custom():
    panel = selection_panel()
    first_two = panel.providers[:2]
    assert [g.provider_id for g in first_two] == ["mock_good", "mock_bad"]
    for g in first_two:
        assert g.models == []
        assert g.supports_custom is False
        assert g.candidate_id == g.provider_id  # the group itself is one candidate
        assert g.available is True


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
