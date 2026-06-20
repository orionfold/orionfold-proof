"""Real-provider parsing + redaction, exercised keyless via a stubbed ``httpx.post``.

No network, no credentials: we stub the single HTTP call each provider makes and assert (a)
the response is parsed into a uniform ``ProviderResult`` with the right tokens/privacy/cost,
and (b) a provider error carrying credential-shaped text is redacted at the ``safe_generate``
boundary — the load-bearing guarantee for Gate 6.
"""

from __future__ import annotations

import httpx
import pytest

from orionfold.domain.models import Candidate, Example
from orionfold.providers import http as http_mod
from orionfold.providers.anthropic import AnthropicProvider
from orionfold.providers.base import safe_generate
from orionfold.providers.gemini import GeminiProvider
from orionfold.providers.ollama import OllamaProvider
from orionfold.providers.openai_compatible import OpenAICompatibleProvider


@pytest.fixture(autouse=True)
def _no_real_keys(tmp_path, monkeypatch):
    """Hermetic: tmp CWD (no .env.local) and provider keys unset, so any key is one we inject."""
    monkeypatch.chdir(tmp_path)
    for name in ("OPENAI_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def _example() -> Example:
    return Example(input_text="Summarize: revenue up 22%.", expected_text="Revenue +22%.")


def _candidate(provider_id: str, model: str) -> Candidate:
    return Candidate(id=provider_id, label=provider_id, provider_id=provider_id, model=model)


def _stub_post(monkeypatch, *, status: int = 200, json_body: dict | None = None, text: str = ""):
    """Replace the module-level ``httpx.post`` the helper calls with a canned response."""

    def fake_post(url, json=None, headers=None, timeout=None):  # noqa: A002 - mirrors httpx
        request = httpx.Request("POST", url)
        if json_body is not None:
            return httpx.Response(status, json=json_body, request=request)
        return httpx.Response(status, text=text, request=request)

    monkeypatch.setattr(http_mod.httpx, "post", fake_post)


# --- parsing (happy path) ---------------------------------------------------------------


def test_ollama_parses_message_and_token_counts(monkeypatch):
    _stub_post(
        monkeypatch,
        json_body={
            "message": {"role": "assistant", "content": "Revenue grew 22%."},
            "prompt_eval_count": 11,
            "eval_count": 7,
            "done": True,
        },
    )
    result = OllamaProvider().generate(_example(), _candidate("ollama", "llama3.2"))
    assert result.output_text == "Revenue grew 22%."
    assert result.input_tokens == 11
    assert result.output_tokens == 7
    assert result.privacy == "local"
    assert result.estimated_cost_usd == 0.0  # local model → not priced
    assert result.error is None
    assert result.raw_metadata == {"provider": "ollama", "model": "llama3.2"}


def test_openai_compatible_parses_choice_and_usage(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    _stub_post(
        monkeypatch,
        json_body={
            "choices": [{"message": {"role": "assistant", "content": "Revenue +22%."}}],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 500},
        },
    )
    provider = OpenAICompatibleProvider(
        id="openai",
        label="OpenAI",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
        key_name="OPENAI_API_KEY",
    )
    result = provider.generate(_example(), _candidate("openai", "gpt-4o-mini"))
    assert result.output_text == "Revenue +22%."
    assert result.input_tokens == 1000
    assert result.output_tokens == 500
    assert result.privacy == "cloud"
    # gpt-4o-mini: (1000*0.15 + 500*0.60) / 1e6 = 0.00045
    assert result.estimated_cost_usd == pytest.approx(0.00045)


def test_lmstudio_is_keyless_local(monkeypatch):
    _stub_post(
        monkeypatch,
        json_body={
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 1},
        },
    )
    provider = OpenAICompatibleProvider(
        id="lmstudio",
        label="LM Studio",
        base_url="http://localhost:1234/v1",
        default_model="local-model",
        key_name=None,
        privacy="local",
    )
    result = provider.generate(_example(), _candidate("lmstudio", "local-model"))
    assert result.output_text == "ok"
    assert result.privacy == "local"
    assert result.estimated_cost_usd == 0.0


