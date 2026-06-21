"""Provider credential & config resolution (ADR-0002).

Resolution precedence is **system environment first, then a repo-root ``.env.local``** — the
system env is authoritative (12-factor / CI), and ``.env.local`` is a local dev convenience
that is git-ignored and must never be committed.

Secrets are *never* logged, echoed, or written to receipts. Callers receive the value or
``None``; the *presence* of a key is what decides whether a cloud candidate is offered. An
empty or whitespace-only value is treated as absent so a misconfigured key never lights up a
broken candidate.

``.env.local`` is parsed by a tiny stdlib parser (no ``python-dotenv`` dependency): one
``KEY=value`` per line, ``#`` comments and blank lines skipped, an optional ``export`` prefix
allowed, and surrounding single/double quotes stripped.
"""

from __future__ import annotations

import os
from pathlib import Path

_ENV_LOCAL_FILENAME = ".env.local"
# Allow tests / advanced users to point at an explicit file instead of the CWD search.
_ENV_FILE_OVERRIDE = "ORIONFOLD_ENV_FILE"
# Stop the upward walk at the project root so we never pick up a parent's .env.local.
_PROJECT_MARKERS = ("pyproject.toml", ".git")


def _env_local_path() -> Path | None:
    """Locate ``.env.local`` — explicit override, else CWD walking up, **bounded**.

    The walk stops at the first directory holding a project marker (``pyproject.toml`` / ``.git``)
    or the user's home directory, whichever comes first — so a nested run can't reach into a
    shared parent's ``.env.local``.
    """
    override = os.environ.get(_ENV_FILE_OVERRIDE)
    if override:
        path = Path(override)
        return path if path.is_file() else None
    here = Path.cwd()
    try:
        home = Path.home()
    except RuntimeError:  # home not resolvable in some sandboxes
        home = None
    for directory in (here, *here.parents):
        candidate = directory / _ENV_LOCAL_FILENAME
        if candidate.is_file():
            return candidate
        if directory == home or any((directory / m).exists() for m in _PROJECT_MARKERS):
            break  # reached the project root / home — don't ascend further
    return None


def _parse_env_local(text: str) -> dict[str, str]:
    """Parse ``KEY=value`` lines into a dict. Never raises on malformed input — skips it."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, sep, value = line.partition("=")
        if not sep:
            continue  # no '=', not a definition
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key] = value
    return values


def _load_env_local() -> dict[str, str]:
    """Read and parse ``.env.local`` fresh (it is tiny and read at most a handful of times)."""
    path = _env_local_path()
    if path is None:
        return {}
    try:
        return _parse_env_local(path.read_text(encoding="utf-8"))
    except OSError:
        # An unreadable .env.local must not crash provider listing — behave as absent.
        return {}


def _nonempty(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def resolve_key(name: str) -> str | None:
    """Return a credential by name — system env first, then ``.env.local`` — or ``None``.

    Empty/whitespace-only values are treated as absent.
    """
    from_env = _nonempty(os.environ.get(name))
    if from_env is not None:
        return from_env
    return _nonempty(_load_env_local().get(name))


def has_key(name: str) -> bool:
    """True when a usable (non-empty) credential is resolvable for ``name``."""
    return resolve_key(name) is not None


def resolve(name: str, default: str) -> str:
    """Resolve a non-secret config value (base URL, host, model override) with a default.

    Same env-over-``.env.local`` precedence; falls back to ``default`` when neither is set.
    """
    value = resolve_key(name)
    return value if value is not None else default


# The four cloud providers that resolve on a key, mapped to their env-var NAME. Single source of
# truth for both the registry's availability gate and the credential-entry whitelist. Local
# providers (ollama, lmstudio) and mocks are deliberately absent — they need no key, and the
# credential endpoint rejects any provider id not in this map (no arbitrary env writes).
CLOUD_KEY_NAMES: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}
