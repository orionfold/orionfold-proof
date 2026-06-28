"""Shared HTTP plumbing for the real providers (Gate 6, ADR-0002).

A single non-streaming JSON POST is all any provider needs — one example in, one completion
out. Keeping it here (rather than a per-provider client) means every provider crosses the
``safe_generate`` boundary the same way: a non-2xx status or a transport failure becomes a
``ProviderError`` carrying a **message only** (status + body, never headers or a key), which
``safe_generate`` then redacts. Latency is measured around the call so the leaderboard has a
real number even when the body omits one.
"""

from __future__ import annotations

import random
import time
from typing import Any

import httpx

from orionfold.config.keys import resolve
from orionfold.domain.models import Candidate, Privacy, ProviderResult
from orionfold.providers.base import redact_secrets
from orionfold.providers.pricing import estimate_cost

# Per-provider-class idle budget: the window one cell has to complete before it fails as a
# timed-out row (ADR-0003 follow-up). Because cells run sequentially, "no cell completes within
# the budget" is just "this cell's HTTP call exceeded the budget" — so the budget is the
# per-request read timeout, tuned by class. Local is generous (a cold model load + slow
# generation on qwen3/deepseek-r1 can run minutes); cloud is tighter (a hosted call idle this
# long is wedged, not working).
_LOCAL_IDLE_S = 300.0
_CLOUD_IDLE_S = 90.0
# Absolute backstop: the connection itself must be established quickly even when the read budget
# is generous, so a black-holed host (wrong OLLAMA_HOST, dropped route) fails fast instead of
# burning the full local budget. Independent of the idle budget by design.
_CONNECT_BACKSTOP_S = 10.0


# Transient-failure retry (dogfood backlog #1). A single 429 / 5xx / dropped connection on a
# paid multi-candidate run should get a bounded, backed-off retry rather than wasting that cell.
# We retry ONLY transient failures — never a deterministic 4xx≠429 (retrying a 400/401/404 wastes
# the buyer's money) and never a read-timeout (a slow-but-working model — that is exactly what the
# generous idle budget is for; a retry would double both the wait and the spend).
_DEFAULT_MAX_RETRIES = 2
_RETRY_BASE_S = 0.5
_RETRY_CAP_S = 8.0
# HTTP statuses worth a second chance: rate-limit + the transient gateway/upstream 5xx family.
_RETRYABLE_STATUSES = frozenset({429, 502, 503, 504})


def _sleep(seconds: float) -> None:
    """Backoff sleep, isolated behind a seam so tests run instantly (they stub this out)."""
    time.sleep(seconds)


def max_retries() -> int:
    """Transient-failure retry count; ``ORIONFOLD_MAX_RETRIES`` overrides the default (2).

    ``0`` disables retry (a single attempt). A garbage or negative value falls back to the
    default — mirrors the ``ORIONFOLD_MAX_TOKENS`` / ``ORIONFOLD_TIMEOUT_S`` env-knob pattern.
    """
    try:
        value = int(resolve("ORIONFOLD_MAX_RETRIES", str(_DEFAULT_MAX_RETRIES)))
    except ValueError:
        return _DEFAULT_MAX_RETRIES
    return value if value >= 0 else _DEFAULT_MAX_RETRIES


def _is_transient_status(status: int) -> bool:
    """True only for statuses a retry could plausibly fix (rate-limit + transient 5xx)."""
    return status in _RETRYABLE_STATUSES


def _is_transient_exc(exc: httpx.HTTPError) -> bool:
    """True for connection-level transport failures (refused / reset / connect-timeout / pool).

    Deliberately EXCLUDES :class:`httpx.ReadTimeout` — a read that exhausts the budget means the
    model is genuinely slow, not flaky, so retrying it is wrong (and, for a paid model, costly).
    """
    if isinstance(exc, httpx.ReadTimeout):
        return False
    return isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.TransportError))


