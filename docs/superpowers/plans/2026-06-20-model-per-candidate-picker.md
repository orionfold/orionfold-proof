# Model-per-candidate Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user pick a specific model per provider (and compare several models of the same provider in one run) through a provider-grouped chip picker, with a custom-model escape hatch.

**Architecture:** The backend is already model-aware (`Candidate.model` feeds `config_hash`; providers do `candidate.model or default_model`). This plan adds (1) `build_candidates()` to widen run validation from a fixed one-per-provider set to "available provider + non-empty model", (2) a server-merged `GET /api/selection` panel, and (3) a `CandidatePicker` frontend that renders it. Composite `provider:model` candidate ids; mocks stay bare-id + `model=None` so the test contract is byte-identical.

**Tech Stack:** Python 3.12 / FastAPI / Pydantic / pytest; Vite / React / TypeScript / Zod / TanStack Query / Vitest; Playwright.

## Global Constraints

- **`config_hash` payload and `RECEIPT_VERSION = 3` are UNTOUCHED.** The picker is selection, never provenance. Do not edit `proof/engine.py:config_hash` or the receipt schema.
- **Mocks keep bare ids** (`mock_good`, `mock_bad`, `model=None`). Only real providers get composite `provider:model` ids. Mock-only runs/`config_hash`/test-contract strings stay byte-identical.
- **Keyless-safe:** a composite/custom id for an unavailable provider is rejected at validation. Cloud providers are "available" only when their key resolves (existing `_build()` rule); mocks + ollama + lmstudio are always available.
- **No secrets** in `GET /api/selection` (asserted in tests, mirroring `/api/catalog`). Never log/echo/commit keys.
- Split composite ids on the **first** colon so Ollama tags (`ollama:llama3.1:8b`) survive.
- Tailwind v4: CSS vars use the parenthesis shorthand `bg-(--color-x)`, never `bg-[--color-x]`.
- Test-contract strings to preserve: heading "Orionfold Proof", "Connected", button `/Run proof/`, regions "Leaderboard" / "Failure cases" / "Proof Receipt export", "100% (5/5)", "Failure cases (5)", "simulated provider failure".
- Commit directly to `main` (solo project; no per-task branches). Run path validation stays backward-compatible: a bare id still resolves to that provider's default-model candidate.

---

### Task 1: `build_candidates()` — widen run validation

**Files:**
- Modify: `src/orionfold/providers/registry.py` (add `UnknownCandidateError` + `build_candidates`)
- Modify: `src/orionfold/server/routes.py:126-156` (`create_run`) and `:163-188` (`create_run_stream`)
- Test: `tests/unit/test_build_candidates.py` (create)
- Test: `tests/integration/test_proof_api.py` (add one route test)

**Interfaces:**
- Consumes: `registry._build()` (private, same module) → `dict[str, tuple[Provider, str|None]]` (available providers only); `registry.available_candidates()` → `list[Candidate]`; `domain.models.Candidate(id, label, provider_id, privacy, model)`.
- Produces:
  - `class UnknownCandidateError(ValueError)` with attribute `.unknown: list[str]`; `str(err) == "Unknown candidate(s): [...]"`.
  - `build_candidates(candidate_ids: list[str]) -> list[Candidate]` — raises `UnknownCandidateError` on any unresolvable id.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_build_candidates.py`:

```python
"""build_candidates widens run validation: bare ids stay valid (back-compat), composite
provider:model ids resolve for AVAILABLE providers, everything else is rejected (keyless-safe)."""

from __future__ import annotations

import pytest

from orionfold.providers.registry import (
    UnknownCandidateError,
    available_candidates,
    build_candidates,
)


@pytest.fixture(autouse=True)
def _no_keys(tmp_path, monkeypatch):
    """Hermetic: tmp CWD (no .env.local) and every cloud key unset → cloud unavailable."""
    monkeypatch.chdir(tmp_path)
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def test_bare_mock_id_resolves_unchanged():
    [cand] = build_candidates(["mock_good"])
    expected = {c.id: c for c in available_candidates()}["mock_good"]
    assert cand == expected  # byte-identical → config_hash unchanged for mock runs
    assert cand.model is None


