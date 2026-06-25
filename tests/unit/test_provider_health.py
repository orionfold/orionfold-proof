"""Provider health probe — classification, redaction, and the /api/health/providers endpoint.

All probes are exercised keyless via a stubbed ``httpx.get``: no live provider, no tokens spent.
The probe must never raise, never echo a credential, and map each HTTP status to the right
``HealthStatus`` so the cockpit can gray out a failing candidate with the right remediation.
"""

from __future__ import annotations

import httpx
import pytest

from orionfold.providers import health as health_mod
from orionfold.providers.health import probe_provider


class _Resp:
    """A canned httpx response with just the fields the probe reads."""

    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


def _stub_get(monkeypatch, *, status: int, text: str = "") -> None:
    monkeypatch.setattr(health_mod.httpx, "get", lambda url, **kw: _Resp(status, text))


def _stub_get_raises(monkeypatch, exc: Exception) -> None:
    def fake_get(url, **kw):  # noqa: ANN001
        raise exc

    monkeypatch.setattr(health_mod.httpx, "get", fake_get)


# A cloud provider id that is always probeable via the OpenAI-compatible path once a key resolves.
# We force its key in via the env so the registry offers it, then stub the network.
@pytest.fixture
def openai_available(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-a-real-key-000000")
    # Keep .env.local out of the picture so resolution is deterministic.
    monkeypatch.setenv("ORIONFOLD_ENV_FILE", "/dev/null")
    return "openai"


# --- mocks are always healthy, no network -----------------------------------------------------


def test_mock_providers_always_ok(monkeypatch):
    # Even if the network would fail, mocks never touch it.
    _stub_get_raises(monkeypatch, httpx.ConnectError("boom"))
    for pid in ("mock_good", "mock_bad"):
        result = probe_provider(pid)
        assert result.status == "ok"
        assert result.remediation == ""


def test_unknown_provider_is_unreachable():
    result = probe_provider("does-not-exist")
    assert result.status == "unreachable"
    assert "not" in result.message.lower()


# --- status-code classification (cloud) -------------------------------------------------------


@pytest.mark.parametrize(
    "code, expected",
    [
        (200, "ok"),
        (204, "ok"),
        (401, "auth"),
        (403, "permission"),
        (429, "quota"),
        (500, "down"),
        (503, "down"),
        (529, "down"),
        (404, "down"),  # unexpected on a metadata GET → reachable-but-degraded
    ],
)
def test_cloud_status_classification(monkeypatch, openai_available, code, expected):
    _stub_get(monkeypatch, status=code, text="{}")
    result = probe_provider("openai")
    assert result.status == expected
    if expected == "ok":
        assert result.remediation == ""
    else:
        assert result.remediation  # every failure has actionable copy


def test_auth_remediation_names_the_key_var(monkeypatch, openai_available):
    _stub_get(monkeypatch, status=401, text='{"error":"invalid key"}')
    result = probe_provider("openai")
    assert "OPENAI_API_KEY" in result.remediation


# --- the credential never escapes -------------------------------------------------------------


def test_credential_is_scrubbed_from_error_body(monkeypatch, openai_available):
    # The provider echoes the key back in an error body (worst case). It must be redacted.
    leaked = "sk-test-not-a-real-key-000000"
    _stub_get(monkeypatch, status=401, text=f'{{"error":"bad key {leaked}"}}')
    result = probe_provider("openai")
    assert leaked not in result.message
    assert "[redacted]" in result.message


def test_custom_format_key_scrubbed_even_at_truncation_boundary(monkeypatch):
    # Regression (security review): a non-sk-/AIza key echoed PAST the 300-char truncation point
    # must still be fully scrubbed. We scrub before truncating, so the literal-key match always
    # sees the intact value regardless of where it lands in the body. Use a custom gateway base
    # URL with a non-standard token the regex redactor would NOT catch on its own.
    custom_key = "gateway_tok_abcdefghijklmnopqrstuvwxyz_0123456789"
    monkeypatch.setenv("OPENAI_API_KEY", custom_key)
    monkeypatch.setenv("OPENAI_BASE_URL", "http://malicious.example/v1")
    monkeypatch.setenv("ORIONFOLD_ENV_FILE", "/dev/null")
    # Pad so the echoed key starts near the truncation boundary (offset ~290).
    body = "x" * 290 + custom_key
    _stub_get(monkeypatch, status=401, text=body)
    result = probe_provider("openai")
    # Not even a fragment of the key may survive — no substring of length ≥ 8.
    assert custom_key not in result.message
    for i in range(0, len(custom_key) - 8):
        assert custom_key[i : i + 8] not in result.message


# --- connection failures are unreachable ------------------------------------------------------


def test_connect_error_is_unreachable(monkeypatch, openai_available):
    _stub_get_raises(monkeypatch, httpx.ConnectError("refused"))
    result = probe_provider("openai")
    assert result.status == "unreachable"


def test_timeout_is_unreachable(monkeypatch, openai_available):
    _stub_get_raises(monkeypatch, httpx.ConnectTimeout("slow"))
    result = probe_provider("openai")
    assert result.status == "unreachable"


# --- local providers get "start the server" remediation, not cloud copy -----------------------


def test_ollama_unreachable_says_start_the_daemon(monkeypatch):
    _stub_get_raises(monkeypatch, httpx.ConnectError("refused"))
    result = probe_provider("ollama")
    assert result.status == "unreachable"
    assert "ollama serve" in result.remediation


def test_lmstudio_unreachable_says_start_the_server(monkeypatch):
    _stub_get_raises(monkeypatch, httpx.ConnectError("refused"))
    result = probe_provider("lmstudio")
    assert result.status == "unreachable"
    assert "LM Studio" in result.remediation


def test_local_provider_ok_when_server_answers(monkeypatch):
    _stub_get(monkeypatch, status=200, text='{"models":[]}')
    result = probe_provider("ollama")
    assert result.status == "ok"


# --- the endpoint wires it together -----------------------------------------------------------


def test_health_endpoint_returns_a_row_per_provider(monkeypatch):
    from fastapi.testclient import TestClient

    from orionfold.server.app import create_app

    # Keyless: no cloud providers; stub the local probes so the test never hits the network.
    monkeypatch.setenv("ORIONFOLD_ENV_FILE", "/dev/null")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    _stub_get(monkeypatch, status=200, text='{"models":[]}')

    client = TestClient(create_app())
    response = client.get("/api/health/providers")
    assert response.status_code == 200
    rows = response.json()["providers"]
    by_id = {r["provider_id"]: r for r in rows}
    # Mocks + the two local profiles are always offered.
    assert by_id["mock_good"]["status"] == "ok"
    assert by_id["ollama"]["status"] == "ok"  # stubbed 200
    # No key material anywhere in the payload.
    blob = response.text
    assert "sk-" not in blob and "AIza" not in blob
