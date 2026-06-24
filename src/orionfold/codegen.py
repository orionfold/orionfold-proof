"""Codegen for cross-language constants the frontend must share with the Python core.

Single-source-of-truth mechanism (ADR-0004 §6): canonical values live in Python; the
frontend consumes a *generated* TypeScript module rather than a hand-mirrored literal that
can silently drift. ``orionfold codegen`` writes the file; a backend test regenerates into a
buffer and asserts a byte-match with the committed copy, so editing the Python source without
regenerating fails CI.

Currently generates the per-kind default thresholds (``DEFAULT_THRESHOLDS``). Keep the
rendered values numerically identical to the Python map — keypoint MUST stay 0.8 (the canonical
mock matrix resolves to keypoint@0.8 → config_hash 467ddd96c9a5).
"""

from __future__ import annotations

import json
from pathlib import Path

from orionfold.scoring.rubric import DEFAULT_THRESHOLDS

# Generated relative to the repo root (the package lives at ``src/orionfold``).
_REPO_ROOT = Path(__file__).resolve().parents[2]
THRESHOLDS_TS_PATH = _REPO_ROOT / "web" / "src" / "features" / "proof" / "thresholds.generated.ts"

_HEADER = (
    "// GENERATED — DO NOT EDIT. Run `uv run orionfold codegen` to regenerate.\n"
    "// Canonical source: src/orionfold/scoring/rubric.py (DEFAULT_THRESHOLDS).\n"
    "// Per-kind default passing threshold (0..1). Similarity is lenient (0.55 — paraphrased\n"
    "// summaries score low on lexical overlap; 0.80 wrongly reads them as \"no winner\");\n"
    "// keypoint/judge stay strict (0.80). A backend test freezes these values + asserts this\n"
    "// file matches the Python map byte-for-byte.\n"
)


def render_thresholds_ts() -> str:
    """Render the ``thresholds.generated.ts`` source from the canonical Python map.

    Deterministic: keys are emitted in the Python map's insertion order; numbers use ``json``
    formatting so ``0.8`` stays ``0.8`` (not ``0.80``). The TS type is derived from the keys, so
    adding a kind to the Python map flows through without a hand edit.
    """
    entries = ",\n".join(
        f"  {key}: {json.dumps(value)}" for key, value in DEFAULT_THRESHOLDS.items()
    )
    union = " | ".join(f'"{key}"' for key in DEFAULT_THRESHOLDS)
    return (
        f"{_HEADER}\n"
        f"export type TunableKind = {union};\n\n"
        f"export const DEFAULT_THRESHOLDS: Record<TunableKind, number> = {{\n"
        f"{entries},\n"
        f"}};\n"
    )


def write_generated_files() -> list[Path]:
    """Write every generated artifact to disk; return the paths written."""
    THRESHOLDS_TS_PATH.write_text(render_thresholds_ts(), encoding="utf-8")
    return [THRESHOLDS_TS_PATH]
