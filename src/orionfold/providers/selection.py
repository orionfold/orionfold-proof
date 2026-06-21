"""Selection panel — the model picker's data, resolved server-side.

Merges the bundled catalog (which models exist) with the live registry (which providers are
available right now) and the keyless mocks into one read-only structure the cockpit renders.
Carries NO credentials — provider labels and model ids only. Pure selection metadata: it never
enters config_hash or the receipt.
"""

from __future__ import annotations

from pydantic import BaseModel

from orionfold.catalog import CostClass, Tier, load_catalog
from orionfold.domain.models import Privacy
from orionfold.providers.registry import _build, available_candidates


class SelectionModel(BaseModel):
    candidate_id: str  # the id sent to the run, e.g. "anthropic:claude-opus-4-8"
    model: str
    display_name: str
    tier: Tier
    cost_class: CostClass
    context_window: int | None = None
    latest: bool = False
    recommended: bool = False


class SelectionGroup(BaseModel):
    provider_id: str
    label: str
    privacy: Privacy
    available: bool
    supports_custom: bool  # real providers True; mocks False
    candidate_id: str | None = None  # set for mocks (group is one candidate); None for model providers
    models: list[SelectionModel] = []


class SelectionPanel(BaseModel):
    providers: list[SelectionGroup]


def selection_panel() -> SelectionPanel:
    """Build the picker panel for the current environment."""
    registry = _build()
    available_ids = set(registry)
    catalog = load_catalog()
    catalog_ids = {p.id for p in catalog.providers}
    groups: list[SelectionGroup] = []

    # Mocks first — the default keyless path. In the registry, not the catalog.
    for cand in available_candidates():
        if cand.provider_id in catalog_ids:
            continue
        groups.append(
            SelectionGroup(
                provider_id=cand.provider_id,
                label=registry[cand.provider_id][0].label,
                privacy=cand.privacy,
                available=True,
                supports_custom=False,
                candidate_id=cand.id,
                models=[],
            )
        )

    # Catalog providers — each model is a selectable candidate; greyed when unavailable.
    for provider in catalog.providers:
        groups.append(
            SelectionGroup(
                provider_id=provider.id,
                label=provider.label,
                privacy=provider.privacy,
                available=provider.id in available_ids,
                supports_custom=True,
                candidate_id=None,
                models=[
                    SelectionModel(
                        candidate_id=f"{provider.id}:{m.id}",
                        model=m.id,
                        display_name=m.display_name,
                        tier=m.tier,
                        cost_class=m.cost_class,
                        context_window=m.context_window,
                        latest=m.latest,
                        recommended=m.recommended,
                    )
                    for m in provider.models
                ],
            )
        )
    return SelectionPanel(providers=groups)
