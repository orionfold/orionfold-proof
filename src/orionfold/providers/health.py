"""Provider health probe — is each active provider actually reachable and authorized?

The registry only knows whether a *key is present* (cloud) or a local profile is offered; it
performs no liveness check. This module adds one: a cheap, **token-free** request per provider
that distinguishes a working provider from one that is down, rate-limited, billing-blocked, or
holding a revoked key — so the cockpit can gray out a candidate that would fail at run time and
tell the operator exactly what to fix.

Design constraints (see ``.claude/rules/providers.md``):

- **No tokens spent.** Every cloud probe hits a free metadata endpoint (``GET .../models``),
  never a generation endpoint. Local probes reuse the daemon's tags/models listing.
- **No exception crosses the boundary** and **no key material escapes.** Like ``safe_generate``,
  a probe always returns a :class:`HealthResult`; any error message is run through the same
  literal-key scrub + ``redact_secrets`` redactor used by the run path.
- **Provider-shaped auth.** Each cloud probe sends the same auth header its ``generate`` uses,
  so a 401 here means the same key would 401 on a real run. The resolved credential is held in
  a local ``cred`` variable only long enough to build the request header; it is never returned,
  logged, or written into a HealthResult.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import httpx

from orionfold.config.keys import CLOUD_KEY_NAMES, resolve_key
from orionfold.providers import gemini as _gemini
from orionfold.providers.base import redact_secrets
from orionfold.providers.ollama_pull import resolve_host as _ollama_host
from orionfold.providers.registry import _build

# A health probe is a quick liveness check, not a run cell — keep it snappy so the cockpit's
# on-load check doesn't stall behind a slow provider. Connect is capped shorter so a black-holed
# host fails fast.
_PROBE_READ_S = 6.0
_PROBE_CONNECT_S = 4.0

# The probe outcome, narrow enough that the UI can map each to a fixed remediation.
HealthStatus = Literal["ok", "auth", "permission", "quota", "down", "unreachable"]

_MAX_ERROR_BODY = 300


@dataclass(frozen=True)
class HealthResult:
    """One provider's probe outcome. ``message``/``remediation`` are safe to show and log."""

    provider_id: str
    status: HealthStatus
    message: str
    remediation: str


# Per-status remediation copy. Phrased for the operator; the cloud variants get the provider's
# key-var name spliced in by ``_cloud_remediation`` so the message names the exact thing to fix.
_LOCAL_REMEDIATION = {
    "ollama": "Start the Ollama daemon with `ollama serve`, then recheck.",
    "lmstudio": "Start LM Studio and load a model (Local Server tab), then recheck.",
}


def _cloud_remediation(provider_id: str, status: HealthStatus) -> str:
    key = CLOUD_KEY_NAMES.get(provider_id, "the API key")
    if status == "auth":
        return f"Key invalid or revoked. Check `{key}` in your environment or .env.local."
    if status == "permission":
        return f"Key lacks access to this model or org. Review the permissions on `{key}`."
    if status == "quota":
        return "Quota or rate limit hit (billing may be exhausted). Retry shortly, or check your plan."
    if status == "down":
        return "The provider's API is unavailable right now. Try again in a few minutes."
    return "Could not reach the provider. Check your network connection, then recheck."


def _scrub(text: str, cred: str | None) -> str:
    """Strip a literal in-flight credential (belt) then apply the regex redactor (suspenders)."""
    scrubbed = text
    if cred:
        scrubbed = scrubbed.replace(cred, "[redacted]")
    return redact_secrets(scrubbed)


def _classify_status_code(code: int) -> HealthStatus:
    """Map an HTTP status from a metadata probe to a health status."""
    if code < 400:
        return "ok"
    if code == 401:
        return "auth"
    if code == 403:
        return "permission"
    if code == 429:
        return "quota"
    if code >= 500:
        return "down"
    # A 400/404/etc. on a plain metadata GET is unexpected but means the endpoint answered with
    # a usable key — treat as reachable-but-degraded "down" so the operator sees something is off
    # without us inventing a brand-new status.
    return "down"


def _probe_url(
    *, provider_id: str, url: str, headers: dict[str, str], cred: str | None
) -> HealthResult:
    """GET ``url`` with ``headers`` and classify the outcome into a HealthResult.

    Connection failures are ``unreachable``; status codes classify auth/quota/etc. Never raises
    and never echoes a credential (``cred`` is scrubbed from any error body).
    """
    timeout = httpx.Timeout(_PROBE_READ_S, connect=_PROBE_CONNECT_S)
    try:
        # follow_redirects stays False (httpx's default, pinned explicitly): the probe carries the
        # credential in its header, so a malicious provider must never be able to 302 it to an
        # attacker-controlled host. Do not flip this on.
        response = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=False)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.TimeoutException):
        return HealthResult(
            provider_id=provider_id,
            status="unreachable",
            message="Could not reach the provider endpoint.",
            remediation=_cloud_remediation(provider_id, "unreachable"),
        )
    except httpx.HTTPError as exc:
        return HealthResult(
            provider_id=provider_id,
            status="unreachable",
            message=f"Request failed: {type(exc).__name__}",
            remediation=_cloud_remediation(provider_id, "unreachable"),
        )
    status = _classify_status_code(response.status_code)
    if status == "ok":
        return HealthResult(provider_id, "ok", "Reachable and authorized.", "")
    # Scrub the FULL body first, then truncate — never the reverse. Truncating first could cut an
    # echoed key in half at the 300-char boundary so the literal `cred` scrub no longer matches it,
    # leaking a fragment for key formats the regex redactor doesn't recognize. The literal scrub on
    # the untruncated body is the load-bearing defense for non-standard (non-sk-/AIza) keys.
    body = _scrub(response.text, cred)[:_MAX_ERROR_BODY].strip()
    return HealthResult(
        provider_id=provider_id,
        status=status,
        message=f"HTTP {response.status_code}: {body}" if body else f"HTTP {response.status_code}",
        remediation=_cloud_remediation(provider_id, status),
    )


