"""OpenAI-compatible provider — ``POST {base_url}/chat/completions`` (Gate 6, ADR-0002).

One class, configured per candidate, serves three profiles that all speak the same wire
format: OpenAI, OpenRouter (both hosted, keyed), and LM Studio (local, keyless). The key (when
required) goes in the ``Authorization`` header and is never logged; a non-2xx error is raised
as a terse :class:`ProviderError` and redacted at the boundary.
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


class OpenAICompatibleProvider:
    """A candidate backed by an OpenAI-compatible ``/chat/completions`` endpoint."""

    def __init__(
        self,
        *,
        id: str,
        label: str,
        base_url: str,
        default_model: str,
        key_name: str | None = None,
        privacy: Privacy = "cloud",
        token_param: str = "max_tokens",
    ) -> None:
        self.id = id
        self.label = label
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.key_name = key_name  # None → keyless (LM Studio)
        self.privacy: Privacy = privacy
        # Output-cap field name. OpenAI's GPT-5.x rejects "max_tokens" (HTTP 400) and requires
        # "max_completion_tokens"; OpenRouter + LM Studio keep the original. One knob per profile.
        self.token_param = token_param

    def generate(self, example: Example, candidate: Candidate) -> ProviderResult:
        model = candidate.model or self.default_model
        headers = {"content-type": "application/json"}
        if self.key_name is not None:
            key = resolve_key(self.key_name)
            if key is None:
                raise ProviderError(f"{self.id}: {self.key_name} not set")
            headers["Authorization"] = f"Bearer {key}"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt_for(candidate)},
                {"role": "user", "content": example.input_text},
            ],
            self.token_param: max_output_tokens(),
        }
        data, latency_ms = post_json(
            f"{self.base_url}/chat/completions",
            payload=payload,
            headers=headers,
            provider=self.id,
            privacy=self.privacy,
        )
        choices = data.get("choices") or []
        if not choices:
            raise ProviderError(f"{self.id}: response contained no choices")
        text = (choices[0].get("message") or {}).get("content") or ""
        usage = data.get("usage") or {}
        return build_result(
            provider_id=self.id,
            model=model,
            text=text,
            latency_ms=latency_ms,
            input_tokens=int(usage.get("prompt_tokens", 0) or 0),
            output_tokens=int(usage.get("completion_tokens", 0) or 0),
            privacy=self.privacy,
        )