def test_bare_local_default_id_resolves_to_default_model():
    [cand] = build_candidates(["ollama"])
    assert cand.provider_id == "ollama"
    assert cand.model  # the catalog default, non-empty


def test_composite_id_for_available_provider_resolves():
    [cand] = build_candidates(["ollama:llama3.2"])
    assert cand.id == "ollama:llama3.2"
    assert cand.provider_id == "ollama"  # BARE provider id — engine routes on this
    assert cand.model == "llama3.2"
    assert cand.label == "Ollama · llama3.2"
    assert cand.privacy == "local"


def test_colon_in_model_is_preserved():
    [cand] = build_candidates(["ollama:llama3.1:8b"])
    assert cand.provider_id == "ollama"
    assert cand.model == "llama3.1:8b"  # split on the FIRST colon only


def test_composite_for_unavailable_provider_is_rejected():
    with pytest.raises(UnknownCandidateError) as exc:
        build_candidates(["anthropic:claude-opus-4-8"])  # no key → unavailable
    assert exc.value.unknown == ["anthropic:claude-opus-4-8"]


def test_empty_model_and_unknown_provider_are_rejected():
    with pytest.raises(UnknownCandidateError) as exc:
        build_candidates(["ollama:", "nope:x", "garbage"])
    assert exc.value.unknown == ["ollama:", "nope:x", "garbage"]


def test_error_message_matches_route_contract():
    with pytest.raises(UnknownCandidateError) as exc:
        build_candidates(["nope:x"])
    assert str(exc.value) == "Unknown candidate(s): ['nope:x']"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_build_candidates.py -q`
Expected: FAIL — `ImportError: cannot import name 'UnknownCandidateError'` / `build_candidates`.

- [ ] **Step 3: Implement `build_candidates` in the registry**

Append to `src/orionfold/providers/registry.py` (after `available_candidates`):

```python
class UnknownCandidateError(ValueError):
    """A requested candidate id can't be resolved to an available provider + model."""

    def __init__(self, unknown: list[str]) -> None:
        self.unknown = unknown
        super().__init__(f"Unknown candidate(s): {unknown}")


def build_candidates(candidate_ids: list[str]) -> list[Candidate]:
    """Resolve request ids into validated candidates.

    - A bare id already offered by ``available_candidates()`` (a mock, or a real provider's
      default model) resolves unchanged — backward compatible.
    - A composite ``provider:model`` id (split on the FIRST colon) resolves iff the provider is
      currently available and ``model`` is a non-empty string. The model becomes part of the
      candidate's identity, which already feeds ``config_hash``.
    - Anything else is collected and raised as :class:`UnknownCandidateError` (keyless-safe: an
      unavailable provider is never in ``_build()``).
    """
    registry = _build()
    by_id = {c.id: c for c in available_candidates()}
    resolved: list[Candidate] = []
    unknown: list[str] = []
    for cid in candidate_ids:
        existing = by_id.get(cid)
        if existing is not None:
            resolved.append(existing)
            continue
        provider_id, sep, model = cid.partition(":")
        if sep and model and provider_id in registry:
            provider = registry[provider_id][0]
            resolved.append(
                Candidate(
                    id=cid,
                    label=f"{provider.label} · {model}",
                    provider_id=provider_id,
                    privacy=provider.privacy,
                    model=model,
                )
            )
        else:
            unknown.append(cid)
    if unknown:
        raise UnknownCandidateError(unknown)
    return resolved
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_build_candidates.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Wire both run routes to `build_candidates`**

In `src/orionfold/server/routes.py`, update the import on line 27:

```python
from orionfold.providers.registry import (
    UnknownCandidateError,
    available_candidates,
    build_candidates,
)
```

In `create_run`, replace the validation block (currently lines 134-140):

```python
        if not body.candidate_ids:
            raise HTTPException(status_code=400, detail="Select at least one candidate")
        try:
            candidates = build_candidates(body.candidate_ids)
        except UnknownCandidateError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
```

In `create_run_stream`, replace the validation block (currently lines 182-188) with the same:

```python
    if not body.candidate_ids:
        raise HTTPException(status_code=400, detail="Select at least one candidate")
    try:
        candidates = build_candidates(body.candidate_ids)
    except UnknownCandidateError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
```

