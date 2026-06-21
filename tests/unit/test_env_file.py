"""The .env.local writer updates one key line atomically, preserving everything else, 0o600,
and never surfacing the value. Confined to a tmp dir via ORIONFOLD_ENV_FILE."""

from __future__ import annotations

import stat

import pytest

from orionfold.config import keys
from orionfold.config.env_file import set_key_in_env_local


@pytest.fixture()
def env_path(tmp_path, monkeypatch):
    path = tmp_path / ".env.local"
    monkeypatch.setenv("ORIONFOLD_ENV_FILE", str(path))
    return path


def test_creates_file_with_the_key_and_strict_perms(env_path):
    returned = set_key_in_env_local("ANTHROPIC_API_KEY", "abc123")
    assert returned == env_path
    assert env_path.read_text() == "ANTHROPIC_API_KEY=abc123\n"
    mode = stat.S_IMODE(env_path.stat().st_mode)
    assert mode == 0o600


def test_resolves_after_write(env_path):
    set_key_in_env_local("ANTHROPIC_API_KEY", "abc123")
    # ORIONFOLD_ENV_FILE points keys.resolve_key at the same file.
    assert keys.resolve_key("ANTHROPIC_API_KEY") == "abc123"


def test_updates_existing_key_and_preserves_other_lines(env_path):
    env_path.write_text(
        "# my keys\nOPENAI_API_KEY=keep-me\nANTHROPIC_API_KEY=old\nOLLAMA_HOST=http://box\n"
    )
    set_key_in_env_local("ANTHROPIC_API_KEY", "new")
    text = env_path.read_text()
    assert "ANTHROPIC_API_KEY=new\n" in text
    assert "ANTHROPIC_API_KEY=old" not in text
    assert "OPENAI_API_KEY=keep-me\n" in text
    assert "OLLAMA_HOST=http://box\n" in text
    assert "# my keys\n" in text


def test_appends_when_key_absent(env_path):
    env_path.write_text("OPENAI_API_KEY=keep-me\n")
    set_key_in_env_local("GEMINI_API_KEY", "g")
    text = env_path.read_text()
    assert "OPENAI_API_KEY=keep-me\n" in text
    assert "GEMINI_API_KEY=g\n" in text


def test_return_value_carries_no_secret(env_path):
    returned = set_key_in_env_local("ANTHROPIC_API_KEY", "topsecret")
    assert "topsecret" not in str(returned)
