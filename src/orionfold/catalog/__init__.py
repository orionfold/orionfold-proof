"""Bundled model catalog — reference data that ships inside the wheel.

Loaded via ``importlib.resources`` (like ``orionfold.data`` datasets) so it resolves identically
from a source checkout or an installed wheel. The data is static for the process lifetime, so the
load is cached.
"""

from __future__ import annotations

import json
from functools import cache
from importlib import resources

from orionfold.catalog.models import ModelCatalog


@cache
def load_catalog() -> ModelCatalog:
    """Load and validate the bundled catalog (cached)."""
    raw = (resources.files("orionfold.catalog") / "catalog.json").read_text("utf-8")
    return ModelCatalog.model_validate(json.loads(raw))