def _backoff_delay(attempt: int, *, retry_after: float | None) -> float:
    """Bounded exponential backoff with jitter for retry ``attempt`` (0-based).

    A 429's ``Retry-After`` (seconds) takes precedence when present (capped at ``_RETRY_CAP_S``);
    otherwise ``base * 2**attempt`` capped at ``_RETRY_CAP_S``, plus ``[0, base)`` jitter so many
    cells retrying at once don't synchronize into a thundering herd.
    """
    if retry_after is not None and retry_after > 0:
        return min(retry_after, _RETRY_CAP_S)
    backoff = min(_RETRY_CAP_S, _RETRY_BASE_S * (2**attempt))
    return backoff + random.uniform(0, _RETRY_BASE_S)


def _parse_retry_after(response: httpx.Response) -> float | None:
    """The ``Retry-After`` header in seconds form, if the server sent a numeric one."""
    raw = response.headers.get("retry-after")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None  # HTTP-date form is not worth parsing for a sub-10s backoff cap


def idle_budget(privacy: Privacy) -> float:
    """Per-cell idle budget in seconds for a provider of the given ``privacy`` class.

    ``ORIONFOLD_TIMEOUT_S`` is the single global override (it *extends*, not replaces, the
    per-class defaults — one knob still wins for everyone); otherwise local gets the generous
    budget and cloud the tighter one. A garbage or non-positive override falls back to the
    class default.
    """
    override = resolve("ORIONFOLD_TIMEOUT_S", "").strip()
    if override:
        try:
            value = float(override)
        except ValueError:
            value = 0.0
        if value > 0:
            return value
    return _LOCAL_IDLE_S if privacy == "local" else _CLOUD_IDLE_S


# Cap echoed error bodies so a provider can't flood a receipt/log; redaction still applies.
_MAX_ERROR_BODY = 500
# Header names whose values carry a credential we must never echo back in an error.
_SECRET_HEADERS = ("authorization", "x-api-key", "x-goog-api-key")


def _scrub_error_body(body: str, headers: dict[str, str]) -> str:
    """Strip any submitted credential from an error body, then apply the regex redactor.

    Removing the *literal* in-flight key value guarantees coverage even for an unlabeled
    custom-gateway token the regex wouldn't recognize; ``redact_secrets`` then catches anything
    echoed from the provider side that we never held.
    """
    scrubbed = body
    for name, value in headers.items():
        if name.lower() in _SECRET_HEADERS and value:
            # "Authorization: Bearer <token>" → strip the token, not the scheme word.
            secret = value.split(" ", 1)[1] if " " in value else value
            if secret:
                scrubbed = scrubbed.replace(secret, "[redacted]")
    return redact_secrets(scrubbed)

# Task-agnostic instruction shared by every real provider. v0 sends the example's input as the
# user turn with this nudge so a real model attempts the task tersely instead of chattering;
# per-Proof-Brief prompt templating is deferred (see ADR-0002).
TASK_SYSTEM_PROMPT = (
    "Complete the task implied by the input. Respond with only the result — no preamble, "
    "labels, or explanation."
)


def system_prompt_for(candidate: Candidate) -> str:
    """The system prompt for a run cell: the candidate's variant, else the global default."""
    return candidate.system_prompt or TASK_SYSTEM_PROMPT


# Output cap per completion. The default leaves room for a short answer; reasoning models
# (qwen3, deepseek-r1, gpt-oss, …) spend the budget *thinking* and can return empty content at
# a low cap, so it's env-overridable with ORIONFOLD_MAX_TOKENS (raise it for those models).
_DEFAULT_MAX_TOKENS = 2048


def max_output_tokens() -> int:
    """Per-completion output cap; ``ORIONFOLD_MAX_TOKENS`` overrides the default."""
    try:
        value = int(resolve("ORIONFOLD_MAX_TOKENS", str(_DEFAULT_MAX_TOKENS)))
    except ValueError:
        return _DEFAULT_MAX_TOKENS
    return value if value > 0 else _DEFAULT_MAX_TOKENS


