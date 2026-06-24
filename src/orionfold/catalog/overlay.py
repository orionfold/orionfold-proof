"""Local model overlay — user-pulled HF/GGUF models recorded outside the bundled catalog.

When ``orionfold pull <repo_id>`` succeeds, the model is appended to ``~/.orionfold/models.json``
so it becomes a first-class, selectable candidate alongside the curated Orionfold roster — even
if it was *not* in the bundled catalog. This is **user data**: gitignored, home-scoped, never in
the wheel.

Integrity rules (spec §4):
- **Success-gated:** only the ``pull`` CLI writes here, and only after Ollama confirms ``success``.
- **Atomic write:** a temp-file + replace, so a crash never leaves a half-written overlay.
- **Fail-soft reads:** an absent or corrupt file resolves to ``[]`` and never raises — a broken
  overlay must never take down the selection panel.
- **Dedupe by id:** re-pulling a model updates its entry in place rather than duplicating it.

The overlay is intent (a record of what was pulled); ``GET /api/tags`` is truth (what is actually
present). Selection reconciles the two, so a GC'd model self-corrects to "Pull to enable".
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from orionfold.catalog.models import CatalogModel


def overlay_path() -> Path:
    """Location of the local overlay file (home-scoped, beside the proof DB)."""
    override = os.environ.get("ORIONFOLD_MODELS_OVERLAY")
    if override:
        return Path(override)
    return Path.home() / ".orionfold" / "models.json"


def load_overlay() -> list[CatalogModel]:
    """Return the overlay's models, or ``[]`` if absent/corrupt/invalid (never raises)."""
    path = overlay_path()
    try:
        raw = path.read_text("utf-8")
    except OSError:
        return []
    try:
        data = json.loads(raw)
    except ValueError:
        return []
    if not isinstance(data, list):
        return []
    models: list[CatalogModel] = []
    for entry in data:
        try:
            models.append(CatalogModel.model_validate(entry))
        except Exception:
            continue  # skip an individual bad row rather than discard the whole overlay
    return models


def add_to_overlay(model: CatalogModel) -> None:
    """Record ``model`` in the overlay, replacing any existing entry with the same id.

    Atomic: writes a sibling temp file and ``os.replace``s it over the target, so a reader
    never observes a partial file. Creates ``~/.orionfold/`` if needed.
    """
    existing = [m for m in load_overlay() if m.id != model.id]
    existing.append(model)
    path = overlay_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        [m.model_dump(mode="json", exclude_none=True) for m in existing], indent=2
    )
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(payload + "\n", encoding="utf-8")
    os.replace(tmp, path)