def _probe_openai_compatible(provider_id: str) -> HealthResult:
    """Probe an OpenAI-compatible profile (openai/openrouter/lmstudio) via ``GET {base}/models``.

    The base URL and key-var come from the live registry entry, so this tracks any env override
    (OPENAI_BASE_URL, LMSTUDIO_BASE_URL, …) exactly as ``generate`` would.
    """
    provider = _build()[provider_id][0]
    base_url = getattr(provider, "base_url", "").rstrip("/")
    key_name = getattr(provider, "key_name", None)
    headers = {"content-type": "application/json"}
    cred: str | None = None
    if key_name is not None:
        cred = resolve_key(key_name)
        if cred is None:
            # Should not happen (registry gates cloud on key presence), but be explicit.
            return HealthResult(
                provider_id, "auth", f"{key_name} not set",
                _cloud_remediation(provider_id, "auth"),
            )
        headers["Authorization"] = f"Bearer {cred}"
    result = _probe_url(
        provider_id=provider_id, url=f"{base_url}/models", headers=headers, cred=cred
    )
    # Local keyless profiles get local remediation copy (start the server) instead of cloud copy.
    if key_name is None and result.status in ("unreachable", "down"):
        return HealthResult(
            provider_id=provider_id,
            status="unreachable",
            message=result.message,
            remediation=_LOCAL_REMEDIATION.get(
                provider_id, "Start the local server, then recheck."
            ),
        )
    return result


def _probe_anthropic() -> HealthResult:
    """Probe Anthropic via the free ``GET /v1/models`` list endpoint (no tokens spent)."""
    cred = resolve_key("ANTHROPIC_API_KEY")
    if cred is None:
        return HealthResult(
            "anthropic", "auth", "ANTHROPIC_API_KEY not set",
            _cloud_remediation("anthropic", "auth"),
        )
    return _probe_url(
        provider_id="anthropic",
        url="https://api.anthropic.com/v1/models",
        headers={"x-api-key": cred, "anthropic-version": "2023-06-01"},
        cred=cred,
    )


def _probe_gemini() -> HealthResult:
    """Probe Gemini via the free model-list endpoint, credential in the ``x-goog-api-key`` header."""
    cred = resolve_key("GEMINI_API_KEY")
    if cred is None:
        return HealthResult(
            "gemini", "auth", "GEMINI_API_KEY not set", _cloud_remediation("gemini", "auth")
        )
    # `_gemini._BASE` is the per-model base (".../v1beta/models"); GET-ing it lists models.
    return _probe_url(
        provider_id="gemini",
        url=_gemini._BASE,
        headers={"x-goog-api-key": cred},
        cred=cred,
    )


def _probe_ollama() -> HealthResult:
    """Probe the local Ollama daemon via ``GET {host}/api/tags`` (its existing liveness check)."""
    host = _ollama_host()
    result = _probe_url(provider_id="ollama", url=f"{host}/api/tags", headers={}, cred=None)
    if result.status in ("unreachable", "down"):
        return HealthResult("ollama", "unreachable", result.message, _LOCAL_REMEDIATION["ollama"])
    return result


def probe_provider(provider_id: str) -> HealthResult:
    """Probe one currently-active provider and return its :class:`HealthResult`.

    Mocks are always healthy (no network). Cloud/local providers each hit their cheapest
    token-free endpoint. Unknown / unavailable ids report ``unreachable`` rather than raising.
    """
    registry = _build()
    if provider_id not in registry:
        return HealthResult(
            provider_id, "unreachable", "Provider not currently available.",
            "This provider is not configured; add its key or start its server.",
        )
    if provider_id in ("mock_good", "mock_bad"):
        return HealthResult(provider_id, "ok", "Deterministic mock — always available.", "")
    if provider_id == "anthropic":
        return _probe_anthropic()
    if provider_id == "gemini":
        return _probe_gemini()
    if provider_id == "ollama":
        return _probe_ollama()
    # openai, openrouter, lmstudio — all OpenAI-compatible.
    return _probe_openai_compatible(provider_id)


def probe_all() -> list[HealthResult]:
    """Probe every currently-active provider concurrently and return one result each.

    Cloud probes run in parallel (independent network calls); the list is ordered to match the
    registry's insertion order so the UI can zip results to provider groups.
    """
    from concurrent.futures import ThreadPoolExecutor

    provider_ids = list(_build().keys())
    # Bounded pool: a handful of providers at most, but cap so a future provider explosion can't
    # spawn an unbounded thread count.
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(provider_ids)))) as pool:
        results = list(pool.map(probe_provider, provider_ids))
    return results
