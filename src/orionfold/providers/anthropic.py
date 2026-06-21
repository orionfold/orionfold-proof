"""Anthropic provider — native Messages API ``POST /v1/messages`` (Gate 6, ADR-0002).

Wire shape per the bundled ``claude-api`` skill: ``x-api-key`` + ``anthropic-version`` headers,
``{model, max_tokens, system, messages}`` body, text in ``content[].text`` and tokens in
``usage.{input,output}_tokens``. The key is header-only and never logged. ``privacy="cloud"``.
The default model is a cheap, current model because the model here is the *subject under test*,
chosen by the operator; override with ``ORIONFOLD_ANTHROPIC_MODEL``.
"""

from __future__ import annotations

from orionfold.config.keys import resolve_key
from orionfold.domain.models import Candidate, Example, Privacy, ProviderResult
from orionfold.providers.http import (
    ProviderError,
    build_result,
    max_output_tokens,
    post_json,
    system_prompt_for,
)

DEFAULT_MODEL = "claude-haiku-4-5"
_URL = "https://api.anthropic.com/v1/messages"
_VERSION = "2023-06-01"
KEY_NAME = "ANTHROPIC_API_KEY"


class AnthropicProvider:
    id: str = "anthropic"
    label: str = "Anthropic"
    privacy: Privacy = "cloud"

    def __init__(self, default_model: str = DEFAULT_MODEL) -> None:
        self.default_model = default_model

    def generate(self, example: Example, candidate: Candidate) -> ProviderResult:
        model = candidate.model or self.default_model
        key = resolve_key(KEY_NAME)
        if key is None:
            raise ProviderError(f"{self.id}: {KEY_NAME} not set")
        payload = {
            "model": model,
            "max_tokens": max_output_tokens(),
            "system": system_prompt_for(candidate),
            "messages": [{"role": "user", "content": example.input_text}],
        }
        data, latency_ms = post_json(
            _URL,
            payload=payload,
            headers={
                "x-api-key": key,
                "anthropic-version": _VERSION,
                "content-type": "application/json",
            },
            provider=self.id,
            privacy=self.privacy,
        )
        blocks = data.get("content") or []
        text = "".join(
            b.get("text", "")
            for b in blocks
            if isinstance(b, dict) and b.get("type") == "text"
        )
        usage = data.get("usage") or {}
        return build_result(
            provider_id=self.id,
            model=model,
            text=text,
            latency_ms=latency_ms,
            input_tokens=int(usage.get("input_tokens", 0) or 0),
            output_tokens=int(usage.get("output_tokens", 0) or 0),
            privacy=self.privacy,
        )
