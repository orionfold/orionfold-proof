"""selection_panel merges catalog (which models exist) + registry (which providers are
available) + mocks into one read-only picker structure. No credentials."""

from __future__ import annotations

import pytest

from orionfold.providers import selection as selection_mod
from orionfold.providers.registry import build_candidates
from orionfold.providers.selection import selection_panel


@pytest.fixture(autouse=True)
def _no_keys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    # Hermetic: never hit a live Ollama daemon or the real overlay. Default = daemon up, nothing
    # pulled. Tests that need a specific pulled set / a down daemon call _patch_pulled to override.
    monkeypatch.setenv("ORIONFOLD_MODELS_OVERLAY", str(tmp_path / "models.json"))
    monkeypatch.setattr(selection_mod, "list_pulled", lambda host: set())


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


# --- hf-own-models: per-model availability for curated Orionfold models ---------------------

from orionfold.providers.http import ProviderError  # noqa: E402


def _orionfold_models(panel):
    ollama = _by_id(panel)["ollama"]
    return [m for m in ollama.models if m.family == "orionfold"]


def _patch_pulled(monkeypatch, *, names=None, down=False):
    """Control the live tag set selection reconciles against (no real daemon)."""

    def fake_list_pulled(host):
        if down:
            raise ProviderError("Ollama not reachable")
        return set(names or [])

    monkeypatch.setattr(selection_mod, "list_pulled", fake_list_pulled)


def test_orionfold_model_unavailable_when_not_pulled(monkeypatch):
    _patch_pulled(monkeypatch, names=["qwen3:latest"])  # daemon up, roster not pulled
    orion = _orionfold_models(selection_panel())
    assert orion  # roster present
    for m in orion:
        assert m.available is False
        assert m.reason is not None and "orionfold pull" in m.reason
        assert m.repo_id is not None


def test_orionfold_model_available_when_pulled(monkeypatch):
    from orionfold.catalog import load_catalog

    target = next(
        m
        for p in load_catalog().providers
        if p.id == "ollama"
        for m in p.models
        if m.family == "orionfold"
    )
    # The daemon reports the pulled model with the default :latest suffix → must reconcile.
    _patch_pulled(monkeypatch, names=[f"{target.repo_id}:latest"])
    by_model = {m.model: m for m in _orionfold_models(selection_panel())}
    assert by_model[target.id].available is True
    assert by_model[target.id].reason is None


def test_daemon_down_degrades_gracefully_cloud_still_present(monkeypatch):
    _patch_pulled(monkeypatch, down=True)
    panel = selection_panel()
    groups = _by_id(panel)
    # Selection never raises; cloud groups are still present.
    assert "anthropic" in groups and "openai" in groups
    # Every Orionfold model is unavailable with a daemon-down reason.
    orion = _orionfold_models(panel)
    assert orion and all(m.available is False for m in orion)
    assert all("Ollama not running" in (m.reason or "") for m in orion)


def test_standard_local_models_unaffected_by_per_model_gate(monkeypatch):
    # llama3.2 etc. have no repo_id → they stay available regardless of the pulled set.
    _patch_pulled(monkeypatch, names=[])
    ollama = _by_id(selection_panel())["ollama"]
    standard = [m for m in ollama.models if m.family != "orionfold"]
    assert standard and all(m.available is True for m in standard)
