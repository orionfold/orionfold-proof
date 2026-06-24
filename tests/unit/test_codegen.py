"""Guards for the Python→TS codegen (single source of truth, ADR-0004 §6).

The committed generated file MUST match what the renderer produces from the canonical Python
map. If someone edits ``DEFAULT_THRESHOLDS`` in ``scoring/rubric.py`` without running
``uv run orionfold codegen``, the file goes stale — this test fails so CI catches it before the
frontend ships a divergent value.
"""

from __future__ import annotations

import json

from orionfold.codegen import THRESHOLDS_TS_PATH, render_thresholds_ts
from orionfold.scoring.rubric import DEFAULT_THRESHOLDS


def test_committed_thresholds_file_is_up_to_date() -> None:
    """The committed thresholds.generated.ts is byte-identical to a fresh render.

    Run ``uv run orionfold codegen`` to fix a failure here.
    """
    committed = THRESHOLDS_TS_PATH.read_text(encoding="utf-8")
    assert committed == render_thresholds_ts(), (
        "thresholds.generated.ts is stale — run `uv run orionfold codegen`."
    )


def test_rendered_ts_carries_the_canonical_values() -> None:
    """Every Python threshold appears in the generated TS with its exact numeric form."""
    rendered = render_thresholds_ts()
    for kind, value in DEFAULT_THRESHOLDS.items():
        assert f"{kind}: {json.dumps(value)}" in rendered
    # keypoint MUST stay 0.8 — the canonical mock matrix resolves to keypoint@0.8 (467ddd96c9a5).
    assert "keypoint: 0.8" in rendered
    # The TS union type is derived from the keys, so a new kind flows through without a hand edit.
    assert 'export type TunableKind = "similarity" | "keypoint" | "judge";' in rendered
