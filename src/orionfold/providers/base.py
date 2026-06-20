"""Provider boundary (ADR-0001 §6, enforced by .claude/rules/providers.md).

Every provider returns a uniform :class:`ProviderResult` — *including on error*. No
exception crosses this boundary, so one bad candidate never aborts a run. API keys are
never logged, printed, or written into ``raw_metadata``.
"""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from orionfold.domain.models import Candidate, Example, Privacy, ProviderResult

# Defense-in-depth: a provider exception message must never carry a credential into a
# receipt or the local DB. The mocks can't leak (no keys), but Gate 6's real providers can
# raise httpx/SDK errors that echo a key in a URL or header — redact those at the boundary.
_SECRET_PATTERN = re.compile(
    # OpenAI / Anthropic keys, including hyphenated families (sk-proj-…, sk-ant-api03-…).
    r"sk-[A-Za-z0-9_-]{6,}"
    # Google API keys (AIza…), which can surface in a Gemini error body.
    r"|AIza[0-9A-Za-z_-]{10,}"
    r"|Bearer\s+\S+"
    r"|(?:api[_-]?key|token|secret|password|authorization)\s*[=:]\s*\S+",
    re.IGNORECASE,
)


def redact_secrets(text: str) -> str:
    """Replace anything that looks like a key/token/credential with ``[redacted]``."""
    return _SECRET_PATTERN.sub("[redacted]", text)


@runtime_checkable
class Provider(Protocol):
    """A thing that turns an example into a scored-elsewhere :class:`ProviderResult`."""

    id: str
    label: str
    privacy: Privacy

    def generate(self, example: Example, candidate: Candidate) -> ProviderResult:
        """Produce output for ``example``. May raise — callers use :func:`safe_generate`."""
        ...


def safe_generate(provider: Provider, example: Example, candidate: Candidate) -> ProviderResult:
    """Call ``provider.generate`` and guarantee a :class:`ProviderResult` back.

    Any exception is captured into ``error`` (its message only — never a stack trace or
    secret) so the matrix engine can record a failure row and keep going.
    """
    try:
        return provider.generate(example, candidate)
    except Exception as exc:  # noqa: BLE001 — the boundary deliberately swallows everything
        # Message only (never a traceback), and redacted so no credential can escape here.
        return ProviderResult(
            output_text="",
            privacy=provider.privacy,
            error=redact_secrets(f"{type(exc).__name__}: {exc}"),
        )
