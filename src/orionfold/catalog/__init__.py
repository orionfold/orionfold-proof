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


def default_model_for(provider_id: str) -> str:
    """The catalog's default model for a provider — the single source of truth.

    Raises ``KeyError`` if the provider id has no catalog entry, so the registry and catalog can
    never silently drift.
    """
    for provider in load_catalog().providers:
        if provider.id == provider_id:
            return provider.default_model
    raise KeyError(f"no catalog entry for provider {provider_id!r}")
