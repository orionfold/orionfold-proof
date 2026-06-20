"""Credential resolution: system env wins over a repo-root .env.local (ADR-0002).

These tests pin the precedence rule and the tiny stdlib parser. They never assert on a real
key — only on resolution behavior — and they keep .env.local confined to a tmp dir.
"""

from __future__ import annotations

import pytest

from orionfold.config import keys


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Run each test in a clean tmp CWD with the four provider keys unset."""
    monkeypatch.chdir(tmp_path)
    for name in (
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "OPENROUTER_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def _write_env_local(tmp_path, body: str) -> None:
    (tmp_path / ".env.local").write_text(body, encoding="utf-8")


def test_system_env_wins_over_env_local(tmp_path, monkeypatch):
    _write_env_local(tmp_path, "OPENAI_API_KEY=from-file\n")
    monkeypatch.setenv("OPENAI_API_KEY", "from-env")
    assert keys.resolve_key("OPENAI_API_KEY") == "from-env"


def test_falls_back_to_env_local_when_env_absent(tmp_path):
    _write_env_local(tmp_path, "ANTHROPIC_API_KEY=from-file\n")
    assert keys.resolve_key("ANTHROPIC_API_KEY") == "from-file"


def test_missing_everywhere_returns_none(tmp_path):
    _write_env_local(tmp_path, "OPENAI_API_KEY=x\n")
    assert keys.resolve_key("GEMINI_API_KEY") is None


def test_no_env_local_file_returns_none(tmp_path):
    assert keys.resolve_key("OPENROUTER_API_KEY") is None


def test_empty_value_is_treated_as_absent(tmp_path, monkeypatch):
    # An empty/whitespace key must not light up a (broken) cloud candidate.
    _write_env_local(tmp_path, "GEMINI_API_KEY=fallback\n")
    monkeypatch.setenv("GEMINI_API_KEY", "   ")
    assert keys.resolve_key("GEMINI_API_KEY") == "fallback"
    monkeypatch.setenv("OPENAI_API_KEY", "")
    assert keys.resolve_key("OPENAI_API_KEY") is None


def test_parser_handles_comments_blanks_quotes_and_export(tmp_path):
    _write_env_local(
        tmp_path,
        "\n".join(
            [
                "# a comment",
                "",
                "   # indented comment",
                'OPENAI_API_KEY="quoted-value"',
                "export ANTHROPIC_API_KEY = spaced-value ",
                "OPENROUTER_API_KEY='single-quoted'",
                "MALFORMED_NO_EQUALS",
            ]
        ),
    )
    assert keys.resolve_key("OPENAI_API_KEY") == "quoted-value"
    assert keys.resolve_key("ANTHROPIC_API_KEY") == "spaced-value"
    assert keys.resolve_key("OPENROUTER_API_KEY") == "single-quoted"


def test_has_key_reflects_presence(tmp_path, monkeypatch):
    assert keys.has_key("ANTHROPIC_API_KEY") is False
    monkeypatch.setenv("ANTHROPIC_API_KEY", "present")
    assert keys.has_key("ANTHROPIC_API_KEY") is True


def test_resolve_returns_default_then_value(tmp_path, monkeypatch):
    assert keys.resolve("OLLAMA_HOST", "http://localhost:11434") == "http://localhost:11434"
    _write_env_local(tmp_path, "OLLAMA_HOST=http://box:11434\n")
    assert keys.resolve("OLLAMA_HOST", "http://localhost:11434") == "http://box:11434"
    monkeypatch.setenv("OLLAMA_HOST", "http://env-host:11434")
    assert keys.resolve("OLLAMA_HOST", "http://localhost:11434") == "http://env-host:11434"