(Both previously built `available = {...}` then `candidates = [available[cid] ...]` — that local `available` dict is now gone in both functions.)

- [ ] **Step 6: Add a route regression test (unavailable composite → 400; bare mock run still works)**

Add to `tests/integration/test_proof_api.py` (uses the existing `client` fixture; set keys unset for determinism):

```python
def test_run_rejects_composite_id_for_unavailable_provider(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    datasets = client.get("/api/datasets").json()
    resp = client.post(
        "/api/runs",
        json={
            "dataset_id": datasets[0]["id"],
            "candidate_ids": ["anthropic:claude-opus-4-8"],
            "brief": {"task_name": "t", "decision_question": "q", "success_criteria": ""},
        },
    )
    assert resp.status_code == 400
    assert "Unknown candidate(s)" in resp.json()["detail"]
```

- [ ] **Step 7: Run backend tests + lint**

Run: `uv run pytest tests/unit/test_build_candidates.py tests/integration/test_proof_api.py tests/unit/test_registry.py -q && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 8: Commit**

```bash
git add src/orionfold/providers/registry.py src/orionfold/server/routes.py tests/unit/test_build_candidates.py tests/integration/test_proof_api.py
git commit -m "feat(run): build_candidates widens validation to provider:model ids

Bare ids stay valid (back-compat); composite provider:model ids resolve for
available providers (model feeds config_hash, unchanged); unavailable providers
rejected (keyless-safe). Both run endpoints use build_candidates.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `GET /api/selection` — server-merged picker panel

**Files:**
- Modify: `src/orionfold/catalog/__init__.py` (re-export `Tier`, `CostClass`)
- Create: `src/orionfold/providers/selection.py`
- Modify: `src/orionfold/server/routes.py` (add `GET /api/selection`)
- Test: `tests/unit/test_selection.py` (create)
- Test: `tests/integration/test_proof_api.py` (add endpoint tests)

**Interfaces:**
- Consumes: `catalog.load_catalog()` → `ModelCatalog`; `catalog.Tier`/`catalog.CostClass` (newly re-exported); `registry._build()`; `registry.available_candidates()`.
- Produces:
  - `SelectionModel(candidate_id, model, display_name, tier, cost_class, context_window, latest, recommended)`
  - `SelectionGroup(provider_id, label, privacy, available, supports_custom, candidate_id, models)`
  - `SelectionPanel(providers: list[SelectionGroup])`
  - `selection_panel() -> SelectionPanel`
  - Route `GET /api/selection -> SelectionPanel`

- [ ] **Step 1: Write the failing unit tests**

Create `tests/unit/test_selection.py`:

```python
"""selection_panel merges catalog (which models exist) + registry (which providers are
available) + mocks into one read-only picker structure. No credentials."""

from __future__ import annotations

import pytest

from orionfold.providers.selection import selection_panel


@pytest.fixture(autouse=True)
def _no_keys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def _by_id(panel):
    return {g.provider_id: g for g in panel.providers}


def test_mocks_come_first_with_no_models_and_no_custom():
    panel = selection_panel()
    first_two = panel.providers[:2]
    assert [g.provider_id for g in first_two] == ["mock_good", "mock_bad"]
    for g in first_two:
        assert g.models == []
        assert g.supports_custom is False
        assert g.candidate_id == g.provider_id  # the group itself is one candidate
        assert g.available is True


def test_catalog_providers_present_with_model_candidate_ids():
    groups = _by_id(selection_panel())
    anthropic = groups["anthropic"]
    assert anthropic.supports_custom is True
    assert anthropic.candidate_id is None
    assert anthropic.models  # populated from the catalog
    sample = anthropic.models[0]
    assert sample.candidate_id == f"anthropic:{sample.model}"


def test_availability_reflects_keys():
    groups = _by_id(selection_panel())
    assert groups["anthropic"].available is False  # no key
    assert groups["ollama"].available is True  # local, keyless


def test_latest_and_recommended_flags_carry_through():
    groups = _by_id(selection_panel())
    anthropic_models = groups["anthropic"].models
    # The catalog marks one latest and at least one recommended for anthropic.
    assert any(m.latest for m in anthropic_models)
    assert any(m.recommended for m in anthropic_models)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_selection.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'orionfold.providers.selection'`.

