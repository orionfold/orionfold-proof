"""Schema for bundled decision recipes — named comparison presets.

A recipe declares SEMANTIC intent (a family/tier/privacy/provider filter), not hardcoded model
ids, so it resolves against whatever the current environment makes available. Like the catalog,
recipes are pre-run SELECTION scaffolding: they never enter ``config_hash`` or the receipt.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator

from orionfold.catalog import Tier
from orionfold.domain.models import Privacy

PickStrategy = Literal["recommended", "cheapest", "latest"]


class Selector(BaseModel):
    label: str  # human tag shown in the resolved panel, e.g. "Economy", "Cloud frontier"
    family: str | None = None  # catalog family: claude | gpt | gemini | llama
    tier: Tier | None = None
    privacy: Privacy | None = None
    provider: str | None = None  # pin to one provider id (e.g. "ollama")
    pick: PickStrategy = "recommended"


class Recipe(BaseModel):
    id: str
    title: str
    subtitle: str
    decision_question: str
    selectors: list[Selector]

    @model_validator(mode="after")
    def _non_empty(self) -> "Recipe":
        if not self.selectors:
            raise ValueError(f"recipe {self.id} has no selectors")
        return self


class RecipeBook(BaseModel):
    version: int
    recipes: list[Recipe]

    @model_validator(mode="after")
    def _unique_ids(self) -> "RecipeBook":
        ids = [r.id for r in self.recipes]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate recipe id")
        return self
