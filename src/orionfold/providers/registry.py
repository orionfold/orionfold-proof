"""Provider registry — maps a candidate id to a configured provider instance.

This is the only file Gate 6 needed to grow: the engine, scorer, leaderboard, and receipt are
untouched because every provider crosses the same ``ProviderResult`` boundary. The registry is
built **dynamically** so it reflects the environment at call time:

- The two deterministic mocks and the local profiles (``ollama``, ``lmstudio``) are always
  offered — they need no credentials.
- The cloud profiles (``openai``, ``openrouter``, ``gemini``, ``anthropic``) are offered **only
  when their API key is resolvable** (system env or ``.env.local``), so the UI never lists a
  candidate that can't run. Selecting a misconfigured one still fails gracefully via
  ``safe_generate``.

Each candidate carries its default model (env-overridable), which is part of its identity and
feeds the run's ``config_hash``.
"""

from __future__ import annotations

from orionfold.config.keys import has_key, resolve
from orionfold.domain.models import Candidate
from orionfold.providers import anthropic as _anthropic
from orionfold.providers import gemini as _gemini
from orionfold.providers import ollama as _ollama
from orionfold.providers.base import Provider
from orionfold.providers.mock import MockBadProvider, MockGoodProvider
from orionfold.providers.openai_compatible import OpenAICompatibleProvider

# Default models per profile. Each is overridable with the matching env / .env.local var so an
# operator can prove a different model without code changes.
_OPENAI_DEFAULT = "gpt-4o-mini"
_OPENROUTER_DEFAULT = "openai/gpt-4o-mini"
_LMSTUDIO_DEFAULT = "local-model"

# (provider instance, model). model is None for the keyless mocks.
_Entry = tuple[Provider, str | None]


def _build() -> dict[str, _Entry]:
    """Construct the candidate map for the current environment (keys may come and go)."""
    registry: dict[str, _Entry] = {}

    # Deterministic mocks — always available, keyless, the default proof path.
    for mock in (MockGoodProvider(), MockBadProvider()):
        registry[mock.id] = (mock, None)

    # Ollama — local, keyless.
    ollama_model = resolve("ORIONFOLD_OLLAMA_MODEL", _ollama.DEFAULT_MODEL)
    registry["ollama"] = (_ollama.OllamaProvider(ollama_model), ollama_model)

    # LM Studio — local, keyless, OpenAI-compatible.
    lmstudio_model = resolve("ORIONFOLD_LMSTUDIO_MODEL", _LMSTUDIO_DEFAULT)
    registry["lmstudio"] = (
        OpenAICompatibleProvider(
            id="lmstudio",
            label="LM Studio",
            base_url=resolve("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
            default_model=lmstudio_model,
            key_name=None,
            privacy="local",
        ),
        lmstudio_model,
    )

    # Cloud profiles — only when their key is present.
    if has_key("OPENAI_API_KEY"):
        model = resolve("ORIONFOLD_OPENAI_MODEL", _OPENAI_DEFAULT)
        registry["openai"] = (
            OpenAICompatibleProvider(
                id="openai",
                label="OpenAI",
                base_url=resolve("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                default_model=model,
                key_name="OPENAI_API_KEY",
            ),
            model,
        )
    if has_key("OPENROUTER_API_KEY"):
        model = resolve("ORIONFOLD_OPENROUTER_MODEL", _OPENROUTER_DEFAULT)
        registry["openrouter"] = (
            OpenAICompatibleProvider(
                id="openrouter",
                label="OpenRouter",
                base_url=resolve("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                default_model=model,
                key_name="OPENROUTER_API_KEY",
            ),
            model,
        )
    if has_key("GEMINI_API_KEY"):
        model = resolve("ORIONFOLD_GEMINI_MODEL", _gemini.DEFAULT_MODEL)
        registry["gemini"] = (_gemini.GeminiProvider(model), model)
    if has_key("ANTHROPIC_API_KEY"):
        model = resolve("ORIONFOLD_ANTHROPIC_MODEL", _anthropic.DEFAULT_MODEL)
        registry["anthropic"] = (_anthropic.AnthropicProvider(model), model)

    return registry


def get_provider(provider_id: str) -> Provider:
    """Return the configured provider for ``provider_id``, or raise ``KeyError`` if unknown."""
    return _build()[provider_id][0]


def available_candidates() -> list[Candidate]:
    """The candidates a user can currently select (one per available provider)."""
    candidates: list[Candidate] = []
    for cid, (provider, model) in _build().items():
        label = provider.label if model is None else f"{provider.label} · {model}"
        candidates.append(
            Candidate(
                id=cid,
                label=label,
                provider_id=cid,
                privacy=provider.privacy,
                model=model,
            )
        )
    return candidates