- [ ] **Step 3: Re-export `Tier`/`CostClass` from the catalog package**

In `src/orionfold/catalog/__init__.py`, change the import line and add `__all__`:

```python
from orionfold.catalog.models import CostClass, ModelCatalog, Tier

__all__ = ["CostClass", "ModelCatalog", "Tier", "default_model_for", "load_catalog"]
```

- [ ] **Step 4: Create `src/orionfold/providers/selection.py`**

```python
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
```

- [ ] **Step 5: Run the unit tests to verify they pass**

Run: `uv run pytest tests/unit/test_selection.py -q`
Expected: PASS (4 passed).

- [ ] **Step 6: Add the route**

In `src/orionfold/server/routes.py`, add the import near the other registry/selection imports:

```python
from orionfold.providers.selection import SelectionPanel, selection_panel
```

Add the endpoint after `get_catalog` (around line 123):

```python
@router.get("/selection")
def get_selection() -> SelectionPanel:
    """The model picker's data: provider groups with availability + catalog models + mocks.

    Read-only and resolved server-side so the cockpit (and later decision recipes) share one
    availability source. Contains no credentials.
    """
    return selection_panel()
```

- [ ] **Step 7: Write the failing endpoint tests**

Add to `tests/integration/test_proof_api.py`:

```python
def test_selection_endpoint_shape_and_mocks_first(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    body = client.get("/api/selection").json()
    providers = body["providers"]
    assert [p["provider_id"] for p in providers[:2]] == ["mock_good", "mock_bad"]
    groups = {p["provider_id"]: p for p in providers}
    assert groups["mock_good"]["candidate_id"] == "mock_good"
    assert groups["mock_good"]["models"] == []
    assert groups["anthropic"]["available"] is False  # no key
    assert groups["ollama"]["available"] is True
    sample = groups["anthropic"]["models"][0]
    assert sample["candidate_id"] == f"anthropic:{sample['model']}"


def test_selection_endpoint_leaks_no_secrets(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-never-appear")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-never-appear")
    text = client.get("/api/selection").text
    assert "sk-ant-should-never-appear" not in text
    assert "sk-should-never-appear" not in text
    assert "API_KEY" not in text
```

- [ ] **Step 8: Run endpoint tests + full backend suite + lint**

Run: `uv run pytest -q && uv run ruff check src tests`
Expected: PASS (full suite green), ruff clean.

- [ ] **Step 9: Commit**

```bash
git add src/orionfold/catalog/__init__.py src/orionfold/providers/selection.py src/orionfold/server/routes.py tests/unit/test_selection.py tests/integration/test_proof_api.py
git commit -m "feat(api): GET /api/selection — server-merged model picker panel

Provider groups with availability (from the live registry) + catalog models +
keyless mocks; candidate_id per model. Re-exports Tier/CostClass. No secrets
(asserted). Selection-only — never touches config_hash/receipt.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Frontend `CandidatePicker` (provider-grouped chips)

**Files:**
- Modify: `web/src/lib/api.ts` (add selection schemas + `getSelection`)
- Create: `web/src/features/proof/CandidatePicker.tsx`
- Modify: `web/src/features/proof/RunSetup.tsx` (swap the candidates fieldset for `<CandidatePicker>`)
- Modify: `web/src/features/proof/ProofCockpit.tsx` (query `getSelection`; default-select mocks)
- Test: `web/src/features/proof/CandidatePicker.test.tsx` (create)

**Interfaces:**
- Consumes: `GET /api/selection` → `SelectionPanel` (Task 2 shape).
- Produces:
  - `getSelection(): Promise<SelectionPanel>` and types `SelectionPanel`/`SelectionGroup`/`SelectionModel`.
  - `<CandidatePicker panel={SelectionPanel} selected={string[]} onToggle={(id: string) => void} />`.
  - `RunSetupProps` loses `candidates: Candidate[]`, gains `panel: SelectionPanel` (keeps `selectedCandidates`, `onToggleCandidate`).

- [ ] **Step 1: Add selection schemas + `getSelection` to `web/src/lib/api.ts`**

After the `candidateSchema` block (after line 14), add:

```typescript
export const selectionModelSchema = z.object({
  candidate_id: z.string(),
  model: z.string(),
  display_name: z.string(),
  tier: z.enum(["frontier", "balanced", "economy"]),
  cost_class: z.enum(["free", "$", "$$", "$$$"]),
  context_window: z.number().nullable().optional(),
  latest: z.boolean(),
  recommended: z.boolean(),
});
export type SelectionModel = z.infer<typeof selectionModelSchema>;

