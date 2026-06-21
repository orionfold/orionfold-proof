"""Bundled decision recipes — reference data that ships inside the wheel.

Loaded via ``importlib.resources`` (like ``orionfold.catalog``) so it resolves identically from a
source checkout or an installed wheel. Static for the process lifetime, so the load is cached.
"""

from __future__ import annotations

import json
from functools import cache
from importlib import resources

from orionfold.recipes.models import Recipe, RecipeBook, Selector

__all__ = ["Recipe", "RecipeBook", "Selector", "load_recipes"]


@cache
def load_recipes() -> RecipeBook:
    """Load and validate the bundled recipe book (cached)."""
    raw = (resources.files("orionfold.recipes") / "recipes.json").read_text("utf-8")
    return RecipeBook.model_validate(json.loads(raw))
