"""Local model overlay (~/.orionfold/models.json) for hf-own-models.

Round-trip, atomic write, fail-soft reads (absent/corrupt → []), dedupe by id. The overlay is
user data the selection panel reads on every render, so a broken file must never raise.
"""

from __future__ import annotations

import pytest

from orionfold.catalog.models import CatalogModel
from orionfold.catalog.overlay import add_to_overlay, load_overlay, overlay_path


@pytest.fixture(autouse=True)
def _isolated_overlay(tmp_path, monkeypatch):
    """Point the overlay at a temp file so we never touch the real ~/.orionfold/models.json."""
    monkeypatch.setenv("ORIONFOLD_MODELS_OVERLAY", str(tmp_path / "models.json"))


def _model(model_id: str, repo_id: str | None = None) -> CatalogModel:
    return CatalogModel(
        id=model_id,
        display_name=model_id,
        family="hf",
        tier="balanced",
        cost_class="free",
        pricing=None,
        repo_id=repo_id or model_id,
    )


def test_absent_overlay_loads_empty():
    assert load_overlay() == []


def test_add_then_load_round_trips():
    m = _model("hf.co/Orionfold/Saul-7B-Instruct-v1-GGUF")
    add_to_overlay(m)
    loaded = load_overlay()
    assert len(loaded) == 1
    assert loaded[0].id == m.id
    assert loaded[0].repo_id == m.repo_id


def test_add_dedupes_by_id():
    add_to_overlay(_model("hf.co/x/y"))
    add_to_overlay(_model("hf.co/x/y"))  # same id again
    add_to_overlay(_model("hf.co/a/b"))
    ids = [m.id for m in load_overlay()]
    assert ids.count("hf.co/x/y") == 1
    assert set(ids) == {"hf.co/x/y", "hf.co/a/b"}


def test_re_add_replaces_entry_in_place():
    add_to_overlay(_model("hf.co/x/y"))
    updated = _model("hf.co/x/y")
    updated.display_name = "Renamed"
    add_to_overlay(updated)
    loaded = load_overlay()
    assert len(loaded) == 1 and loaded[0].display_name == "Renamed"


def test_corrupt_overlay_loads_empty_without_raising():
    overlay_path().write_text("{ this is not json", encoding="utf-8")
    assert load_overlay() == []  # fail-soft, never crashes selection


def test_non_list_overlay_loads_empty():
    overlay_path().write_text('{"models": []}', encoding="utf-8")  # object, not a list
    assert load_overlay() == []


def test_bad_row_is_skipped_not_fatal():
    # One invalid entry must not discard the whole overlay.
    overlay_path().write_text(
        '[{"id": "hf.co/ok/model", "display_name": "OK", "family": "hf", '
        '"tier": "balanced", "cost_class": "free"}, {"id": "missing-fields"}]',
        encoding="utf-8",
    )
    loaded = load_overlay()
    assert [m.id for m in loaded] == ["hf.co/ok/model"]


def test_atomic_write_leaves_no_tmp_file():
    add_to_overlay(_model("hf.co/x/y"))
    tmp = overlay_path().with_name(f"{overlay_path().name}.tmp")
    assert not tmp.exists()
