"""Write a single credential line into a repo-root ``.env.local`` (ADR-0002).

Used by the inline key-entry flow. The write is atomic (temp file + ``os.replace``), preserves
every other line/comment, and sets ``0o600`` because the file holds secrets. The value is never
logged or returned — callers receive only the path written.
"""

from __future__ import annotations

import os
from pathlib import Path

from orionfold.config.keys import _ENV_FILE_OVERRIDE, _ENV_LOCAL_FILENAME, _env_local_path


def _target_path() -> Path:
    """Where to write: the explicit override, an existing discovered file, else ``./``."""
    override = os.environ.get(_ENV_FILE_OVERRIDE)
    if override:
        return Path(override)
    existing = _env_local_path()
    return existing if existing is not None else Path.cwd() / _ENV_LOCAL_FILENAME


def set_key_in_env_local(key_name: str, value: str) -> Path:
    """Insert or replace ``key_name=value`` in ``.env.local``; return the path written."""
    path = _target_path()
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    new_line = f"{key_name}={value}"
    replaced = False
    out: list[str] = []
    for raw in lines:
        stripped = raw.strip()
        body = stripped[len("export ") :].strip() if stripped.startswith("export ") else stripped
        if body.partition("=")[0].strip() == key_name:
            out.append(new_line)
            replaced = True
        else:
            out.append(raw)
    if not replaced:
        out.append(new_line)

    tmp = path.with_name(path.name + ".tmp")
    # Create the temp file with 0o600 from the start so the secret is never world-readable,
    # even briefly (the umask could otherwise leave a write+chmod window at 0o644).
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("\n".join(out) + "\n")
    os.replace(tmp, path)
    return path
