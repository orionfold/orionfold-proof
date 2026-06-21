"""Shared HTTP plumbing for the real providers (Gate 6, ADR-0002).

A single non-streaming JSON POST is all any provider needs — one example in, one completion
out. Keeping it here (rather than a per-provider client) means every provider crosses the
``safe_generate`` boundary the same way: a non-2xx status or a transport failure becomes a
``ProviderError`` carrying a **message only** (status + body, never headers or a key), which
``safe_generate`` then redacts. Latency is measured around the call so the leaderboard has a
real number even when the body omits one.
"""

from __future__ import annotations

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

    Raises :class:`ProviderError` on a timeout (``"{provider} timed out after {n}s"``), a non-2xx
    response (``"{provider} HTTP {status}: {short body}"``), or any other transport error — all
    terse, with nothing sensitive that redaction would need to catch.
    """
    budget = idle_budget(privacy) if timeout is None else timeout
    request_timeout = httpx.Timeout(budget, connect=min(_CONNECT_BACKSTOP_S, budget))
    start = time.monotonic()
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=request_timeout)
    except httpx.TimeoutException as exc:
        raise ProviderError(f"{provider} timed out after {budget:.0f}s") from exc
    except httpx.HTTPError as exc:
        raise ProviderError(f"{provider} request failed: {type(exc).__name__}") from exc
    latency_ms = int((time.monotonic() - start) * 1000)

    if response.status_code >= 400:
        body = _scrub_error_body(response.text[:_MAX_ERROR_BODY].strip(), headers)
        raise ProviderError(f"{provider} HTTP {response.status_code}: {body}")

    try:
        data = response.json()
    except ValueError as exc:
        raise ProviderError(f"{provider} returned non-JSON response") from exc
    return data, latency_ms


def build_result(
    *,
    provider_id: str,
    model: str,
    text: str,
    latency_ms: int,
    input_tokens: int,
    output_tokens: int,
    privacy: Privacy,
) -> ProviderResult:
    """Assemble the uniform :class:`ProviderResult` every real provider returns.

    ``raw_metadata`` carries only the provider id and model — never a key. Cost is estimated
    (``0.0`` for local/unknown models) and always labeled estimated downstream.
    """
    return ProviderResult(
        output_text=text,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimate_cost(model, input_tokens, output_tokens),
        privacy=privacy,
        raw_metadata={"provider": provider_id, "model": model},
    )
