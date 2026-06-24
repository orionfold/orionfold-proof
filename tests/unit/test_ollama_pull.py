"""Pull/list/normalize helpers for hf-own-models — exercised keyless via stubbed ``httpx``.

No live Ollama: we stub the streamed ``POST /api/pull`` and the ``GET /api/tags`` call. These
are pre-run selection helpers, so unlike a run provider they *raise* ``ProviderError`` on failure;
the tests pin both the parse (happy path) and the raise (daemon down, error-in-stream).
"""

from __future__ import annotations

import json

import httpx
import pytest

from orionfold.providers import ollama_pull as pull_mod
from orionfold.providers.http import ProviderError
from orionfold.providers.ollama_pull import list_pulled, normalize_tag, pull_model


def _ndjson(lines: list[dict]) -> str:
    return "\n".join(json.dumps(o) for o in lines) + "\n"


def _stub_stream(monkeypatch, *, status: int = 200, body: str = ""):
    """Replace ``httpx.stream`` with a context manager over a canned streamed response."""

    class _Resp:
        def __init__(self) -> None:
            self.status_code = status

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return body.encode()

        def iter_lines(self):
            yield from body.splitlines()

    def fake_stream(method, url, **kwargs):  # noqa: ANN001
        return _Resp()

    monkeypatch.setattr(pull_mod.httpx, "stream", fake_stream)


def _stub_stream_raises(monkeypatch, exc: Exception):
    def fake_stream(method, url, **kwargs):  # noqa: ANN001
        raise exc

    monkeypatch.setattr(pull_mod.httpx, "stream", fake_stream)


# --- pull_model: parse the NDJSON progress stream -------------------------------------------


def test_pull_model_parses_progress_then_success(monkeypatch):
    _stub_stream(
        monkeypatch,
        body=_ndjson(
            [
                {"status": "pulling manifest"},
                {"status": "downloading", "completed": 2_100_000_000, "total": 3_400_000_000},
                {"status": "success"},
            ]
        ),
    )
    events = list(pull_model("http://localhost:11434", "hf.co/Orionfold/Saul-7B-Instruct-v1-GGUF"))
    assert [e.status for e in events] == ["pulling manifest", "downloading", "success"]
    dl = events[1]
    assert dl.completed == 2_100_000_000 and dl.total == 3_400_000_000


def test_pull_model_raises_on_error_status_in_stream(monkeypatch):
    _stub_stream(
        monkeypatch,
        body=_ndjson([{"status": "pulling manifest"}, {"error": "file does not exist"}]),
    )
    with pytest.raises(ProviderError, match="file does not exist"):
        list(pull_model("http://localhost:11434", "hf.co/Orionfold/nope"))


def test_pull_model_tolerates_a_garbage_line(monkeypatch):
    _stub_stream(
        monkeypatch,
        body="not json\n" + _ndjson([{"status": "success"}]),
    )
    events = list(pull_model("http://localhost:11434", "hf.co/x/y"))
    assert [e.status for e in events] == ["success"]


def test_pull_model_daemon_down_raises_not_reachable(monkeypatch):
    _stub_stream_raises(monkeypatch, httpx.ConnectError("refused"))
    with pytest.raises(ProviderError, match="Ollama not reachable"):
        list(pull_model("http://localhost:11434", "hf.co/x/y"))


# --- list_pulled: parse /api/tags -----------------------------------------------------------


def _stub_get(monkeypatch, *, status: int = 200, json_body: dict | None = None, exc=None):
    def fake_get(url, timeout=None):  # noqa: ANN001
        if exc is not None:
            raise exc
        request = httpx.Request("GET", url)
        return httpx.Response(status, json=json_body or {}, request=request)

    monkeypatch.setattr(pull_mod.httpx, "get", fake_get)


def test_list_pulled_parses_model_names(monkeypatch):
    _stub_get(
        monkeypatch,
        json_body={
            "models": [
                {"name": "qwen3:latest"},
                {"name": "hf.co/Orionfold/Saul-7B-Instruct-v1-GGUF:latest"},
            ]
        },
    )
    names = list_pulled("http://localhost:11434")
    assert "qwen3:latest" in names
    assert "hf.co/Orionfold/Saul-7B-Instruct-v1-GGUF:latest" in names


def test_list_pulled_daemon_down_raises(monkeypatch):
    _stub_get(monkeypatch, exc=httpx.ConnectError("refused"))
    with pytest.raises(ProviderError, match="Ollama not reachable"):
        list_pulled("http://localhost:11434")


# --- normalize_tag: the known-unknown reconciliation (fixture from a real round-trip) --------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        # Real shapes observed from a live `/api/tags`: standard models come back `name:latest`.
        ("qwen3:latest", "qwen3"),
        ("deepseek-r1:latest", "deepseek-r1"),
        # HF/GGUF pull shapes (HF Ollama docs): hf.co/<org>/<repo>[:<quant>], quant case-insensitive.
        ("hf.co/Orionfold/Saul-7B-Instruct-v1-GGUF:latest", "orionfold/saul-7b-instruct-v1-gguf"),
        ("hf.co/Orionfold/Saul-7B-Instruct-v1-GGUF:Q4_K_M", "orionfold/saul-7b-instruct-v1-gguf"),
        ("hf.co/Orionfold/Saul-7B-Instruct-v1-GGUF", "orionfold/saul-7b-instruct-v1-gguf"),
        # The repo_id we store (no suffix) normalizes to the same key — so set-membership matches.
        ("hf.co/Orionfold/Kepler-GGUF", "orionfold/kepler-gguf"),
    ],
)
def test_normalize_tag_canonicalizes(name, expected):
    assert normalize_tag(name) == expected


def test_normalize_tag_repo_id_matches_pulled_tag():
    # The load-bearing invariant: a stored repo_id and the daemon's returned name reconcile.
    repo_id = "hf.co/Orionfold/Saul-7B-Instruct-v1-GGUF"
    pulled = "hf.co/Orionfold/Saul-7B-Instruct-v1-GGUF:Q4_K_M"  # default quant + tag
    assert normalize_tag(repo_id) == normalize_tag(pulled)
