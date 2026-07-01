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


def test_ollama_captures_eval_duration_as_warm_decode_ms(monkeypatch):
    # Honesty fix (proof-tokps-diluted-not-warm-decode): Ollama returns eval_count + eval_duration
    # (ns) — the pure warm-decode time, excluding cold model load + prompt-eval. Capture it so the
    # receipt can report true warm throughput, not the ~3×-diluted end-to-end number.
    _stub_post(
        monkeypatch,
        json_body={
            "message": {"role": "assistant", "content": "Revenue grew 22%."},
            "prompt_eval_count": 11,
            "eval_count": 7,
            "load_duration": 4_000_000_000,  # 4s cold load — must NOT leak into warm_decode_ms
            "prompt_eval_duration": 500_000_000,  # 0.5s prompt-eval — also excluded
            "eval_duration": 350_000_000,  # 0.35s pure decode → 350ms
            "done": True,
        },
    )
    result = OllamaProvider().generate(_example(), _candidate("ollama", "llama3.2"))
    assert result.warm_decode_ms == 350  # eval_duration(ns) / 1e6, decode-only


def test_ollama_warm_decode_ms_none_when_timing_absent(monkeypatch):
    # A response without eval_duration (or with a zero/garbage value) yields None — never a fake
    # zero that would later divide into a bogus throughput.
    _stub_post(
        monkeypatch,
        json_body={
            "message": {"role": "assistant", "content": "ok"},
            "prompt_eval_count": 1,
            "eval_count": 1,
            "done": True,
        },
    )
    result = OllamaProvider().generate(_example(), _candidate("ollama", "llama3.2"))
    assert result.warm_decode_ms is None


