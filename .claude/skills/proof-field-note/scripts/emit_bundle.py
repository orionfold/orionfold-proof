#!/usr/bin/env python3
"""Assemble a website-ready bundle from an authored Proof field note (Layer B).

Input: the path to a scaffold `article.md` produced by `orionfold field-note`
(Layer A) and then authored by the operator (the `## Why this can be trusted`
narrative written in place of the stub).

Output: a gitignored bundle at `_field-notes/<slug>/bundle/` targeting the peer
website's Astro `story` collection:

    _field-notes/<slug>/bundle/
    ├── article.md        # the authored note, verbatim (figures stay inline)
    ├── bundle.json       # provenance manifest (slug, run_id, config_hash, ...)
    └── hero/README.md    # where to drop the optional hero image

This helper does NOT author anything and does NOT rewrite frontmatter: Layer A's
frontmatter is already a valid superset of the `story` schema (extra
proof-provenance keys are tolerated by Astro's non-strict collection). It only:

  1. refuses to emit while the narrative is still the unauthored stub (marker guard),
  2. derives the slug from the frontmatter `title`,
  3. backstops a secret scan (Layer A is secret-free by construction; this is
     defense in depth, mirroring the repo's secrets-guard shapes),
  4. lays out the bundle + a provenance manifest.

Pure stdlib, no third-party deps. Run from the repo root (paths are relative to CWD).

Usage:
    python3 .claude/skills/proof-field-note/scripts/emit_bundle.py _field-notes/<run_id>/article.md
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

# The author marker Layer A's narrative stub carries (receipts/field_note.py).
# Its presence means the operator has not yet written the trust narrative.
AUTHOR_MARKER = "<!-- author: replace this section -->"

# Secret value signatures — a subset of the repo's secrets-guard hook patterns,
# so the bundle can never ship a key even though Layer A is secret-free by
# construction. Defense in depth (the PreToolUse hook backstops Writes too).
_SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{30,})\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    re.compile(r"[Aa]uthorization\s*:\s*Bearer\s+[A-Za-z0-9._-]{20,}"),
]


def _die(msg: str) -> None:
    """Print to stderr and exit non-zero (no bundle written)."""
    print(msg, file=sys.stderr)
    raise SystemExit(1)


def _frontmatter_block(text: str) -> str:
    """Return the leading `---`...`---` YAML block, or '' if absent."""
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[: end] if end != -1 else ""


def _fm_value(block: str, key: str) -> str:
    """Pull a top-level scalar `key: "value"` (or `key: value`) from the block."""
    m = re.search(rf'(?m)^{re.escape(key)}:\s*(.*)$', block)
    if not m:
        return ""
    raw = m.group(1).strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
        raw = raw[1:-1]
    return raw


def slugify(title: str) -> str:
    """Slugify a title the way the website's filename-is-slug convention expects."""
    norm = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    norm = norm.lower()
    norm = re.sub(r"[^a-z0-9]+", "-", norm)
    return norm.strip("-")


def find_secret(text: str) -> str | None:
    """Return a short reason if the text carries key-shaped material, else None."""
    for pat in _SECRET_PATTERNS:
        m = pat.search(text)
        if m:
            return f"matches {pat.pattern!r}"
    return None


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        _die("usage: emit_bundle.py <path-to-authored-article.md>")

    note_path = Path(argv[1])
    if not note_path.is_file():
        _die(f"no such file: {note_path}")

    text = note_path.read_text(encoding="utf-8")

    # 1. Marker guard — refuse while the narrative is still the unauthored stub.
    if AUTHOR_MARKER in text:
        _die(
            'narrative not authored — write the "## Why this can be trusted" '
            "section (replace the stub), then re-run emit."
        )

    # 2. Secret backstop — never ship a key.
    reason = find_secret(text)
    if reason is not None:
        _die(f"secret material found in the note ({reason}) — refusing to emit. Remove it first.")

    # 3. Slug + provenance from the frontmatter.
    block = _frontmatter_block(text)
    if not block:
        _die("no YAML frontmatter found — is this a field note from `orionfold field-note`?")

    title = _fm_value(block, "title")
    slug = slugify(title) or note_path.parent.name
    run_id = _fm_value(block, "run_id")
    config_hash = _fm_value(block, "config_hash")
    recommended = _fm_value(block, "recommended")

    # 4. Assemble the bundle (gitignored staging dir, relative to CWD = repo root).
    bundle = Path("_field-notes") / slug / "bundle"
    (bundle / "hero").mkdir(parents=True, exist_ok=True)

    (bundle / "article.md").write_text(text, encoding="utf-8")

    manifest = {
        "slug": slug,
        "target_collection": "story",
        "run_id": run_id,
        "config_hash": config_hash,
        "recommended": recommended,
        "source_export": "orionfold field-note",
        "hero_convention": f"src/assets/story/{slug}/hero.png",
    }
    (bundle / "bundle.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    (bundle / "hero" / "README.md").write_text(
        f"# Hero image for `{slug}`\n\n"
        f"Drop a `hero.png` (or `.jpeg`) in this folder, then on the website copy it to "
        f"`src/assets/story/{slug}/hero.png` and add to the article frontmatter:\n\n"
        "```yaml\n"
        f"hero: ../../assets/story/{slug}/hero.png\n"
        'heroAlt: "describe the image"\n'
        "```\n\n"
        "The `story` collection's `hero`/`heroAlt` fields are optional — skip this if "
        "the post needs no hero (the card falls back to a generated cover).\n",
        encoding="utf-8",
    )

    print(f"bundle written to {bundle}", file=sys.stderr)
    print(
        "next: copy this bundle's article.md into ~/orionfold/website/src/content/story/"
        f"{slug}.md (and the hero per hero/README.md) when ready.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main(sys.argv)
