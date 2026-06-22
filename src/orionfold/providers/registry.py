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

import re

from orionfold.catalog import default_model_for
from orionfold.config.keys import has_key, resolve
from orionfold.domain.models import Candidate, PromptVariant
from orionfold.providers import anthropic as _anthropic
from orionfold.providers import gemini as _gemini
from orionfold.providers import ollama as _ollama
from orionfold.providers.base import Provider
from orionfold.providers.mock import MockBadProvider, MockGoodProvider
from orionfold.providers.openai_compatible import OpenAICompatibleProvider

# Default models are sourced from the bundled catalog (single source of truth). Each remains
# overridable with the matching env / .env.local var so an operator can prove a different model
# without code changes: ORIONFOLD_<PROVIDER>_MODEL > catalog default.

# (provider instance, model). model is None for the keyless mocks.
_Entry = tuple[Provider, str | None]


def _build() -> dict[str, _Entry]:
    """Construct the candidate map for the current environment (keys may come and go)."""
    registry: dict[str, _Entry] = {}

    # Deterministic mocks — always available, keyless, the default proof path.
    for mock in (MockGoodProvider(), MockBadProvider()):
        registry[mock.id] = (mock, None)

    # Ollama — local, keyless.
    ollama_model = resolve("ORIONFOLD_OLLAMA_MODEL", default_model_for("ollama"))
    registry["ollama"] = (_ollama.OllamaProvider(ollama_model), ollama_model)

    # LM Studio — local, keyless, OpenAI-compatible.
    lmstudio_model = resolve("ORIONFOLD_LMSTUDIO_MODEL", default_model_for("lmstudio"))
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
        model = resolve("ORIONFOLD_OPENAI_MODEL", default_model_for("openai"))
        registry["openai"] = (
            OpenAICompatibleProvider(
                id="openai",
                label="OpenAI",
                base_url=resolve("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                default_model=model,
                key_name="OPENAI_API_KEY",
                # GPT-5.x rejects "max_tokens"; OpenAI requires "max_completion_tokens".
                token_param="max_completion_tokens",
            ),
            model,
        )
    if has_key("OPENROUTER_API_KEY"):
        model = resolve("ORIONFOLD_OPENROUTER_MODEL", default_model_for("openrouter"))
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
        model = resolve("ORIONFOLD_GEMINI_MODEL", default_model_for("gemini"))
        registry["gemini"] = (_gemini.GeminiProvider(model), model)
    if has_key("ANTHROPIC_API_KEY"):
        model = resolve("ORIONFOLD_ANTHROPIC_MODEL", default_model_for("anthropic"))
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


class UnknownCandidateError(ValueError):
    """A requested candidate id can't be resolved to an available provider + model."""

    def __init__(self, unknown: list[str]) -> None:
        self.unknown = unknown
        super().__init__(f"Unknown candidate(s): {unknown}")


def build_candidates(candidate_ids: list[str]) -> list[Candidate]:
    """Resolve request ids into validated candidates.

    - A bare id already offered by ``available_candidates()`` (a mock, or a real provider's
      default model) resolves unchanged — backward compatible.
    - A composite ``provider:model`` id (split on the FIRST colon) resolves iff the provider is
      a currently-available **model-bearing** provider and ``model`` is a non-empty string. The
      model becomes part of the candidate's identity, which already feeds ``config_hash``. The
      keyless mocks carry ``model=None`` and are deliberately excluded here, so a crafted id
      like ``mock_good:foo`` can never mint a composite mock candidate — mocks stay bare-id.
    - Anything else is collected and raised as :class:`UnknownCandidateError` (keyless-safe: an
      unavailable provider is never in ``_build()``).
    """
    registry = _build()
    by_id = {c.id: c for c in available_candidates()}
    resolved: list[Candidate] = []
    unknown: list[str] = []
    for cid in candidate_ids:
        existing = by_id.get(cid)
        if existing is not None:
            resolved.append(existing)
            continue
        provider_id, sep, model = cid.partition(":")
        # ``registry[pid] == (provider, default_model)``; mocks have ``default_model is None``,
        # so this guard accepts composite ids only for real, model-bearing providers.
        if sep and model and provider_id in registry and registry[provider_id][1] is not None:
            provider = registry[provider_id][0]
            resolved.append(
                Candidate(
                    id=cid,
                    label=f"{provider.label} · {model}",
                    provider_id=provider_id,
                    privacy=provider.privacy,
                    model=model,
                )
            )
        else:
            unknown.append(cid)
    if unknown:
        raise UnknownCandidateError(unknown)
    return resolved


def _slug(name: str) -> str:
    """Lowercase, alphanumeric-with-hyphens slug for a variant id segment."""
    s = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "variant"


def expand_prompt_variants(
    base: Candidate, variants: list[PromptVariant]
) -> list[Candidate]:
    """Fan one model-bearing ``base`` candidate out into one candidate per prompt variant.

    Each variant becomes a candidate sharing ``base``'s provider/model/privacy but carrying its
    own ``system_prompt`` and a ``{base.id}#{slug}`` id. Slugs are deduped within the run so two
    same-named variants still get distinct ids (and distinct config_hash entries).
    """
    out: list[Candidate] = []
    seen: dict[str, int] = {}
    for v in variants:
        slug = _slug(v.name)
        seen[slug] = seen.get(slug, 0) + 1
        if seen[slug] > 1:
            slug = f"{slug}-{seen[slug]}"
        out.append(
            Candidate(
                id=f"{base.id}#{slug}",
                label=v.name,
                provider_id=base.provider_id,
                privacy=base.privacy,
                model=base.model,
                system_prompt=v.system_prompt,
            )
        )
    return out