def test_cloud_provider_has_no_warm_decode_ms(monkeypatch):
    # Cloud providers report no decode-only timing — warm_decode_ms stays None so the receipt's
    # warm column honestly shows "—" rather than a number that means something different.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    _stub_post(
        monkeypatch,
        json_body={
            "choices": [{"message": {"role": "assistant", "content": "ok"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
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
    assert result.warm_decode_ms is None


def test_ollama_discloses_deterministic_sampling(monkeypatch):
    # Honesty (cloud-provider-determinism-audit): Ollama pins temperature 0, so it discloses a
    # deterministic descriptor the receipt can surface — the disclosure counterpart to the
    # temperature=0 it already sends. Secret-free: {temperature, mode} only.
    _stub_post(
        monkeypatch,
        json_body={"message": {"content": "ok"}, "prompt_eval_count": 1, "eval_count": 1},
    )
    result = OllamaProvider().generate(_example(), _candidate("ollama", "llama3.2"))
    assert result.sampling == {"temperature": 0.0, "mode": "deterministic"}


@pytest.mark.parametrize(
    "make_provider, cand, key_name",
    [
        (lambda: AnthropicProvider(), ("anthropic", "claude-haiku-4-5"), "ANTHROPIC_API_KEY"),
        (lambda: GeminiProvider(), ("gemini", "gemini-2.5-flash"), "GEMINI_API_KEY"),
        (
            lambda: OpenAICompatibleProvider(
                id="openai", label="OpenAI", base_url="https://api.openai.com/v1",
                default_model="gpt-4o-mini", key_name="OPENAI_API_KEY",
            ),
            ("openai", "gpt-4o-mini"),
            "OPENAI_API_KEY",
        ),
    ],
)
def test_cloud_provider_discloses_provider_default_sampling(monkeypatch, make_provider, cand, key_name):
    # The three cloud providers set no sampling params → they inherit each API's server-side
    # default. We do NOT fabricate a temperature we didn't send; the descriptor is an honest
    # {temperature: None, mode: "provider_default"} so the receipt reads "sampled", not "temp=1.0".
    monkeypatch.setenv(key_name, "fake-key-for-test")
    _stub_post(
        monkeypatch,
        json_body={
            "content": [{"type": "text", "text": "ok"}], "usage": {"input_tokens": 1, "output_tokens": 1},
            "choices": [{"message": {"content": "ok"}}],
            "candidates": [{"content": {"parts": [{"text": "ok"}]}}], "usageMetadata": {},
        },
    )
    result = make_provider().generate(_example(), _candidate(*cand))
    assert result.sampling == {"temperature": None, "mode": "provider_default"}


def test_ollama_sends_deterministic_options(monkeypatch):
    """Local runs must be reproducible: the provider pins temperature 0 and disables thinking
    (think=false) so a thinking-capable model emits clean, parseable output. Without this a proof
    run is non-deterministic — at odds with the receipt's repeatability promise."""
    captured: dict = {}

    def capturing_post(url, json=None, headers=None, timeout=None):  # noqa: A002 - mirrors httpx
        captured["payload"] = json
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={"message": {"content": "ok"}, "prompt_eval_count": 1, "eval_count": 1},
            request=request,
        )

    monkeypatch.setattr(http_mod.httpx, "post", capturing_post)
    OllamaProvider().generate(_example(), _candidate("ollama", "llama3.2"))

    payload = captured["payload"]
    assert payload["options"]["temperature"] == 0
    assert payload["options"]["num_predict"] >= 1
    assert payload["think"] is False  # thinking off → no <think> block to pollute scoring


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


def test_openrouter_uses_real_usage_cost_even_for_unknown_model(monkeypatch):
    # Regression: openrouter-cost-reads-zero. OpenRouter returns the real billed cost in
    # ``usage.cost`` (credits = USD). A CUSTOM model id is not in the static price table, so the
    # old estimate path returned 0.0 ("free") for a genuinely billed call. The real cost must win.
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-not-real")
    _stub_post(
        monkeypatch,
        json_body={
            "choices": [{"message": {"content": "Routed."}}],
            "usage": {"prompt_tokens": 1200, "completion_tokens": 300, "cost": 0.0123},
        },
    )
    provider = OpenAICompatibleProvider(
        id="openrouter",
        label="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        default_model="z-ai/glm-4.6",
        key_name="OPENROUTER_API_KEY",
    )
    # an id deliberately NOT in pricing._PRICES (the custom-model case)
    result = provider.generate(_example(), _candidate("openrouter", "some-lab/brand-new-model"))
    assert result.estimated_cost_usd == pytest.approx(0.0123)
    assert result.input_tokens == 1200 and result.output_tokens == 300


def test_openai_compatible_falls_back_to_estimate_when_no_real_cost(monkeypatch):
    # OpenAI/LM Studio responses carry no ``usage.cost`` → the static estimate table is still used,
    # unchanged. (gpt-4o-mini: (1000*0.15 + 500*0.60)/1e6 = 0.00045.)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    _stub_post(
        monkeypatch,
        json_body={
            "choices": [{"message": {"content": "ok"}}],
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
    assert result.estimated_cost_usd == pytest.approx(0.00045)


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


def _capture_openai_payload(monkeypatch, provider) -> dict:
    """Run one ``generate`` against ``provider`` with a stubbed POST; return the sent JSON body."""
    captured: dict = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.clear()
        captured.update(json or {})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(http_mod.httpx, "post", fake_post)
    provider.generate(_example(), _candidate(provider.id, provider.default_model))
    return captured


def test_openai_profile_sends_max_completion_tokens(monkeypatch):
    # GPT-5.x rejects "max_tokens" (HTTP 400 "Use 'max_completion_tokens' instead"). The OpenAI
    # profile must send the newer param; "max_tokens" must NOT appear on the wire.
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    provider = OpenAICompatibleProvider(
        id="openai",
        label="OpenAI",
        base_url="https://api.openai.com/v1",
        default_model="gpt-5-mini",
        key_name="OPENAI_API_KEY",
        token_param="max_completion_tokens",
    )
    payload = _capture_openai_payload(monkeypatch, provider)
    assert payload["max_completion_tokens"] == http_mod.max_output_tokens()
    assert "max_tokens" not in payload


def test_openai_compatible_defaults_to_max_tokens(monkeypatch):
    # OpenRouter + LM Studio share the class but accept "max_tokens" — the default must not regress.
    provider = OpenAICompatibleProvider(
        id="lmstudio",
        label="LM Studio",
        base_url="http://localhost:1234/v1",
        default_model="local-model",
        key_name=None,
        privacy="local",
    )
    payload = _capture_openai_payload(monkeypatch, provider)
    assert payload["max_tokens"] == http_mod.max_output_tokens()
    assert "max_completion_tokens" not in payload


def test_idle_budget_is_per_provider_class(monkeypatch):
    # No override: local gets the generous budget, cloud the tighter one (ADR-0003 follow-up).
    monkeypatch.delenv("ORIONFOLD_TIMEOUT_S", raising=False)
    assert http_mod.idle_budget("local") == 300.0
    assert http_mod.idle_budget("cloud") == 90.0


def test_idle_budget_env_override_applies_to_both_classes(monkeypatch):
    # ORIONFOLD_TIMEOUT_S extends (does not replace) the budget: one knob overrides everyone.
    monkeypatch.setenv("ORIONFOLD_TIMEOUT_S", "45")
    assert http_mod.idle_budget("local") == 45.0
    assert http_mod.idle_budget("cloud") == 45.0
    # A garbage / non-positive override falls back to the per-class default.
    monkeypatch.setenv("ORIONFOLD_TIMEOUT_S", "garbage")
    assert http_mod.idle_budget("local") == 300.0
    monkeypatch.setenv("ORIONFOLD_TIMEOUT_S", "0")
    assert http_mod.idle_budget("cloud") == 90.0


def test_timeout_becomes_clean_timed_out_error(monkeypatch):
    # A read timeout must surface as a "timed out after Ns" row — not the generic "request
    # failed" message — so the operator sees the real reason a slow cell failed.
    def slow(url, json=None, headers=None, timeout=None):
        raise httpx.ReadTimeout("read timed out", request=httpx.Request("POST", url))

    monkeypatch.setattr(http_mod.httpx, "post", slow)
    result = safe_generate(OllamaProvider(), _example(), _candidate("ollama", "llama3.2"))
    assert result.error is not None
    assert "timed out after" in result.error
    assert "300" in result.error  # local idle budget reached
    assert "request failed" not in result.error


def test_connect_uses_short_backstop_while_read_is_generous(monkeypatch):
    # The absolute backstop: connect must happen quickly even when the read budget is generous,
    # so a black-holed host fails fast instead of burning the full local budget.
    captured: dict = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["timeout"] = timeout
        return httpx.Response(
            200,
            json={"message": {"content": "ok"}, "prompt_eval_count": 1, "eval_count": 1},
            request=httpx.Request("POST", url),
        )

    monkeypatch.delenv("ORIONFOLD_TIMEOUT_S", raising=False)
    monkeypatch.setattr(http_mod.httpx, "post", fake_post)
    OllamaProvider().generate(_example(), _candidate("ollama", "llama3.2"))
    timeout = captured["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.connect == 10.0  # absolute connect backstop
    assert timeout.read == 300.0  # generous local idle budget


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


def test_system_prompt_for_falls_back_to_task_default():
    from orionfold.providers.http import TASK_SYSTEM_PROMPT, system_prompt_for

    assert system_prompt_for(_candidate("ollama", "llama3.2")) == TASK_SYSTEM_PROMPT
    custom = Candidate(id="x", label="x", provider_id="ollama", model="llama3.2",
                       system_prompt="Be terse.")
    assert system_prompt_for(custom) == "Be terse."


def test_providers_send_the_candidates_system_prompt(monkeypatch):
    # Each provider must put the candidate's system_prompt on the wire when set, in the
    # provider-specific slot. Capture the outgoing payload for all four wire shapes.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    captured: dict = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.clear()
        captured.update(json or {})
        body = {
            "content": [{"type": "text", "text": "ok"}], "usage": {"input_tokens": 1, "output_tokens": 1},
            "choices": [{"message": {"content": "ok"}}], "usage_openai": {},
            "candidates": [{"content": {"parts": [{"text": "ok"}]}}], "usageMetadata": {},
            "message": {"content": "ok"}, "prompt_eval_count": 1, "eval_count": 1,
        }
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(http_mod.httpx, "post", fake_post)

    def cand(pid: str, m: str) -> Candidate:
        return Candidate(id="v", label="v", provider_id=pid, model=m, system_prompt="VARIANT-SYS-PROMPT")

    AnthropicProvider().generate(_example(), cand("anthropic", "claude-haiku-4-5"))
    assert captured["system"] == "VARIANT-SYS-PROMPT"

    OpenAICompatibleProvider(id="openai", label="OpenAI", base_url="https://api.openai.com/v1",
                             default_model="gpt-4o-mini", key_name="OPENAI_API_KEY").generate(
        _example(), cand("openai", "gpt-4o-mini"))
    assert captured["messages"][0] == {"role": "system", "content": "VARIANT-SYS-PROMPT"}

    GeminiProvider().generate(_example(), cand("gemini", "gemini-2.5-flash"))
    assert captured["systemInstruction"]["parts"][0]["text"] == "VARIANT-SYS-PROMPT"

    OllamaProvider().generate(_example(), cand("ollama", "llama3.2"))
    assert captured["messages"][0] == {"role": "system", "content": "VARIANT-SYS-PROMPT"}
