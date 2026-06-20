"""Real provider smoke tests — skip gracefully when a credential or local server is absent.

These make actual network calls, so each is gated: cloud providers on the key being present,
local providers on the server being reachable. The invariants are deliberately modest — a
``ProviderResult`` comes back, and **no key material ever appears** in the output or error —
because the point of Gate 6 is that the integration and the redaction boundary work against
real responses, not that a given model passes the mock-tuned rubric.
"""

from __future__ import annotations

import httpx
import pytest

from orionfold.config.keys import resolve_key
from orionfold.domain.models import Candidate, Example, ProviderResult
from orionfold.providers.base import safe_generate
from orionfold.providers.registry import available_candidates, get_provider


@pytest.fixture(autouse=True)
def _small_budget(monkeypatch):
    """Keep live calls cheap and fast — a tiny output cap is enough to prove the round-trip."""
    monkeypatch.setenv("ORIONFOLD_MAX_TOKENS", "256")


def _example() -> Example:
    return Example(
        input_text="Summarize in one short sentence: Q3 revenue rose 22% to $48.2M on enterprise growth.",
        expected_text="Revenue rose 22% to $48.2M.",
    )


def _candidate(provider_id: str) -> Candidate:
    for cand in available_candidates():
        if cand.id == provider_id:
            return cand
    pytest.skip(f"{provider_id} not currently available")


def _assert_no_key_leak(result: ProviderResult, *keys: str | None) -> None:
    blob = f"{result.output_text or ''} {result.error or ''}"
    for key in keys:
        if key:
            assert key not in blob, "a credential leaked into output/error"


def _server_reachable(url: str) -> bool:
    try:
        httpx.get(url, timeout=2.0)
        return True
    except httpx.HTTPError:
        return False


def _ollama_models() -> list[str]:
    try:
        resp = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        return [m["name"] for m in resp.json().get("models", [])]
    except (httpx.HTTPError, ValueError, KeyError):
        return []


_OLLAMA_MODELS = _ollama_models()


# --- cloud providers (gated on key presence) --------------------------------------------


@pytest.mark.parametrize("provider_id, key_name", [
    ("openai", "OPENAI_API_KEY"),
    ("openrouter", "OPENROUTER_API_KEY"),
    ("gemini", "GEMINI_API_KEY"),
    ("anthropic", "ANTHROPIC_API_KEY"),
])
def test_cloud_provider_completes_without_leaking_key(provider_id, key_name):
    key = resolve_key(key_name)
    if key is None:
        pytest.skip(f"{key_name} not set")
    cand = _candidate(provider_id)
    result = safe_generate(get_provider(provider_id), _example(), cand)
    assert isinstance(result, ProviderResult)
    _assert_no_key_leak(result, key)
    if result.error is not None:
        # A real failure (model access, quota) is allowed — but must be a clean, redacted msg.
        assert "[redacted]" in result.error or "sk-" not in result.error
    else:
        # Output content depends on model + token budget (a reasoning model at a small cap can
        # legitimately return empty), so we don't assert on it here — the integration + no-leak
        # guarantees are what matter. Real non-empty success is shown by the manual run evidence.
        assert result.privacy == "cloud"


def test_anthropic_bad_key_error_does_not_leak_the_key(monkeypatch):
    # Force a real 401 with a known bad key and confirm it never appears in the returned error.
    # (In practice Anthropic's 401 body doesn't echo the key at all — the redaction boundary is
    # belt-and-suspenders, proven against key-bearing bodies in test_providers_http.py.)
    if resolve_key("ANTHROPIC_API_KEY") is None and not _server_reachable("https://api.anthropic.com"):
        pytest.skip("no network/credential context for Anthropic")
    bad = "sk-ant-badkey-DEADBEEF0123456789"
    monkeypatch.setenv("ANTHROPIC_API_KEY", bad)
    cand = _candidate("anthropic")
    result = safe_generate(get_provider("anthropic"), _example(), cand)
    assert result.error is not None
    assert bad not in result.error


# --- local providers (gated on server reachability) -------------------------------------


@pytest.mark.skipif(not _OLLAMA_MODELS, reason="ollama not reachable / no models pulled")
def test_ollama_completes_locally(monkeypatch):
    model = _OLLAMA_MODELS[0]
    cand = Candidate(id="ollama", label="ollama", provider_id="ollama", privacy="local", model=model)
    result = safe_generate(get_provider("ollama"), _example(), cand)
    assert isinstance(result, ProviderResult)
    assert result.privacy == "local"
    assert result.estimated_cost_usd == 0.0
    # No output-content assertion: a reasoning model (qwen3/deepseek-r1) at a small cap can
    # exhaust the budget thinking and return empty — still a valid clean round-trip.


@pytest.mark.skipif(
    not _server_reachable("http://localhost:1234/v1/models"),
    reason="LM Studio server not running on :1234",
)
def test_lmstudio_completes_locally():
    cand = _candidate("lmstudio")
    result = safe_generate(get_provider("lmstudio"), _example(), cand)
    assert isinstance(result, ProviderResult)
    assert result.privacy == "local"