export const selectionGroupSchema = z.object({
  provider_id: z.string(),
  label: z.string(),
  privacy: Privacy,
  available: z.boolean(),
  supports_custom: z.boolean(),
  candidate_id: z.string().nullable().optional(),
  models: z.array(selectionModelSchema),
});
export type SelectionGroup = z.infer<typeof selectionGroupSchema>;

export const selectionPanelSchema = z.object({
  providers: z.array(selectionGroupSchema),
});
export type SelectionPanel = z.infer<typeof selectionPanelSchema>;
```

After `getCandidates` (after line 161), add:

```typescript
export function getSelection(): Promise<SelectionPanel> {
  return getJson("/api/selection", selectionPanelSchema);
}
```

- [ ] **Step 2: Write the failing component test**

Create `web/src/features/proof/CandidatePicker.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { CandidatePicker } from "./CandidatePicker";
import type { SelectionPanel } from "../../lib/api";

const PANEL: SelectionPanel = {
  providers: [
    {
      provider_id: "mock_good",
      label: "Mock · good",
      privacy: "local",
      available: true,
      supports_custom: false,
      candidate_id: "mock_good",
      models: [],
    },
    {
      provider_id: "anthropic",
      label: "Anthropic",
      privacy: "cloud",
      available: false,
      supports_custom: true,
      candidate_id: null,
      models: [
        { candidate_id: "anthropic:claude-haiku-4-5", model: "claude-haiku-4-5", display_name: "Claude Haiku 4.5", tier: "economy", cost_class: "$", context_window: 200000, latest: false, recommended: true },
      ],
    },
    {
      provider_id: "ollama",
      label: "Ollama",
      privacy: "local",
      available: true,
      supports_custom: true,
      candidate_id: null,
      models: [
        { candidate_id: "ollama:llama3.2", model: "llama3.2", display_name: "Llama 3.2", tier: "balanced", cost_class: "free", context_window: 8192, latest: true, recommended: true },
      ],
    },
  ],
};

test("renders a mock chip and provider model chips", () => {
  render(<CandidatePicker panel={PANEL} selected={["mock_good"]} onToggle={vi.fn()} />);
  expect(screen.getByRole("checkbox", { name: "Mock · good" })).toBeChecked();
  expect(screen.getByText("Claude Haiku 4.5")).toBeVisible();
  expect(screen.getByText("Llama 3.2")).toBeVisible();
});

test("toggling an available model chip emits its candidate_id", () => {
  const onToggle = vi.fn();
  render(<CandidatePicker panel={PANEL} selected={[]} onToggle={onToggle} />);
  fireEvent.click(screen.getByLabelText("Llama 3.2"));
  expect(onToggle).toHaveBeenCalledWith("ollama:llama3.2");
});

test("unavailable provider model chips are disabled", () => {
  render(<CandidatePicker panel={PANEL} selected={[]} onToggle={vi.fn()} />);
  expect(screen.getByLabelText("Claude Haiku 4.5")).toBeDisabled();
});

test("custom entry builds a provider:model candidate id", () => {
  const onToggle = vi.fn();
  render(<CandidatePicker panel={PANEL} selected={[]} onToggle={onToggle} />);
  fireEvent.click(screen.getByRole("button", { name: /custom model for Ollama/i }));
  fireEvent.change(screen.getByLabelText(/custom Ollama model/i), { target: { value: "phi3:mini" } });
  fireEvent.submit(screen.getByLabelText(/custom Ollama model/i).closest("form")!);
  expect(onToggle).toHaveBeenCalledWith("ollama:phi3:mini");
});
```

- [ ] **Step 3: Run to verify it fails**

Run: `pnpm --dir web test --run CandidatePicker`
Expected: FAIL — cannot resolve `./CandidatePicker`.

- [ ] **Step 4: Create `web/src/features/proof/CandidatePicker.tsx`**

```tsx
import { useState } from "react";

