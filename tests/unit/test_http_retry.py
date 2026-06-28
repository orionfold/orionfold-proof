"""Transient-failure retry for the shared provider HTTP layer (dogfood backlog #1).

A single 429 / 5xx / dropped connection on a paid multi-candidate run should get a bounded,
backed-off retry rather than wasting that cell. The rules (the load-bearing distinctions):

- Retry **only** transient failures: 429, 502/503/504, and connection-level transport errors.
- **Never** retry a read-timeout (a slow-but-working model — that is what the generous budget
  is for), nor a deterministic 4xx≠429 (400/401/404 — retrying wastes the buyer's money).
- Bounded: ``max_retries()`` attempts of backoff, env-configurable (``ORIONFOLD_MAX_RETRIES``),
  honoring a 429 ``Retry-After``, capped.

The sleep is injected via ``_sleep`` so these tests are deterministic and never actually wait.
"""

from __future__ import annotations

import httpx
import pytest

from orionfold.providers import http as http_mod


@pytest.fixture(autouse=True)
def _hermetic(tmp_path, monkeypatch):
    """No .env.local, default retry budget, and a no-op sleep so tests never block."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ORIONFOLD_MAX_RETRIES", raising=False)
    monkeypatch.delenv("ORIONFOLD_TIMEOUT_S", raising=False)
    monkeypatch.setattr(http_mod, "_sleep", lambda _seconds: None)


def _ok_response(url: str) -> httpx.Response:
    return httpx.Response(200, json={"ok": True}, request=httpx.Request("POST", url))


def _post(**kw):
    """Call ``post_json`` with throwaway args; the test controls the stubbed ``httpx.post``."""
    return http_mod.post_json(
        "https://api.example/v1/x",
        payload={"p": 1},
        headers={"content-type": "application/json"},
        provider="prov",
        privacy="cloud",
        **kw,
    )


# --- max_retries() env knob -------------------------------------------------------------


def test_max_retries_defaults_to_two(monkeypatch):
    assert http_mod.max_retries() == 2


def test_max_retries_env_override(monkeypatch):
    monkeypatch.setenv("ORIONFOLD_MAX_RETRIES", "4")
    assert http_mod.max_retries() == 4


def test_max_retries_zero_disables(monkeypatch):
    monkeypatch.setenv("ORIONFOLD_MAX_RETRIES", "0")
    assert http_mod.max_retries() == 0


def test_max_retries_garbage_and_negative_fall_back(monkeypatch):
    monkeypatch.setenv("ORIONFOLD_MAX_RETRIES", "nonsense")
    assert http_mod.max_retries() == 2
    monkeypatch.setenv("ORIONFOLD_MAX_RETRIES", "-3")
    assert http_mod.max_retries() == 2


# --- transient retry succeeds -----------------------------------------------------------


def test_retries_a_429_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def flaky(url, json=None, headers=None, timeout=None):  # noqa: A002 - mirrors httpx
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, text="rate limited", request=httpx.Request("POST", url))
        return _ok_response(url)

    monkeypatch.setattr(http_mod.httpx, "post", flaky)
    data, _latency = _post()
    assert data == {"ok": True}
    assert calls["n"] == 2  # one retry consumed


@pytest.mark.parametrize("status", [502, 503, 504])
def test_retries_5xx_then_succeeds(monkeypatch, status):
    calls = {"n": 0}

    def flaky(url, json=None, headers=None, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(status, text="upstream", request=httpx.Request("POST", url))
        return _ok_response(url)

    monkeypatch.setattr(http_mod.httpx, "post", flaky)
    data, _ = _post()
    assert data == {"ok": True}
    assert calls["n"] == 2


def test_retries_a_connect_error_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def flaky(url, json=None, headers=None, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("refused", request=httpx.Request("POST", url))
        return _ok_response(url)

    monkeypatch.setattr(http_mod.httpx, "post", flaky)
    data, _ = _post()
    assert data == {"ok": True}
    assert calls["n"] == 2


# --- exhaustion raises ------------------------------------------------------------------


def test_persistent_503_exhausts_retries_and_raises(monkeypatch):
    calls = {"n": 0}

    def down(url, json=None, headers=None, timeout=None):
        calls["n"] += 1
        return httpx.Response(503, text="unavailable", request=httpx.Request("POST", url))

    monkeypatch.setattr(http_mod.httpx, "post", down)
    with pytest.raises(http_mod.ProviderError) as exc:
        _post()
    assert "HTTP 503" in str(exc.value)
    assert calls["n"] == 3  # initial + 2 retries (default)


def test_persistent_connect_error_exhausts_and_raises(monkeypatch):
    calls = {"n": 0}

    def down(url, json=None, headers=None, timeout=None):
        calls["n"] += 1
        raise httpx.ConnectError("refused", request=httpx.Request("POST", url))

    monkeypatch.setattr(http_mod.httpx, "post", down)
    with pytest.raises(http_mod.ProviderError):
        _post()
    assert calls["n"] == 3


# --- non-transient: never retried -------------------------------------------------------


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_deterministic_4xx_is_never_retried(monkeypatch, status):
    calls = {"n": 0}

    def reject(url, json=None, headers=None, timeout=None):
        calls["n"] += 1
        return httpx.Response(status, text="nope", request=httpx.Request("POST", url))

    monkeypatch.setattr(http_mod.httpx, "post", reject)
    with pytest.raises(http_mod.ProviderError):
        _post()
    assert calls["n"] == 1  # single attempt — no money wasted retrying a deterministic error


def test_read_timeout_is_never_retried(monkeypatch):
    # A slow-but-working model must not be retried: the generous read budget already covers it,
    # and a retry would double both the wait and (for paid models) the spend.
    calls = {"n": 0}

    def slow(url, json=None, headers=None, timeout=None):
        calls["n"] += 1
        raise httpx.ReadTimeout("read timed out", request=httpx.Request("POST", url))

    monkeypatch.setattr(http_mod.httpx, "post", slow)
    with pytest.raises(http_mod.ProviderError) as exc:
        _post()
    assert "timed out after" in str(exc.value)
    assert calls["n"] == 1


def test_max_retries_zero_means_single_attempt(monkeypatch):
    monkeypatch.setenv("ORIONFOLD_MAX_RETRIES", "0")
    calls = {"n": 0}

    def down(url, json=None, headers=None, timeout=None):
        calls["n"] += 1
        return httpx.Response(503, text="unavailable", request=httpx.Request("POST", url))

    monkeypatch.setattr(http_mod.httpx, "post", down)
    with pytest.raises(http_mod.ProviderError):
        _post()
    assert calls["n"] == 1  # retry disabled


# --- backoff shape ----------------------------------------------------------------------


def test_backoff_is_bounded_and_grows(monkeypatch):
    # Delays are non-negative, monotonically non-decreasing across attempts, and capped.
    d0 = http_mod._backoff_delay(0, retry_after=None)
    d1 = http_mod._backoff_delay(1, retry_after=None)
    d2 = http_mod._backoff_delay(2, retry_after=None)
    d_big = http_mod._backoff_delay(20, retry_after=None)
    assert 0.0 <= d0 <= d1 <= d2
    assert d_big <= http_mod._RETRY_CAP_S + http_mod._RETRY_BASE_S  # cap + max jitter
    assert d2 <= http_mod._RETRY_CAP_S + http_mod._RETRY_BASE_S


def test_retry_after_header_is_honored_and_capped(monkeypatch):
    # A 429 Retry-After (seconds) drives the delay, capped at _RETRY_CAP_S.
    assert http_mod._backoff_delay(0, retry_after=2.0) >= 2.0
    assert http_mod._backoff_delay(0, retry_after=10_000.0) <= http_mod._RETRY_CAP_S


def test_sleep_is_called_between_attempts(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr(http_mod, "_sleep", lambda s: slept.append(s))
    calls = {"n": 0}

    def flaky(url, json=None, headers=None, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, text="x", request=httpx.Request("POST", url))
        return _ok_response(url)

    monkeypatch.setattr(http_mod.httpx, "post", flaky)
    _post()
    assert len(slept) == 2  # slept before each of the 2 retries
    assert all(s >= 0 for s in slept)
