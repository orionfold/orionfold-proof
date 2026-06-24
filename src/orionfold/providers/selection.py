"""Selection panel — the model picker's data, resolved server-side.

Merges the bundled catalog (which models exist) with the live registry (which providers are
available right now) and the keyless mocks into one read-only structure the cockpit renders.
Carries NO credentials — provider labels and model ids only. Pure selection metadata: it never
enters config_hash or the receipt.

Curated Orionfold (HF/GGUF) models and any user-pulled overlay model carry a ``repo_id``. For
those, availability is **per model**, reconciled against the live ``GET /api/tags`` set: a model
is ``available`` iff its tag has actually been pulled, else it shows a "Pull to enable" reason.
The Ollama daemon being down degrades gracefully — Orionfold models go unavailable-with-reason
while cloud candidates stay present (this path never raises).
"""

from __future__ import annotations

from pydantic import BaseModel

from orionfold.catalog import CostClass, Tier, load_catalog
from orionfold.catalog.models import CatalogModel
from orionfold.catalog.overlay import load_overlay
from orionfold.domain.models import Privacy
from orionfold.providers.http import ProviderError
from orionfold.providers.ollama_pull import list_pulled, normalize_tag, resolve_host
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
    family: str | None = None  # "orionfold" tags curated HF/GGUF models in the cockpit
    repo_id: str | None = None  # the HF repo to pull; drives the "Pull to enable" hint
    available: bool = True  # per-model gate for pullable models (cloud/standard models inherit group)
    reason: str | None = None  # why a pullable model is unavailable (e.g. "Pull to enable")


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


def _pulled_tags() -> set[str] | None:
    """Normalized set of pulled Ollama model tags, or ``None`` if the daemon is unreachable.

    ``None`` (not ``set()``) distinguishes "daemon down — can't tell" (every Orionfold model
    unavailable, reason "Ollama not running") from "daemon up, nothing pulled yet" (reason
    "Pull to enable"). Either way this never raises into the selection path.
    """
    try:
        return {normalize_tag(t) for t in list_pulled(resolve_host())}
    except ProviderError:
        return None


def _ollama_model_rows(
    models: list[CatalogModel], pulled: set[str] | None
) -> list[SelectionModel]:
    """Build selection rows for the Ollama provider, reconciling pullable models against tags.

    A model with no ``repo_id`` is a standard local model (llama3.2, …) and stays ``available``
    (the group-level gate already reflects the daemon). A model *with* a ``repo_id`` is gated
    per model: pulled → available; daemon down → unavailable "Ollama not running"; not pulled →
    unavailable "Pull to enable …".
    """
    rows: list[SelectionModel] = []
    for m in models:
        available = True
        reason: str | None = None
        if m.repo_id is not None:
            if pulled is None:
                available, reason = False, "Ollama not running — start `ollama serve`"
            elif normalize_tag(m.repo_id) in pulled:
                available = True
            else:
                available = False
                reason = f"Not pulled — run: orionfold pull {m.repo_id}"
        rows.append(
            SelectionModel(
                candidate_id=f"ollama:{m.id}",
                model=m.id,
                display_name=m.display_name,
                tier=m.tier,
                cost_class=m.cost_class,
                context_window=m.context_window,
                latest=m.latest,
                recommended=m.recommended,
                family=m.family,
                repo_id=m.repo_id,
                available=available,
                reason=reason,
            )
        )
    return rows


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
    # Live truth for pullable models, resolved once. ``None`` ⇒ daemon unreachable.
    pulled = _pulled_tags()
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
        if provider.id == "ollama":
            # Merge bundled roster ⊕ user overlay; dedupe by id (bundled wins on collision),
            # then reconcile every pullable model against the live tag set.
            seen = {m.id for m in provider.models}
            merged = list(provider.models) + [m for m in load_overlay() if m.id not in seen]
            models = _ollama_model_rows(merged, pulled)
        else:
            models = [
                SelectionModel(
                    candidate_id=f"{provider.id}:{m.id}",
                    model=m.id,
                    display_name=m.display_name,
                    tier=m.tier,
                    cost_class=m.cost_class,
                    context_window=m.context_window,
                    latest=m.latest,
                    recommended=m.recommended,
                    family=m.family,
                )
                for m in provider.models
            ]
        groups.append(
            SelectionGroup(
                provider_id=provider.id,
                label=provider.label,
                privacy=provider.privacy,
                available=provider.id in available_ids,
                supports_custom=True,
                candidate_id=None,
                models=models,
            )
        )
    return SelectionPanel(providers=groups)
