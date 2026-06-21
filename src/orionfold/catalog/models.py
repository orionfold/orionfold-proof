"""Schema for the bundled model catalog (provider → model → capabilities).

The catalog is pre-run *selection* scaffolding — it informs which models to compare. It is NOT
run provenance: it never enters ``config_hash`` or the receipt. Prices are dated, sourced LIST
prices, never a claim the receipt is meant to prove (a measured receipt cost always outranks a
catalog list price downstream).
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, model_validator

from orionfold.domain.models import Privacy

Tier = Literal["frontier", "balanced", "economy"]
CostClass = Literal["free", "$", "$$", "$$$"]


class ModelPricing(BaseModel):
    input_per_mtok: float  # USD per 1M input tokens — a LIST price, not a claim
    output_per_mtok: float
    currency: str = "USD"
    as_of: date  # ISO date the price was recorded
    source: str  # provider pricing-page URL


class CatalogModel(BaseModel):
    id: str  # exact string sent to the provider API (e.g. "claude-opus-4-8")
    display_name: str
    family: str  # "claude" | "gpt" | "gemini" | "llama" — enables "same family across providers"
    tier: Tier
    context_window: int | None = None
    cost_class: CostClass  # stable selection signal; local = "free"
    pricing: ModelPricing | None = None  # None for local models
    latest: bool = False
    recommended: bool = False


class CatalogProvider(BaseModel):
    id: str  # matches provider registry ids: anthropic, openai, ollama, ...
    label: str
    privacy: Privacy
    default_model: str  # must equal one models[].id (validated)
    models: list[CatalogModel]

    @model_validator(mode="after")
    def _check(self) -> "CatalogProvider":
        ids = [m.id for m in self.models]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate model id in provider {self.id}")
        if self.default_model not in ids:
            raise ValueError(
                f"default_model {self.default_model!r} not in provider {self.id} models"
            )
        return self


class ModelCatalog(BaseModel):
    version: int  # catalog schema version (starts at 1)
    as_of: date  # catalog-wide snapshot date
    providers: list[CatalogProvider]