import type { SelectionGroup, SelectionModel, SelectionPanel } from "../../lib/api";

export interface CandidatePickerProps {
  panel: SelectionPanel;
  selected: string[];
  onToggle: (candidateId: string) => void;
}

// Provider-grouped chips: each curated model is a toggle; toggle several on one provider to
// compare them (the cost/latency-vs-quality proof). Unavailable providers are greyed; a
// "+ custom" field is the escape hatch for any model string the catalog doesn't list.
export function CandidatePicker({ panel, selected, onToggle }: CandidatePickerProps) {
  return (
    <fieldset className="grid gap-3 text-sm">
      <legend className="text-(--color-ink-muted)">Candidates</legend>
      <p className="text-xs text-(--color-ink-faint)">
        The models you’re comparing. Toggle several models of one provider to weigh cost and
        latency against quality. Mock candidates run instantly, no API key.
      </p>
      <div className="grid gap-3">
        {panel.providers.map((g) => (
          <ProviderRow key={g.provider_id} group={g} selected={selected} onToggle={onToggle} />
        ))}
      </div>
    </fieldset>
  );
}

function ProviderRow({
  group,
  selected,
  onToggle,
}: {
  group: SelectionGroup;
  selected: string[];
  onToggle: (id: string) => void;
}) {
  // Custom-model chips the user added that aren't in the catalog list, so they still render.
  const customSelected = selected.filter(
    (id) => id.startsWith(`${group.provider_id}:`) && !group.models.some((m) => m.candidate_id === id),
  );
  return (
    <div className="grid gap-2 sm:grid-cols-[8rem_minmax(0,1fr)] sm:items-start">
      <div className="flex items-center gap-1.5 pt-1.5 text-(--color-ink-muted)">
        <span
          aria-hidden
          className={
            "h-2 w-2 rounded-full " +
            (group.available ? "bg-(--color-accent)" : "bg-(--color-panel-line-strong)")
          }
        />
        {/* Mocks carry their full label on the chip, so the left column stays generic to avoid
            repeating the same text twice in one row. */}
        <span>{group.candidate_id != null ? "Mock" : group.label}</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {group.candidate_id !== null && group.candidate_id !== undefined ? (
          <Chip
            label={group.label}
            value={group.candidate_id}
            checked={selected.includes(group.candidate_id)}
            disabled={!group.available}
            onToggle={onToggle}
          />
        ) : null}
        {group.models.map((m) => (
          <ModelChip
            key={m.candidate_id}
            model={m}
            checked={selected.includes(m.candidate_id)}
            disabled={!group.available}
            onToggle={onToggle}
          />
        ))}
        {customSelected.map((id) => (
          <Chip
            key={id}
            label={id.slice(group.provider_id.length + 1)}
            value={id}
            checked
            disabled={!group.available}
            onToggle={onToggle}
          />
        ))}
        {group.supports_custom && group.available ? (
          <CustomChip providerId={group.provider_id} providerLabel={group.label} onToggle={onToggle} />
        ) : null}
        {!group.available ? (
          <span className="self-center text-xs text-(--color-ink-faint)">
            Unavailable — add a key (coming with recipes)
          </span>
        ) : null}
      </div>
    </div>
  );
}

const chipBase =
  "flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 transition-colors disabled:cursor-not-allowed disabled:opacity-40";

function Chip({
  label,
  value,
  checked,
  disabled,
  onToggle,
}: {
  label: string;
  value: string;
  checked: boolean;
  disabled?: boolean;
  onToggle: (id: string) => void;
}) {
  return (
    <label
      className={
        chipBase +
        " " +
        (checked
          ? "border-(--color-accent)/50 bg-(--color-accent)/10"
          : "border-(--color-panel-line) hover:border-(--color-panel-line-strong)")
      }
    >
      <input
        type="checkbox"
        aria-label={label}
        checked={checked}
        disabled={disabled}
        onChange={() => onToggle(value)}
        className="accent-(--color-accent-strong)"
      />
      <span className="text-(--color-ink)">{label}</span>
    </label>
  );
}

