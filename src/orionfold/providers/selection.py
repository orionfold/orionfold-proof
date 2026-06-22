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

# Picker labels for the two simulated mocks when shown under the single "Mock" provider in
# Sandbox. The engine still routes on the bare ids (mock_good / mock_bad) — these are display only.
_MOCK_DISPLAY = {"mock_good": "Good model", "mock_bad": "Bad model"}


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


def selection_panel(sandbox: bool = False) -> SelectionPanel:
    """Build the picker panel for the current environment.

    The simulated Mock provider only appears when ``sandbox`` is on (opt-in). It is shown as a
    single "Mock" provider exposing the two mocks as Good/Bad models; the candidate ids stay bare
    (``mock_good`` / ``mock_bad``) so the engine routing is unchanged.
    """
    registry = _build()
    available_ids = set(registry)
    catalog = load_catalog()
    catalog_ids = {p.id for p in catalog.providers}
    groups: list[SelectionGroup] = []

    # Sandbox only: one "Mock" provider grouping the keyless mocks as Good/Bad models.
    if sandbox:
        mocks = [c for c in available_candidates() if c.provider_id not in catalog_ids]
        if mocks:
            groups.append(
                SelectionGroup(
                    provider_id="mock",
                    label="Mock",
                    privacy=mocks[0].privacy,
                    available=True,
                    supports_custom=False,
                    candidate_id=None,
                    models=[
                        SelectionModel(
                            candidate_id=c.id,
                            model=c.id.removeprefix("mock_"),
                            display_name=_MOCK_DISPLAY.get(c.id, c.label),
                            tier="economy",
                            cost_class="free",
                            context_window=None,
                            latest=False,
                            recommended=False,
                        )
                        for c in mocks
                    ],
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
