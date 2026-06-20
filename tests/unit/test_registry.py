"""The dynamic registry: local profiles always offered, cloud profiles gated on keys.

Listing makes no network calls, so a dummy key safely lights up a cloud candidate here.
"""

from __future__ import annotations

import pytest

from orionfold.providers.registry import available_candidates, get_provider

_CLOUD = {"openai", "openrouter", "gemini", "anthropic"}
_KEY_FOR = {
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


@pytest.fixture(autouse=True)
def _no_keys(tmp_path, monkeypatch):
    """Hermetic: tmp CWD (no .env.local) and every provider key unset."""
    monkeypatch.chdir(tmp_path)
    for name in _KEY_FOR.values():
        monkeypatch.delenv(name, raising=False)


def _ids() -> set[str]:
    return {c.id for c in available_candidates()}


def test_local_profiles_always_offered_no_cloud_without_keys():
    ids = _ids()
    assert {"mock_good", "mock_bad", "ollama", "lmstudio"} <= ids
    assert ids.isdisjoint(_CLOUD)  # no key → no cloud candidate


@pytest.mark.parametrize("candidate_id", sorted(_CLOUD))
def test_cloud_candidate_appears_only_when_its_key_is_present(candidate_id, monkeypatch):
    assert candidate_id not in _ids()
    monkeypatch.setenv(_KEY_FOR[candidate_id], "dummy-key-no-network-in-listing")
    assert candidate_id in _ids()
    # get_provider returns the configured instance with the right privacy boundary.
    provider = get_provider(candidate_id)
    assert provider.privacy == "cloud"


def test_local_candidates_carry_model_and_label():
    cands = {c.id: c for c in available_candidates()}
    ollama = cands["ollama"]
    assert ollama.model  # a default model string
    assert "·" in ollama.label  # label is "Ollama · <model>"
    assert ollama.privacy == "local"
    # mocks have no model and keep their plain label
    assert cands["mock_good"].model is None


def test_unknown_provider_raises():
    with pytest.raises(KeyError):
        get_provider("does-not-exist")


def test_env_var_overrides_catalog_default(monkeypatch):
    # The catalog default is only the *fallback*; an explicit ORIONFOLD_<P>_MODEL must win.
    monkeypatch.setenv("ORIONFOLD_OLLAMA_MODEL", "custom-ollama-model")
    cands = {c.id: c for c in available_candidates()}
    assert cands["ollama"].model == "custom-ollama-model"
