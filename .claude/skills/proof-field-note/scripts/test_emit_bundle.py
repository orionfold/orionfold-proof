"""Self-test for emit_bundle.py — run directly, not via pytest.

This skill is dev-only and gitignored-bound (Layer B), so it lives outside the
package's pytest suite. Run it with:

    python3 .claude/skills/proof-field-note/scripts/test_emit_bundle.py

Exits 0 on success, non-zero with a diff on the first failure.

Covers spec section 6:
  - marker still present        -> non-zero exit, NO bundle written
  - authored note               -> bundle/{article.md, bundle.json, hero/README.md},
                                   correct provenance, figures stayed inline
  - a key-shaped token present  -> secret backstop trips (non-zero, no bundle)

The fake key in the secret case is assembled at runtime so this source carries
no key-shaped literal and no secret-named assignment -- the repo's secrets-guard
hook blocks both, and those are exactly the shapes emit_bundle.py must catch.
(For the same reason, identifiers here avoid the suffixes KEY/SECRET/TOKEN.)
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EMIT = HERE / "emit_bundle.py"

# A minimal scaffold mirroring Layer A's `build_field_note` output shape: a
# leading YAML frontmatter block (a superset of the website `story` schema), an
# inline SVG figure, an evidence body, and the narrative stub WITH its author
# marker. Tests flip the marker / inject a token by string replacement.
MARKER = "<!-- author: replace this section -->"

# A fake Anthropic-style value, assembled at runtime so no key-shaped literal
# sits in this source. The identifier avoids KEY/SECRET/TOKEN suffixes.
_FAKE_SHAPE = "-".join(["sk", "ant", "api03"]) + "-" + ("a1b2c3d4" * 3)

SCAFFOLD_WITH_MARKER = f"""\
---
artifact: proof-field-note
title: "Which model should I trust for ticket triage?"
date: "2026-06-23"
summary: "claude-haiku-4-5 is the clear pick (80% pass)."
run_id: "run_593bbe577f05"
config_hash: "467ddd96c9a5"
recommended: "claude-haiku-4-5"
tags: [proof, judge]
---

# Which model should I trust for ticket triage?

## Figures

<figure class="fn-diagram"><svg role="img" aria-label="cost vs quality"></svg></figure>

## Evidence

The receipt body lives here.

## Why this can be trusted

{MARKER}

_Write the trust narrative here._

<!-- /author -->
"""

AUTHORED = SCAFFOLD_WITH_MARKER.replace(
    f"{MARKER}\n\n_Write the trust narrative here._\n\n<!-- /author -->",
    "I ran five real tickets through three models. Haiku won on cost and quality.",
)

# An authored note that nonetheless smuggles a key-shaped value -- the secret
# backstop must catch it even though the marker is gone. (Name avoids the
# secret-named-field shape the guard flags.)
LEAKY_NOTE = AUTHORED.replace(
    "Haiku won on cost and quality.",
    f"Haiku won. (leaked credential {_FAKE_SHAPE})",
)


def _run(scaffold_text: str, tmp: Path) -> subprocess.CompletedProcess[str]:
    note = tmp / "run_593bbe577f05" / "article.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(scaffold_text, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(EMIT), str(note)],
        capture_output=True,
        text=True,
        cwd=tmp,
    )


def _check(cond: bool, msg: str) -> None:
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        raise SystemExit(1)


def test_marker_present_refuses() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        result = _run(SCAFFOLD_WITH_MARKER, tmp)
        _check(result.returncode != 0, "marker present should exit non-zero")
        _check("not authored" in result.stderr.lower(), "should explain the unauthored stub")
        bundles = list(tmp.glob("**/bundle"))
        _check(not bundles, f"no bundle should be written, found {bundles}")


def test_authored_assembles_bundle() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        result = _run(AUTHORED, tmp)
        _check(result.returncode == 0, f"authored note should exit 0, got {result.stderr}")

        slug = "which-model-should-i-trust-for-ticket-triage"
        bundle = tmp / "_field-notes" / slug / "bundle"
        article = bundle / "article.md"
        manifest = bundle / "bundle.json"
        hero_readme = bundle / "hero" / "README.md"

        _check(article.is_file(), "bundle/article.md should exist")
        _check(manifest.is_file(), "bundle/bundle.json should exist")
        _check(hero_readme.is_file(), "bundle/hero/README.md should exist")

        body = article.read_text(encoding="utf-8")
        _check(MARKER not in body, "the author marker must be gone from the shipped article")
        _check("<svg" in body, "figures must stay inline in the article (no asset extraction)")

        data = json.loads(manifest.read_text(encoding="utf-8"))
        _check(data["slug"] == slug, f"manifest slug wrong: {data['slug']}")
        _check(data["target_collection"] == "story", "manifest target_collection should be story")
        _check(data["run_id"] == "run_593bbe577f05", f"manifest run_id wrong: {data['run_id']}")
        _check(data["config_hash"] == "467ddd96c9a5", "manifest config_hash wrong")
        _check(data["recommended"] == "claude-haiku-4-5", "manifest recommended wrong")
        _check(slug in hero_readme.read_text(encoding="utf-8"), "hero README should name the slug path")


def test_secret_backstop_trips() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        result = _run(LEAKY_NOTE, tmp)
        _check(result.returncode != 0, "a key-shaped token should exit non-zero")
        _check("secret" in result.stderr.lower(), "should explain the secret backstop")
        bundles = list(tmp.glob("**/bundle"))
        _check(not bundles, f"no bundle should be written when a secret is found, found {bundles}")


def main() -> None:
    test_marker_present_refuses()
    test_authored_assembles_bundle()
    test_secret_backstop_trips()
    print("OK -- emit_bundle.py self-test passed (3 cases)")


if __name__ == "__main__":
    main()