function ModelChip({
  model,
  checked,
  disabled,
  onToggle,
}: {
  model: SelectionModel;
  checked: boolean;
  disabled?: boolean;
  onToggle: (id: string) => void;
}) {
  return (
    <label
      className={
        chipBase +
        " " +
        (checked
          ? "border-(--color-accent)/50 bg-(--color-accent)/10"
          : "border-(--color-panel-line) hover:border-(--color-panel-line-strong)")
      }
    >
      <input
        type="checkbox"
        aria-label={model.display_name}
        checked={checked}
        disabled={disabled}
        onChange={() => onToggle(model.candidate_id)}
        className="accent-(--color-accent-strong)"
      />
      <span className="text-(--color-ink)">{model.display_name}</span>
      {model.latest ? <span title="latest" className="text-(--color-accent)">★</span> : null}
      <span className="text-xs text-(--color-ink-faint)">{model.cost_class}</span>
    </label>
  );
}

function CustomChip({
  providerId,
  providerLabel,
  onToggle,
}: {
  providerId: string;
  providerLabel: string;
  onToggle: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  if (!open) {
    return (
      <button
        type="button"
        aria-label={`custom model for ${providerLabel}`}
        onClick={() => setOpen(true)}
        className="rounded-lg border border-dashed border-(--color-panel-line) px-3 py-2 text-(--color-ink-muted) hover:border-(--color-panel-line-strong)"
      >
        + custom
      </button>
    );
  }
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const value = text.trim();
        if (value) onToggle(`${providerId}:${value}`);
        setText("");
        setOpen(false);
      }}
      className="flex items-center gap-1"
    >
      <input
        autoFocus
        aria-label={`custom ${providerLabel} model`}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="model id"
        className="w-40 rounded-lg border border-(--color-panel-line) bg-(--color-panel) px-2 py-1.5 text-(--color-ink)"
      />
      <button type="submit" className="rounded-lg bg-(--color-accent-strong) px-2 py-1.5 text-(--color-accent-ink)">
        Add
      </button>
    </form>
  );
}
```

- [ ] **Step 5: Run the component test to verify it passes**

Run: `pnpm --dir web test --run CandidatePicker`
Expected: PASS (4 passed).

- [ ] **Step 6: Swap the candidates fieldset in `RunSetup.tsx`**

Replace the imports at the top (lines 1-2) with:

```tsx
import type { Dataset, ProofBrief, SelectionPanel } from "../../lib/api";
import { CandidatePicker } from "./CandidatePicker";
```

In `RunSetupProps`, replace `candidates: Candidate[];` with `panel: SelectionPanel;`.

In the destructure inside `RunSetup`, replace `candidates,` with `panel,`.

Replace the entire `<fieldset>` candidates block (lines 72-102) with:

```tsx
        <CandidatePicker
          panel={panel}
          selected={selectedCandidates}
          onToggle={onToggleCandidate}
        />
```

- [ ] **Step 7: Wire `ProofCockpit.tsx` to `getSelection` + default-select mocks**

In the import block (lines 5-15), replace `getCandidates,` with `getSelection,`.

Replace the candidates query (line 43):

```tsx
  const selection = useQuery({ queryKey: ["selection"], queryFn: getSelection });
```

Replace `resolvedSelected` (lines 77-82) with:

```tsx
  const resolvedSelected = useMemo(() => {
    if (selected.length > 0) return selected;
    // Mocks are the keyless default path: groups that ARE a candidate (candidate_id set).
    const groups = selection.data?.providers ?? [];
    return groups
      .filter((g) => g.candidate_id)
      .map((g) => g.candidate_id as string);
  }, [selected, selection.data]);