def test_gemini_joins_parts_and_reads_usage_metadata(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-test-not-real")
    _stub_post(
        monkeypatch,
        json_body={
            "candidates": [{"content": {"parts": [{"text": "Revenue "}, {"text": "+22%."}]}}],
            "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 4},
        },
    )
    result = GeminiProvider().generate(_example(), _candidate("gemini", "gemini-2.5-flash"))
    assert result.output_text == "Revenue +22%."
    assert result.input_tokens == 12
    assert result.output_tokens == 4
    assert result.privacy == "cloud"


def test_anthropic_joins_text_blocks_and_reads_usage(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-real")
    _stub_post(
        monkeypatch,
        json_body={
            "content": [
                {"type": "text", "text": "Revenue "},
                {"type": "text", "text": "+22%."},
            ],
            "usage": {"input_tokens": 20, "output_tokens": 6},
        },
    )
    result = AnthropicProvider().generate(_example(), _candidate("anthropic", "claude-haiku-4-5"))
    assert result.output_text == "Revenue +22%."
    assert result.input_tokens == 20
    assert result.output_tokens == 6
    # claude-haiku-4-5: (20*1.00 + 6*5.00) / 1e6
    assert result.estimated_cost_usd == pytest.approx((20 * 1.00 + 6 * 5.00) / 1_000_000)


# --- error path + redaction (the load-bearing guarantee) --------------------------------


def test_missing_key_is_returned_as_error_not_raised(monkeypatch):
    # No key set; safe_generate must return a result with an error, never raise.
    result = safe_generate(
        AnthropicProvider(), _example(), _candidate("anthropic", "claude-haiku-4-5")
    )
    assert result.error is not None
    assert "ANTHROPIC_API_KEY not set" in result.error
    assert result.output_text == ""


@pytest.mark.parametrize(
    "provider, cand, leaky_body",
    [
        (
            OpenAICompatibleProvider(
                id="openai",
                label="OpenAI",
                base_url="https://api.openai.com/v1",
                default_model="gpt-4o-mini",
                key_name="OPENAI_API_KEY",
            ),
            ("openai", "gpt-4o-mini"),
            'Incorrect API key provided: sk-proj-ABCDEF1234567890. Header was "Bearer sk-proj-ABCDEF1234567890"',
        ),
        (
            GeminiProvider(),
            ("gemini", "gemini-2.5-flash"),
            "API key not valid. key=AIzaSyAExampleKey123456 token=tok_secretvalue",
        ),
        (
            AnthropicProvider(),
            ("anthropic", "claude-haiku-4-5"),
            "authentication_error: invalid x-api-key sk-ant-api03-SECRETKEYVALUE123456",
        ),
    ],
)
def test_real_provider_error_body_is_redacted(monkeypatch, provider, cand, leaky_body):
    # Give cloud providers a (fake) key so they reach the HTTP call, then return a 401 whose
    # body echoes credential-shaped text. safe_generate must redact it.
    for name in ("OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.setenv(name, "fake-key-for-test")
    _stub_post(monkeypatch, status=401, text=leaky_body)
    result = safe_generate(provider, _example(), _candidate(*cand))
    assert result.error is not None
    assert "[redacted]" in result.error
    for secret in ("sk-proj-ABCDEF1234567890", "AIzaSyAExampleKey123456", "sk-ant-api03-SECRETKEYVALUE123456", "tok_secretvalue"):
        assert secret not in result.error


def test_unlabeled_custom_gateway_key_is_scrubbed_by_value(monkeypatch):
    # A custom gateway key with no recognizable shape (not sk-/AIza/Bearer/labeled) that the
    # error body echoes verbatim must still be removed — we scrub the literal in-flight value.
    weird = "weirdgatewaytoken123abc"
    monkeypatch.setenv("OPENAI_API_KEY", weird)
    _stub_post(monkeypatch, status=401, text=f"unauthorized: token {weird} rejected by gateway")
    provider = OpenAICompatibleProvider(
        id="openai",
        label="OpenAI",
        base_url="https://gw.example/v1",
        default_model="m",
        key_name="OPENAI_API_KEY",
    )
    result = safe_generate(provider, _example(), _candidate("openai", "m"))
    assert result.error is not None
    assert weird not in result.error
    assert "[redacted]" in result.error


def test_max_output_tokens_env_override(monkeypatch):
    assert http_mod.max_output_tokens() == 2048  # default
    monkeypatch.setenv("ORIONFOLD_MAX_TOKENS", "8192")
    assert http_mod.max_output_tokens() == 8192
    monkeypatch.setenv("ORIONFOLD_MAX_TOKENS", "garbage")
    assert http_mod.max_output_tokens() == 2048  # bad value falls back to default


def test_providers_send_the_configured_token_cap(monkeypatch):
    # Capture the outgoing payload to confirm the cap reaches the wire for each profile shape.
    monkeypatch.setenv("ORIONFOLD_MAX_TOKENS", "4096")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
    captured: dict = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.update(json or {})
        return httpx.Response(
            200,
            json={"content": [{"type": "text", "text": "ok"}], "usage": {"input_tokens": 1, "output_tokens": 1}},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(http_mod.httpx, "post", fake_post)
    AnthropicProvider().generate(_example(), _candidate("anthropic", "claude-haiku-4-5"))
    assert captured["max_tokens"] == 4096


def test_transport_failure_becomes_clean_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake")

    def boom(url, json=None, headers=None, timeout=None):
        raise httpx.ConnectError("connection refused", request=httpx.Request("POST", url))

    monkeypatch.setattr(http_mod.httpx, "post", boom)
    provider = OpenAICompatibleProvider(
        id="openai",
        label="OpenAI",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
        key_name="OPENAI_API_KEY",
    )
    result = safe_generate(provider, _example(), _candidate("openai", "gpt-4o-mini"))
    assert result.error is not None
    assert "ConnectError" in result.error
