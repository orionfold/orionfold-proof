"""Google Gemini provider — ``POST .../v1beta/models/{model}:generateContent`` (Gate 6).

The key is sent in the ``x-goog-api-key`` **header**, not the ``?key=`` URL parameter, so it
can never end up in a URL that an error message echoes — this is the primary case the
``redact_secrets`` boundary is proven against (ADR-0002). ``privacy="cloud"``.
"""

from __future__ import annotations

from orionfold.config.keys import resolve_key
from orionfold.domain.models import Candidate, Example, Privacy, ProviderResult
from orionfold.providers.http import (
    TASK_SYSTEM_PROMPT,
    ProviderError,
    build_result,
    max_output_tokens,
    post_json,
)

DEFAULT_MODEL = "gemini-3.1-flash-lite"
_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
KEY_NAME = "GEMINI_API_KEY"


class GeminiProvider:
    id: str = "gemini"
    label: str = "Gemini"
    privacy: Privacy = "cloud"

    def __init__(self, default_model: str = DEFAULT_MODEL) -> None:
        self.default_model = default_model

    def generate(self, example: Example, candidate: Candidate) -> ProviderResult:
        model = candidate.model or self.default_model
        key = resolve_key(KEY_NAME)
        if key is None:
            raise ProviderError(f"{self.id}: {KEY_NAME} not set")
        payload = {
            "systemInstruction": {"parts": [{"text": TASK_SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": example.input_text}]}],
            "generationConfig": {"maxOutputTokens": max_output_tokens()},
        }
        data, latency_ms = post_json(
            f"{_BASE}/{model}:generateContent",
            payload=payload,
            headers={"x-goog-api-key": key, "content-type": "application/json"},
            provider=self.id,
            privacy=self.privacy,
        )
        candidates = data.get("candidates") or []
        text = ""
        if candidates:
            parts = (candidates[0].get("content") or {}).get("parts") or []
            text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        usage = data.get("usageMetadata") or {}
        return build_result(
            provider_id=self.id,
            model=model,
            text=text,
            latency_ms=latency_ms,
            input_tokens=int(usage.get("promptTokenCount", 0) or 0),
            output_tokens=int(usage.get("candidatesTokenCount", 0) or 0),
            privacy=self.privacy,
        )
