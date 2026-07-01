"""Ollama provider — local models over ``POST /api/chat`` (Gate 6, ADR-0002).

Local and keyless: ``privacy="local"`` and ``$0.00`` estimated cost. Errors (a model not
pulled, the daemon down) cross the ``safe_generate`` boundary as a returned error, never a
raised exception.
"""

from __future__ import annotations

from orionfold.config.keys import resolve
from orionfold.domain.models import Candidate, Example, Privacy, ProviderResult
from orionfold.providers.http import (
    DETERMINISTIC_SAMPLING,
    ProviderError,
    build_result,
    max_output_tokens,
    post_json,
    system_prompt_for,
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
                {"role": "system", "content": system_prompt_for(candidate)},
                {"role": "user", "content": example.input_text},
            ],
            "stream": False,
            # A proof must be reproducible: pin temperature 0 (greedy decode) so a re-run is
            # byte-stable, matching the receipt's repeatability promise. `think=false` disables a
            # thinking-capable model's reasoning block so its output is the clean, directly-scorable
            # answer (no <think> spill into citation/refusal parsing). Both are inert for models that
            # don't support them — Ollama ignores unknown sampling knobs and the think flag.
            "think": False,
            "options": {"num_predict": max_output_tokens(), "temperature": 0},
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
        # Pure warm-decode time: Ollama's eval_duration (ns) is the token-generation phase ONLY —
        # it excludes load_duration (cold model load) and prompt_eval_duration. Capturing it lets
        # the receipt report honest warm throughput instead of the ~3×-diluted end-to-end latency.
        eval_duration_ns = int(data.get("eval_duration", 0) or 0)
        warm_decode_ms = round(eval_duration_ns / 1e6) if eval_duration_ns > 0 else None
        return build_result(
            provider_id=self.id,
            model=model,
            text=text,
            latency_ms=latency_ms,
            input_tokens=int(data.get("prompt_eval_count", 0) or 0),
            output_tokens=int(data.get("eval_count", 0) or 0),
            privacy=self.privacy,
            warm_decode_ms=warm_decode_ms,
            sampling=DETERMINISTIC_SAMPLING,  # pins temperature 0 above → disclose it
        )