```

Replace the two loading/error guards (lines 104-120) to use `selection` instead of `candidates`:

```tsx
  if (datasets.isLoading || selection.isLoading) {
```

```tsx
  if (datasets.isError || selection.isError || !datasets.data || !selection.data) {
```

Replace the `candidates={candidates.data}` prop on `<RunSetup>` (line 138) with:

```tsx
          panel={selection.data}
```

- [ ] **Step 8: Run frontend units + typecheck/build**

Run: `pnpm --dir web test --run && pnpm --dir web build`
Expected: PASS — all Vitest green; `tsc` + Vite build succeed (no unused `Candidate`/`ProviderTag` import errors in RunSetup — confirm they were removed).

- [ ] **Step 9: Commit**

```bash
git add web/src/lib/api.ts web/src/features/proof/CandidatePicker.tsx web/src/features/proof/CandidatePicker.test.tsx web/src/features/proof/RunSetup.tsx web/src/features/proof/ProofCockpit.tsx
git commit -m "feat(cockpit): model-per-candidate picker (provider-grouped chips)

CandidatePicker renders GET /api/selection: per-provider model chips (★ latest,
cost class), multi-select within a provider, + custom-model escape hatch;
unavailable providers greyed. Mocks pre-selected by default (keyless path).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: e2e coverage + full verification gate

**Files:**
- Modify: `e2e/playwright/proof.spec.ts` (assert the picker shows a real model chip; mock run still works)
- Verify: full suite, lint, build, embed rebuild, real-browser check

**Interfaces:**
- Consumes: the running embedded app (mocks default-selected; a catalog model chip visible).

- [ ] **Step 1: Add a picker assertion to the existing happy-path e2e**

In `e2e/playwright/proof.spec.ts`, after the "Engine reachable" assertions and before clicking Run, add:

```typescript
  // The model picker renders catalog models per provider (the #4 capability). A local model
  // chip is selectable; cloud providers without a key are greyed. Mocks stay default-selected.
  await expect(page.getByText("Candidates")).toBeVisible();
  await expect(page.getByRole("checkbox", { name: "Mock · good" })).toBeChecked();
  await expect(page.getByRole("button", { name: /custom model for Ollama/i })).toBeVisible();
```

(The run still fires with the two mocks pre-selected, so the rest of the spec — leaderboard "100% (5/5)", "Failure cases (5)", three receipt downloads — is unchanged.)

- [ ] **Step 2: Rebuild the embedded cockpit (e2e runs against the embed)**

Run: `bash scripts/build.sh`
Expected: builds `web/dist`, copies into `src/orionfold/server/static`, produces the wheel. No errors.

- [ ] **Step 3: Run the Playwright e2e**

Run: `pnpm --dir web e2e`
Expected: PASS — `proof.spec.ts`, `dataset-import.spec.ts`, `theme.spec.ts` all green.

- [ ] **Step 4: Full verification sweep**

Run: `uv run pytest -q && uv run ruff check src tests && pnpm --dir web test --run && pnpm --dir web build`
Expected: all green; ruff clean.

- [ ] **Step 5: Real-browser sanity check on a provably-free port**

Pick a free port (assert the listener PID is yours, per HANDOFF). Start `orionfold up --port <free>`, open the cockpit, confirm the Candidates picker shows provider-grouped chips with a model chip and a "+ custom" affordance, run a mock proof, see the leaderboard. Screenshot via the `browser-visual-verification` skill; list any visual diffs and fix scoped ones.

- [ ] **Step 6: Commit**

```bash
git add e2e/playwright/proof.spec.ts
git commit -m "test(e2e): assert model picker renders per-provider model chips

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- Composite `provider:model` ids, first-colon split, mocks bare → Task 1 (`build_candidates`). ✓
- Widen validation, keyless-safe, backward compatible, both endpoints → Task 1. ✓
- `config_hash`/`RECEIPT_VERSION` untouched → no task edits them; mock byte-identity asserted (Task 1 Step 1). ✓
- `GET /api/selection` server-merge, mocks-first, availability, no-secrets, Tier/CostClass re-export → Task 2. ✓
- Provider-grouped chips, ★/cost-class marks, multi-select per provider, custom escape hatch, greyed unavailable, keyboard-accessible (checkbox `aria-label`) → Task 3. ✓
- Default keyless mock pre-selection preserved → Task 3 Step 7. ✓
- e2e + full verification + embed rebuild → Task 4. ✓
- Inline key entry deferred → not in any task (correct; #5). ✓

**Placeholder scan:** none — every code/test step shows full content.

**Type consistency:** `SelectionModel`/`SelectionGroup`/`SelectionPanel` field names match across Python (Task 2) and Zod (Task 3). `build_candidates`/`UnknownCandidateError`/`selection_panel` names consistent across tasks and routes. `candidate_id` format `provider:model` consistent (backend builds it; frontend custom path builds it identically). `panel` prop replaces `candidates` consistently in RunSetup (Task 3 Steps 6) and ProofCockpit (Step 7).
