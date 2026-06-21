"""Resolve recipe selectors against the live catalog ∩ availability.

Pure SELECTION metadata: mirrors ``providers.selection`` (catalog + ``_build()`` availability).
Carries no credentials — only provider labels, model ids, and the env-var NAME a provider needs.
"""

from __future__ import annotations

from pydantic import BaseModel

from orionfold.catalog import CostClass, load_catalog
from orionfold.catalog.models import CatalogModel, CatalogProvider
from orionfold.config.keys import CLOUD_KEY_NAMES
from orionfold.providers.registry import _build
from orionfold.recipes import Recipe, Selector, load_recipes


class ResolvedSelector(BaseModel):
    label: str
    candidate_id: str
    display_name: str
    provider_id: str
    cost_class: CostClass


class UnmetSelector(BaseModel):
    label: str
    needs_provider_id: str
    needs_provider_label: str
    key_name: str


class ResolvedRecipe(BaseModel):
    id: str
    title: str
    subtitle: str
    decision_question: str
    candidate_ids: list[str]
    resolved: list[ResolvedSelector]
    unmet: list[UnmetSelector]


class RecipesPanel(BaseModel):
    recipes: list[ResolvedRecipe]


def _price(model: CatalogModel) -> float | None:
    return model.pricing.input_per_mtok if model.pricing else None


def _matches(selector: Selector, provider: CatalogProvider, model: CatalogModel) -> bool:
    if selector.family is not None and model.family != selector.family:
        return False
    if selector.tier is not None and model.tier != selector.tier:
        return False
    if selector.privacy is not None and provider.privacy != selector.privacy:
        return False
    if selector.provider is not None and provider.id != selector.provider:
        return False
    return True


def _pick(selector: Selector, rows: list[tuple[CatalogProvider, CatalogModel]]):
    if selector.pick == "cheapest":
        return min(rows, key=lambda r: _price(r[1]) if _price(r[1]) is not None else 0.0)
    if selector.pick == "latest":
        return next((r for r in rows if r[1].latest), rows[0])
    # "recommended": recommended flag, then latest, then cheapest, then first.
    for r in rows:
        if r[1].recommended:
            return r
    for r in rows:
        if r[1].latest:
            return r
    priced = [r for r in rows if _price(r[1]) is not None]
    if priced:
        return min(priced, key=lambda r: _price(r[1]))
    return rows[0]


def _resolve_one(selector: Selector, available: set[str]):
    catalog = load_catalog()
    matches = [
        (p, m) for p in catalog.providers for m in p.models if _matches(selector, p, m)
    ]
    if not matches:
        return None  # selector references something the catalog no longer carries — skip
    avail = [r for r in matches if r[0].id in available]
    if avail:
        provider, model = _pick(selector, avail)
        return ResolvedSelector(
            label=selector.label,
            candidate_id=f"{provider.id}:{model.id}",
            display_name=model.display_name,
            provider_id=provider.id,
            cost_class=model.cost_class,
        )
    # Unmet: suggest the cheapest unavailable match's provider (must be a known cloud key).
    cloud = [r for r in matches if r[0].id in CLOUD_KEY_NAMES]
    if not cloud:
        return None
    provider, _ = min(
        cloud, key=lambda r: _price(r[1]) if _price(r[1]) is not None else float("inf")
    )
    return UnmetSelector(
        label=selector.label,
        needs_provider_id=provider.id,
        needs_provider_label=provider.label,
        key_name=CLOUD_KEY_NAMES[provider.id],
    )


def _resolve_recipe(recipe: Recipe, available: set[str]) -> ResolvedRecipe:
    resolved: list[ResolvedSelector] = []
    unmet: list[UnmetSelector] = []
    for selector in recipe.selectors:
        outcome = _resolve_one(selector, available)
        if isinstance(outcome, ResolvedSelector):
            resolved.append(outcome)
        elif isinstance(outcome, UnmetSelector):
            unmet.append(outcome)
    seen: set[str] = set()
    candidate_ids: list[str] = []
    for s in resolved:
        if s.candidate_id not in seen:
            seen.add(s.candidate_id)
            candidate_ids.append(s.candidate_id)
    return ResolvedRecipe(
        id=recipe.id,
        title=recipe.title,
        subtitle=recipe.subtitle,
        decision_question=recipe.decision_question,
        candidate_ids=candidate_ids,
        resolved=resolved,
        unmet=unmet,
    )


def resolve_recipes() -> RecipesPanel:
    """Resolve every bundled recipe for the current environment."""
    available = set(_build())
    return RecipesPanel(
        recipes=[_resolve_recipe(r, available) for r in load_recipes().recipes]
    )
