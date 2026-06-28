#!/usr/bin/env python3
"""Secrets-guard PreToolUse hook for orionfold-proof.

Enforces the product's prime directive — "never log, commit, or write API keys
into code, receipts, or screenshots" — as a deterministic guarantee rather than
advisory CLAUDE.md prose. See .claude/settings.json (hooks.PreToolUse) and the
release charter's Safety section.

Contract (Claude Code PreToolUse hook):
  - stdin: JSON with {"tool_name": ..., "tool_input": {...}}.
  - exit 0  -> allow the tool call.
  - exit 2  -> BLOCK the tool call; stderr is shown to Claude as the reason.

Design: deliberately conservative. We match secret *values* (provider key
prefixes, bearer tokens, high-entropy assignments to *_KEY/*_SECRET/*_TOKEN) and
staging of .env files — never the bare words "key"/"token". Legitimate receipt
fields (config hashes, model names, api_base URLs) must pass untouched, so the
fast iteration loop stays friction-free.
"""

from __future__ import annotations

import json
import re
import sys

# Provider/secret value signatures. Each requires real length so short,
# placeholder-ish fragments do not trip the guard.
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Anthropic API key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("GitHub token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{30,})\b")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("Bearer token", re.compile(r"[Aa]uthorization\s*:\s*Bearer\s+[A-Za-z0-9._-]{20,}")),
]

# Generic assignment of a real-looking value to a secret-named field.
# Excludes env-var references and obvious placeholders (handled below).
ASSIGNMENT_PATTERN = re.compile(
    r"""(?ix)
    \b[A-Za-z0-9_]*(?:API[_-]?KEY|SECRET|TOKEN|ACCESS[_-]?KEY|PASSWORD)\b
    \s* [=:] \s*
    ['"]? (?P<val>[^\s'"]{16,}) ['"]?
    """
)

# Values that are clearly not real secrets — env lookups, references, templates,
# examples. The captured `val` stops at the first space/quote, so a secret-named
# field assigned a *dotted-attribute reference* (e.g. `api_key = settings.advisor_api_key`)
# is captured whole and must be recognized as a reference, not a literal. This is
# safe: SECRET_PATTERNS runs first (so a real keyed literal still blocks), and a
# genuine high-entropy secret is an unbroken base64/hex run; the dotted-ref alt caps
# each segment at 32 chars + depth at 6, so a dotted token (a JWT header.payload.sig
# whose segments are 40+ base64url chars) cannot slip through it.
PLACEHOLDER = re.compile(
    r"(?ix)^(?:"
    r"\$?\{?[A-Z0-9_]*(?:ENV|VAR|PLACEHOLDER)[A-Z0-9_]*\}?"  # ENV/VAR/PLACEHOLDER refs
    r"|os\.environ.*|getenv.*|process\.env.*"                 # code env lookups
    r"|(?:self|cls|settings|config|cfg|conf|app|ctx|os|sys|env|args|opts|options|secrets|creds|credentials|vault|client|request|req|response|resp|state)(?:\.[A-Za-z_]\w{0,31}){1,5}[;),]?"  # dotted ref anchored to a known namespace, each seg <=32, depth <=6 (a token can't masquerade as one)
    r"|your[-_].*|example.*|changeme.*|placeholder.*|xxx+.*|\.\.\.+"
    r"|<[^>]+>"                                                # <your-key-here>
    r")$"
)


def find_secret(text: str) -> str | None:
    """Return a human-readable reason if `text` carries secret material."""
    if not text:
        return None
    for label, pat in SECRET_PATTERNS:
        if pat.search(text):
            return f"{label} detected"
    for m in ASSIGNMENT_PATTERN.finditer(text):
        val = m.group("val")
        if not PLACEHOLDER.match(val):
            return "a secret-named field assigned a literal value"
    return None


def check_bash(command: str) -> str | None:
    """Block staging/committing of .env files; also scan for inline secrets."""
    if re.search(r"\bgit\s+add\b[^\n|&;]*\.env", command):
        return "git add of a .env file"
    if re.search(r"\bgit\s+commit\b[^\n|&;]*\.env", command):
        return "git commit referencing a .env file"
    return find_secret(command)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # Never block on a malformed/empty payload.

    tool = payload.get("tool_name", "")
    ti = payload.get("tool_input", {}) or {}

    reason: str | None = None
    if tool == "Write":
        reason = find_secret(ti.get("content", ""))
    elif tool == "Edit":
        reason = find_secret(ti.get("new_string", ""))
    elif tool == "Bash":
        reason = check_bash(ti.get("command", ""))

    if reason:
        sys.stderr.write(
            f"BLOCKED by secrets-guard: {reason}. "
            "Secrets must never be written into code, receipts, screenshots, or commits "
            "(orionfold-proof prime directive). Use an env var / .env.local reference "
            "instead, and keep real keys out of tracked files.\n"
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
