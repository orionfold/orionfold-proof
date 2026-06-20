"""Provider registry — maps a provider id to an instance and to selectable candidates.

v0 ships the two deterministic mocks. Ollama and OpenAI-compatible register here in Gate 6
without any change to the engine, scorer, leaderboard, or receipt — that is the point of the
uniform provider boundary.
"""

from __future__ import annotations

from orionfold.domain.models import Candidate
from orionfold.providers.base import Provider
from orionfold.providers.mock import MockBadProvider, MockGoodProvider

_INSTANCES: list[Provider] = [MockGoodProvider(), MockBadProvider()]
_PROVIDERS: dict[str, Provider] = {p.id: p for p in _INSTANCES}


def get_provider(provider_id: str) -> Provider:
    """Return the registered provider, or raise ``KeyError`` for an unknown id."""
    return _PROVIDERS[provider_id]


def available_candidates() -> list[Candidate]:
    """The candidates a user can select in v0 (one per registered provider)."""
    return [
        Candidate(id=p.id, label=p.label, provider_id=p.id, privacy=p.privacy)
        for p in _PROVIDERS.values()
    ]
