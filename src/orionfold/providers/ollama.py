"""Ollama provider — local models over ``POST /api/chat`` (Gate 6, ADR-0002).

Local and keyless: ``privacy="local"`` and ``$0.00`` estimated cost. Errors (a model not
pulled, the daemon down) cross the ``safe_generate`` boundary as a returned error, never a
raised exception.
"""

from __future__ import annotations

from orionfold.config.keys import resolve
from orionfold.domain.models import Candidate, Example, Privacy, ProviderResult
from orionfold.providers.http import (
    TASK_SYSTEM_PROMPT,
    ProviderError,
    build_result,
    max_output_tokens,
    post_json,
)

DEFAULT_MODEL = "llama3.2"
DEFAULT_HOST = "http://localhost:11434"


class OllamaProvider:
    id: str = "ollama"
    label: str = "Ollama"
    privacy: Privacy = "local"

    def __init__(self, default_model: str = DEFAULT_MODEL) -> None:
        self.default_model = default_model

    def generate(self, example: Example, candidate: Candidate) -> ProviderResult:
        model = candidate.model or self.default_model
        host = resolve("OLLAMA_HOST", DEFAULT_HOST).rstrip("/")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": TASK_SYSTEM_PROMPT},
                {"role": "user", "content": example.input_text},
            ],
            "stream": False,
            "options": {"num_predict": max_output_tokens()},
        }
        data, latency_ms = post_json(
            f"{host}/api/chat",
            payload=payload,
            headers={"content-type": "application/json"},
            provider=self.id,
            privacy=self.privacy,
        )
        message = data.get("message") or {}
        text = message.get("content", "")
        if not isinstance(text, str):
            raise ProviderError(f"{self.id}: unexpected response shape")
        return build_result(
            provider_id=self.id,
            model=model,
            text=text,
            latency_ms=latency_ms,
            input_tokens=int(data.get("prompt_eval_count", 0) or 0),
            output_tokens=int(data.get("eval_count", 0) or 0),
            privacy=self.privacy,
        )
