"""build_candidates widens run validation: bare ids stay valid (back-compat), composite
provider:model ids resolve for AVAILABLE providers, everything else is rejected (keyless-safe)."""

from __future__ import annotations

import pytest

from orionfold.domain.models import PromptVariant
from orionfold.providers.registry import (
    UnknownCandidateError,
    available_candidates,
    build_candidates,
    expand_prompt_variants,
)


@pytest.fixture(autouse=True)
def _no_keys(tmp_path, monkeypatch):
    """Hermetic: tmp CWD (no .env.local) and every cloud key unset → cloud unavailable."""
    monkeypatch.chdir(tmp_path)
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def test_bare_mock_id_resolves_unchanged():
    [cand] = build_candidates(["mock_good"])
    expected = {c.id: c for c in available_candidates()}["mock_good"]
    assert cand == expected  # byte-identical → config_hash unchanged for mock runs
    assert cand.model is None


def test_bare_local_default_id_resolves_to_default_model():
    [cand] = build_candidates(["ollama"])
    assert cand.provider_id == "ollama"
    assert cand.model  # the catalog default, non-empty


def test_composite_id_for_available_provider_resolves():
    [cand] = build_candidates(["ollama:llama3.2"])
    assert cand.id == "ollama:llama3.2"
    assert cand.provider_id == "ollama"  # BARE provider id — engine routes on this
    assert cand.model == "llama3.2"
    assert cand.label == "Ollama · llama3.2"
    assert cand.privacy == "local"


def test_colon_in_model_is_preserved():
    [cand] = build_candidates(["ollama:llama3.1:8b"])
    assert cand.provider_id == "ollama"
    assert cand.model == "llama3.1:8b"  # split on the FIRST colon only


def test_composite_for_unavailable_provider_is_rejected():
    with pytest.raises(UnknownCandidateError) as exc:
        build_candidates(["anthropic:claude-opus-4-8"])  # no key → unavailable
    assert exc.value.unknown == ["anthropic:claude-opus-4-8"]


def test_composite_id_on_a_mock_provider_is_rejected():
    # Mocks must stay bare-id + model=None (this protects mock-run config_hash). A crafted
    # ``mock_good:foo`` must NOT mint a composite mock candidate — mocks are model=None in the
    # registry, so the composite branch excludes them.
    with pytest.raises(UnknownCandidateError) as exc:
        build_candidates(["mock_good:foo"])
    assert exc.value.unknown == ["mock_good:foo"]


def test_empty_model_and_unknown_provider_are_rejected():
    with pytest.raises(UnknownCandidateError) as exc:
        build_candidates(["ollama:", "nope:x", "garbage"])
    assert exc.value.unknown == ["ollama:", "nope:x", "garbage"]


def test_error_message_matches_route_contract():
    with pytest.raises(UnknownCandidateError) as exc:
        build_candidates(["nope:x"])
    assert str(exc.value) == "Unknown candidate(s): ['nope:x']"


def test_expand_prompt_variants_mints_one_candidate_per_prompt():
    [base] = build_candidates(["mock_good"])  # model=None, bare mock
    variants = [
        PromptVariant(name="Baseline", system_prompt="Be neutral."),
        PromptVariant(name="Step by step", system_prompt="Think step by step."),
    ]
    out = expand_prompt_variants(base, variants)
    assert [c.id for c in out] == ["mock_good#baseline", "mock_good#step-by-step"]
    assert [c.label for c in out] == ["Baseline", "Step by step"]
    assert [c.system_prompt for c in out] == ["Be neutral.", "Think step by step."]
    # Provider/model/privacy copied from the base, so the engine routes + hashes correctly.
    assert all(c.provider_id == "mock_good" and c.model is None and c.privacy == "local" for c in out)


def test_expand_prompt_variants_dedupes_clashing_slugs():
    [base] = build_candidates(["ollama:llama3.2"])
    variants = [
        PromptVariant(name="Terse", system_prompt="a"),
        PromptVariant(name="terse!", system_prompt="b"),  # slugifies to the same "terse"
    ]
    out = expand_prompt_variants(base, variants)
    assert [c.id for c in out] == ["ollama:llama3.2#terse", "ollama:llama3.2#terse-2"]
    assert all(c.model == "llama3.2" and c.provider_id == "ollama" for c in out)