class ProviderError(RuntimeError):
    """A real-provider call failed. Message only — no key material, redacted at the boundary."""


def post_json(
    url: str,
    *,
    payload: dict[str, Any],
    headers: dict[str, str],
    provider: str,
    privacy: Privacy = "cloud",
    timeout: float | None = None,
) -> tuple[dict[str, Any], int]:
    """POST ``payload`` as JSON and return ``(parsed_json, latency_ms)``.

    The ``privacy`` class selects the per-cell idle budget (local generous, cloud tighter);
    an explicit ``timeout`` overrides it. Connect is capped at the short absolute backstop so
    an unreachable host fails fast regardless of the read budget.

    A transient failure (429, 502/503/504, or a connection-level transport error) is retried up
    to ``max_retries()`` times with bounded exponential backoff + jitter; a 429 ``Retry-After`` is
    honored (capped). A read-timeout and a deterministic 4xx≠429 are NEVER retried.

    Raises :class:`ProviderError` on a timeout (``"{provider} timed out after {n}s"``), a non-2xx
    response (``"{provider} HTTP {status}: {short body}"``), or any other transport error — all
    terse, with nothing sensitive that redaction would need to catch. On exhaustion, the LAST
    failure's error is raised (so the operator sees the final real reason the cell failed).
    """
    budget = idle_budget(privacy) if timeout is None else timeout
    request_timeout = httpx.Timeout(budget, connect=min(_CONNECT_BACKSTOP_S, budget))
    retries = max_retries()
    start = time.monotonic()
    for attempt in range(retries + 1):
        retry_after: float | None = None
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=request_timeout)
        except httpx.TimeoutException as exc:
            # ReadTimeout is non-transient (slow model, not flaky); a connect-timeout retries.
            if _is_transient_exc(exc) and attempt < retries:
                _sleep(_backoff_delay(attempt, retry_after=None))
                continue
            raise ProviderError(f"{provider} timed out after {budget:.0f}s") from exc
        except httpx.HTTPError as exc:
            if _is_transient_exc(exc) and attempt < retries:
                _sleep(_backoff_delay(attempt, retry_after=None))
                continue
            raise ProviderError(f"{provider} request failed: {type(exc).__name__}") from exc

        if response.status_code >= 400:
            if _is_transient_status(response.status_code) and attempt < retries:
                retry_after = _parse_retry_after(response)
                _sleep(_backoff_delay(attempt, retry_after=retry_after))
                continue
            body = _scrub_error_body(response.text[:_MAX_ERROR_BODY].strip(), headers)
            raise ProviderError(f"{provider} HTTP {response.status_code}: {body}")

        latency_ms = int((time.monotonic() - start) * 1000)
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError(f"{provider} returned non-JSON response") from exc
        return data, latency_ms

    # Unreachable: the loop either returns on success or raises on the terminal attempt.
    raise ProviderError(f"{provider} request failed: retries exhausted")  # pragma: no cover


def build_result(
    *,
    provider_id: str,
    model: str,
    text: str,
    latency_ms: int,
    input_tokens: int,
    output_tokens: int,
    privacy: Privacy,
    actual_cost_usd: float | None = None,
) -> ProviderResult:
    """Assemble the uniform :class:`ProviderResult` every real provider returns.

    ``raw_metadata`` carries only the provider id and model — never a key. Cost is the provider's
    **real** billed cost when it reports one (``actual_cost_usd`` — OpenRouter returns it in
    ``usage.cost``); otherwise it falls back to the static estimate table (``0.0`` for
    local/unknown models). This is why a custom OpenRouter model id still reports a true cost
    rather than a misleading ``0.0`` (the estimate table can't cover arbitrary ids).
    """
    cost = (
        actual_cost_usd
        if actual_cost_usd is not None
        else estimate_cost(model, input_tokens, output_tokens)
    )
    return ProviderResult(
        output_text=text,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=cost,
        privacy=privacy,
        raw_metadata={"provider": provider_id, "model": model},
    )
