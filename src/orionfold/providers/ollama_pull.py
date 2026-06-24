"""Ollama model management — pull an HF/GGUF model and list what's pulled (hf-own-models).

Pre-run *selection* scaffolding, not a run-path provider: it never produces a ``ProviderResult``
and never crosses the ``safe_generate`` boundary. Both calls hit only the **local** Ollama daemon
(``OLLAMA_HOST``, default ``localhost:11434``); Ollama itself reaches HuggingFace. Public Apache-2.0
GGUF repos need no token, so there is nothing secret to carry.

Unlike a run provider, these helpers *raise* :class:`ProviderError` on failure (daemon down, bad
repo). The caller decides the policy: the ``pull`` CLI surfaces the error with a non-zero exit;
the selection path catches it and degrades gracefully (Orionfold models unavailable-with-reason,
cloud candidates still present — see ``selection_panel``).
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import httpx
from pydantic import BaseModel

from orionfold.config.keys import resolve
from orionfold.providers.http import ProviderError
from orionfold.providers.ollama import DEFAULT_HOST

# A pull of a multi-GB GGUF can run for many minutes over a slow link; the stream stays open
# the whole time, so the read timeout is generous. Connect is capped short so an unreachable
# daemon fails fast instead of hanging.
_PULL_READ_S = 1800.0
_TAGS_READ_S = 10.0
_CONNECT_S = 5.0


class PullStatus(BaseModel):
    """One progress event from a streamed ``/api/pull`` line."""

    status: str  # e.g. "pulling manifest", "downloading", "success"
    completed: int | None = None  # bytes pulled so far (download statuses only)
    total: int | None = None  # total bytes (download statuses only)


def resolve_host() -> str:
    """The Ollama base URL, reusing :class:`OllamaProvider`'s ``OLLAMA_HOST`` resolution."""
    return resolve("OLLAMA_HOST", DEFAULT_HOST).rstrip("/")


def _not_reachable(host: str) -> ProviderError:
    return ProviderError(
        f"Ollama not reachable at {host} — is `ollama serve` running?"
    )


def pull_model(host: str, repo_id: str) -> Iterator[PullStatus]:
    """Stream ``POST {host}/api/pull`` and yield one :class:`PullStatus` per NDJSON line.

    Ollama emits newline-delimited JSON: a sequence of progress objects ending in
    ``{"status": "success"}``. An error mid-stream arrives as ``{"error": "..."}``; we raise
    :class:`ProviderError` carrying that message verbatim (no overlay write happens — the CLI
    only records the model after a clean ``success``). A daemon that is down raises before any
    line is yielded.
    """
    url = f"{host}/api/pull"
    payload = {"model": repo_id, "stream": True}
    timeout = httpx.Timeout(_PULL_READ_S, connect=_CONNECT_S)
    try:
        with httpx.stream(
            "POST",
            url,
            json=payload,
            headers={"content-type": "application/json"},
            timeout=timeout,
        ) as response:
            if response.status_code >= 400:
                response.read()
                raise ProviderError(f"ollama pull HTTP {response.status_code}")
            for line in response.iter_lines():
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue  # tolerate a partial/garbage line rather than abort the pull
                error = obj.get("error")
                if error:
                    raise ProviderError(f"ollama pull failed: {error}")
                yield PullStatus(
                    status=str(obj.get("status", "")),
                    completed=obj.get("completed"),
                    total=obj.get("total"),
                )
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        raise _not_reachable(host) from exc
    except httpx.HTTPError as exc:
        raise ProviderError(f"ollama pull request failed: {type(exc).__name__}") from exc


def list_pulled(host: str) -> set[str]:
    """Return the set of model names currently pulled, from ``GET {host}/api/tags``.

    ``/api/tags`` returns ``{"models": [{"name": "...", ...}, ...]}``. A daemon that is down
    raises :class:`ProviderError` so the selection path can degrade gracefully.
    """
    url = f"{host}/api/tags"
    timeout = httpx.Timeout(_TAGS_READ_S, connect=_CONNECT_S)
    try:
        response = httpx.get(url, timeout=timeout)
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        raise _not_reachable(host) from exc
    except httpx.HTTPError as exc:
        raise ProviderError(f"ollama tags request failed: {type(exc).__name__}") from exc
    if response.status_code >= 400:
        raise ProviderError(f"ollama tags HTTP {response.status_code}")
    try:
        data = response.json()
    except ValueError as exc:
        raise ProviderError("ollama tags returned non-JSON response") from exc
    models = data.get("models") or []
    return {str(m["name"]) for m in models if isinstance(m, dict) and m.get("name")}


def normalize_tag(name: str) -> str:
    """Canonicalize an Ollama model name for set-membership against a ``repo_id``.

    Ollama registers an ``hf.co/<org>/<repo>`` pull under a name it derives from the repo and
    reports it via ``/api/tags`` — typically the ``hf.co/...`` form with a ``:tag`` suffix that
    defaults to ``:latest`` (and may be a quant like ``:Q4_K_M``). We compare on the bare
    repo path: lowercase, ``hf.co/``-prefix-stripped, and ``:tag``-suffix-dropped, so a
    ``repo_id`` and the daemon's returned name match regardless of casing or which quant tag
    Ollama chose.

    ⚠️ Exact returned-name shape is a known unknown resolved by observation (spec §3); the
    selection tests pin this against a fixture captured from a real ``pull`` + ``/api/tags``
    round-trip.
    """
    bare = name.strip().lower()
    bare = bare.removeprefix("hf.co/")
    if ":" in bare:
        bare = bare.rsplit(":", 1)[0]
    return bare
