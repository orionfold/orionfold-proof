# Settings: Sample Data, Sandbox, Mocks-out-of-happy-path — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove mock providers from the default Candidates picker; add a Settings area to seed/remove sample data, clear all data, and toggle a Sandbox that re-exposes the mocks as one "Mock" provider.

**Architecture:** Server-persisted settings (KV `settings` table) gate the Mock provider in `selection_panel`. Sample artifacts are flagged with an `is_sample` column on `datasets`/`runs` (append-only migrations) and generated at seed time by running the mocks through `run_proof`. A new `SettingsView` drives it all via five `/api` endpoints.

**Tech Stack:** Python 3.12 · FastAPI · Pydantic · SQLite (stdlib `sqlite3`) · pytest · ruff · React + TypeScript · Vite · TanStack Query · Zod · Vitest · Playwright.

## Global Constraints

- **Invariant — bare-id mocks:** the ids sent to the engine stay `mock_good` / `mock_bad`. Only the picker *presentation* groups them under one `mock` provider. Never mint `mock:good`-style composite ids.
- **Invariant — engine labels unchanged:** candidate labels stay `Mock · good` / `Mock · bad`. "Good model" / "Bad model" are picker `display_name`s only.
- **Invariant — byte-identity:** the model-compare sample reproduces `config_hash 467ddd96c9a5`; `RECEIPT_VERSION` stays `6`. Do not modify the domain `Dataset`/`Candidate`/`ProofReport` models or `config_hash`.
- **Migrations are append-only** (`.claude/rules/storage.md`): only append to `MIGRATIONS`; never edit indices 0–1.
- **Secrets:** these endpoints touch only `datasets`/`runs`/`settings` — no keys, no logging of secrets.
- **Sandbox default:** OFF (`sandbox_enabled` absent → `false`).
- **Sample ids (stable):** dataset `sample-investment-memo`; run `run_sample01`; `created_at` `2026-06-19T12:00:00Z`. Run ids are otherwise hex (`run_<uuid hex>`), so `run_sample…` can never collide with a real run id.
- **Design system:** secondary buttons neutral; destructive = `--color-danger`; cyan only for interactive accents; status never cyan. Light + dark + AA.
- After any web change that must ship: rebuild the embed with `bash scripts/build.sh` (or `pnpm --dir web build && rm -rf src/orionfold/server/static && cp -r web/dist src/orionfold/server/static`) before `pnpm --dir web e2e`.

---

## File structure

**Backend**
- Modify `src/orionfold/storage/db.py` — append migrations 2–4.
- Create `src/orionfold/storage/settings.py` — KV settings repo.
- Modify `src/orionfold/storage/repository.py` — `is_sample` on `save_report`; `insert_sample_dataset`, `list_dataset_rows`, `remove_sample_data`, `clear_all_data`.
- Create `src/orionfold/sample_data.py` — seed orchestration (runs mocks via `run_proof`).
- Modify `src/orionfold/providers/selection.py` — `selection_panel(sandbox: bool)` + Mock provider group.
- Modify `src/orionfold/server/routes.py` — 5 endpoints + `DatasetRow` on `/datasets` + sandbox-aware `/selection`.

**Frontend**
- Modify `web/src/lib/api.ts` — `is_sample` on dataset schema; settings + sample-data client fns.
- Create `web/src/features/proof/SettingsView.tsx` — Data Management card + sandbox toggle + inline confirm.
- Modify `web/src/app/App.tsx` — "Settings" nav + route.
- Modify `web/src/features/proof/ProofCockpit.tsx` — default-selection from the mock group; first-run copy.
- Modify `web/src/features/proof/ProviderLogo.tsx` — `mock → FlaskConical`.
- Modify `web/src/features/proof/DatasetsView.tsx` + `ReceiptsView.tsx` — "Sample" badge.

**Tests**
- Create `tests/unit/test_settings_and_samples.py`; extend `tests/unit/test_selection.py` (create if absent) and `tests/integration/test_proof_api.py`.
- Create `web/src/features/proof/SettingsView.test.tsx`; extend `ProviderLogo.test.tsx`, `lib/api.test.ts`.
- Modify `e2e/playwright/proof.spec.ts`; create `e2e/playwright/settings.spec.ts`.

---

## Task 1: Migrations + settings KV repo

**Files:**
- Modify: `src/orionfold/storage/db.py` (append to `MIGRATIONS`)
- Create: `src/orionfold/storage/settings.py`
- Test: `tests/unit/test_settings_and_samples.py`

**Interfaces — Produces:**
- `get_setting(conn, key: str, default: str | None = None) -> str | None`
- `set_setting(conn, key: str, value: str) -> None`
- `get_sandbox_enabled(conn) -> bool`
- `set_sandbox_enabled(conn, enabled: bool) -> None`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_settings_and_samples.py
import sqlite3
from orionfold.storage.db import apply_migrations
from orionfold.storage import settings


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    apply_migrations(conn)
    return conn


def test_sandbox_defaults_false_and_round_trips():
    conn = _db()
    assert settings.get_sandbox_enabled(conn) is False
    settings.set_sandbox_enabled(conn, True)
    assert settings.get_sandbox_enabled(conn) is True
    settings.set_sandbox_enabled(conn, False)
    assert settings.get_sandbox_enabled(conn) is False


def test_setting_get_default_and_set():
    conn = _db()
    assert settings.get_setting(conn, "missing", "fallback") == "fallback"
    settings.set_setting(conn, "k", "v")
    assert settings.get_setting(conn, "k") == "v"


def test_migrations_are_idempotent_and_add_is_sample():
    conn = _db()
    assert apply_migrations(conn) == 0  # re-apply adds nothing
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(datasets)")}
    assert "is_sample" in cols
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(runs)")}
    assert "is_sample" in cols
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_settings_and_samples.py -q`
Expected: FAIL — `ModuleNotFoundError: orionfold.storage.settings` (and `is_sample` columns absent).

- [ ] **Step 3: Append migrations**

In `src/orionfold/storage/db.py`, append three entries to the `MIGRATIONS` list (after index 1):

```python
    """
    ALTER TABLE datasets ADD COLUMN is_sample INTEGER NOT NULL DEFAULT 0;
    """,
    """
    ALTER TABLE runs ADD COLUMN is_sample INTEGER NOT NULL DEFAULT 0;
    """,
    """
    CREATE TABLE settings (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """,
```

- [ ] **Step 4: Create the settings repo**

```python
# src/orionfold/storage/settings.py
"""Tiny key-value settings store (one row per setting). Local, per-install.

Booleans are stored as the strings "true"/"false". The only key today is
``sandbox_enabled`` (default off) — it gates the simulated Mock provider in the picker.
"""

from __future__ import annotations

import sqlite3

_SANDBOX_KEY = "sandbox_enabled"


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row is not None else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()


def get_sandbox_enabled(conn: sqlite3.Connection) -> bool:
    return get_setting(conn, _SANDBOX_KEY, "false") == "true"


def set_sandbox_enabled(conn: sqlite3.Connection, enabled: bool) -> None:
    set_setting(conn, _SANDBOX_KEY, "true" if enabled else "false")
```

- [ ] **Step 5: Run tests + ruff**

Run: `uv run pytest tests/unit/test_settings_and_samples.py -q && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 6: Commit**

```bash
git add src/orionfold/storage/db.py src/orionfold/storage/settings.py tests/unit/test_settings_and_samples.py
git commit -m "feat(storage): is_sample migrations + settings KV repo"
```

---

## Task 2: Sample-data repository ops + seed orchestration

**Files:**
- Modify: `src/orionfold/storage/repository.py`
- Create: `src/orionfold/sample_data.py`
- Test: `tests/unit/test_settings_and_samples.py` (extend)

**Interfaces:**
- Consumes: `apply_migrations`, `run_proof`, `load_dataset`, `default_rubric_for`.
- Produces:
  - `repository.save_report(conn, report, *, is_sample: bool = False) -> None` (extended signature; default keeps existing callers)
  - `repository.insert_sample_dataset(conn, dataset: Dataset) -> None`
  - `repository.list_dataset_rows(conn) -> list[tuple[Dataset, bool]]`
  - `repository.remove_sample_data(conn) -> tuple[int, int]` → `(datasets_deleted, runs_deleted)`
  - `repository.clear_all_data(conn) -> tuple[int, int]` → `(datasets_deleted, runs_deleted)`
  - `sample_data.seed_sample_data(conn) -> tuple[int, int]` → `(datasets, receipts)`
  - `sample_data.SAMPLE_DATASET_ID = "sample-investment-memo"`, `SAMPLE_RUN_ID = "run_sample01"`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_settings_and_samples.py  (append)
from orionfold.storage import repository
from orionfold import sample_data


def test_seed_creates_flagged_sample_dataset_and_receipt():
    conn = _db()
    repository.seed_datasets(conn)  # bundled (real) datasets exist
    datasets, receipts = sample_data.seed_sample_data(conn)
    assert (datasets, receipts) == (1, 1)
    rows = repository.list_dataset_rows(conn)
    samples = [d for d, is_sample in rows if is_sample]
    assert [d.id for d in samples] == [sample_data.SAMPLE_DATASET_ID]
    run = conn.execute("SELECT id, is_sample FROM runs").fetchone()
    assert run["id"] == sample_data.SAMPLE_RUN_ID and run["is_sample"] == 1


def test_seed_is_idempotent():
    conn = _db()
    repository.seed_datasets(conn)
    sample_data.seed_sample_data(conn)
    sample_data.seed_sample_data(conn)  # re-seed
    assert conn.execute("SELECT COUNT(*) c FROM runs WHERE is_sample=1").fetchone()["c"] == 1
    assert conn.execute("SELECT COUNT(*) c FROM datasets WHERE is_sample=1").fetchone()["c"] == 1


def test_remove_samples_keeps_real_data():
    conn = _db()
    repository.seed_datasets(conn)
    real_before = conn.execute("SELECT COUNT(*) c FROM datasets WHERE is_sample=0").fetchone()["c"]
    sample_data.seed_sample_data(conn)
    ds, runs = repository.remove_sample_data(conn)
    assert ds == 1 and runs == 1
    assert conn.execute("SELECT COUNT(*) c FROM datasets WHERE is_sample=0").fetchone()["c"] == real_before
    assert conn.execute("SELECT COUNT(*) c FROM runs").fetchone()["c"] == 0


def test_clear_all_wipes_datasets_and_runs_but_not_settings():
    conn = _db()
    repository.seed_datasets(conn)
    sample_data.seed_sample_data(conn)
    settings.set_sandbox_enabled(conn, True)
    ds, runs = repository.clear_all_data(conn)
    assert ds >= 1 and runs == 1
    assert conn.execute("SELECT COUNT(*) c FROM datasets").fetchone()["c"] == 0
    assert conn.execute("SELECT COUNT(*) c FROM runs").fetchone()["c"] == 0
    assert settings.get_sandbox_enabled(conn) is True  # settings preserved
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_settings_and_samples.py -q`
Expected: FAIL — `AttributeError`/`ModuleNotFoundError` for the new functions and `orionfold.sample_data`.

- [ ] **Step 3: Extend the repository**

In `src/orionfold/storage/repository.py`:

Change `save_report` to carry the flag:
```python
def save_report(conn: sqlite3.Connection, report: ProofReport, *, is_sample: bool = False) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO runs (id, created_at, config_hash, report, is_sample) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            report.run.id,
            report.run.created_at,
            report.run.config_hash,
            report.model_dump_json(),
            1 if is_sample else 0,
        ),
    )
    conn.commit()
```

Add these functions:
```python
def insert_sample_dataset(conn: sqlite3.Connection, dataset: Dataset) -> None:
    """Upsert a sample dataset (is_sample=1). Stable id makes re-seeding idempotent."""
    conn.execute(
        "INSERT OR REPLACE INTO datasets (id, name, description, examples, is_sample) "
        "VALUES (?, ?, ?, ?, 1)",
        (dataset.id, dataset.name, dataset.description, _examples_json(dataset)),
    )
    conn.commit()


def list_dataset_rows(conn: sqlite3.Connection) -> list[tuple[Dataset, bool]]:
    """Datasets plus their is_sample flag — for the API; the domain model stays flag-free."""
    rows = conn.execute(
        "SELECT id, name, description, examples, is_sample FROM datasets ORDER BY name"
    ).fetchall()
    out: list[tuple[Dataset, bool]] = []
    for r in rows:
        dataset = Dataset.model_validate(
            {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "examples": _load_examples(r["examples"]),
            }
        )
        out.append((dataset, bool(r["is_sample"])))
    return out


def remove_sample_data(conn: sqlite3.Connection) -> tuple[int, int]:
    """Delete only sample rows. Returns (datasets_deleted, runs_deleted)."""
    runs = conn.execute("DELETE FROM runs WHERE is_sample = 1").rowcount
    datasets = conn.execute("DELETE FROM datasets WHERE is_sample = 1").rowcount
    conn.commit()
    return datasets, runs


def clear_all_data(conn: sqlite3.Connection) -> tuple[int, int]:
    """Delete ALL datasets and runs (settings are untouched). Returns (datasets, runs)."""
    runs = conn.execute("DELETE FROM runs").rowcount
    datasets = conn.execute("DELETE FROM datasets").rowcount
    conn.commit()
    return datasets, runs
```

- [ ] **Step 4: Create the seed orchestrator**

```python
# src/orionfold/sample_data.py
"""Seed realistic sample data so a new install isn't empty: one sample dataset plus a
finished Proof Receipt over it, generated by the keyless mocks (deterministic, no network).
Idempotent — re-seeding clears prior samples first."""

from __future__ import annotations

import sqlite3

from orionfold.data import load_dataset
from orionfold.domain.models import Candidate, Dataset, ProofBrief
from orionfold.proof.engine import run_proof
from orionfold.scoring.rubric import default_rubric_for
from orionfold.storage import repository

SAMPLE_DATASET_ID = "sample-investment-memo"
SAMPLE_RUN_ID = "run_sample01"
SAMPLE_CREATED_AT = "2026-06-19T12:00:00Z"
SAMPLE_BRIEF = ProofBrief(
    task_name="Sample · investment memo summarization",
    decision_question="Which model should I trust for client memos?",
    success_criteria="At least 80% similarity to the analyst summary.",
)


def _sample_dataset() -> Dataset:
    base = load_dataset("investment-memo-summarization")
    return base.model_copy(
        update={"id": SAMPLE_DATASET_ID, "name": "Sample · investment memo summarization"}
    )


def seed_sample_data(conn: sqlite3.Connection) -> tuple[int, int]:
    """(Re)create the sample dataset + receipt. Returns (datasets, receipts) created."""
    repository.remove_sample_data(conn)  # idempotent: clear prior samples first
    dataset = _sample_dataset()
    repository.insert_sample_dataset(conn, dataset)
    report = run_proof(
        run_id=SAMPLE_RUN_ID,
        created_at=SAMPLE_CREATED_AT,
        brief=SAMPLE_BRIEF,
        dataset=dataset,
        candidates=[
            Candidate(id="mock_good", label="Mock · good", provider_id="mock_good"),
            Candidate(id="mock_bad", label="Mock · bad", provider_id="mock_bad"),
        ],
        rubric=default_rubric_for(dataset),
    )
    repository.save_report(conn, report, is_sample=True)
    return (1, 1)
```

- [ ] **Step 5: Run tests + ruff**

Run: `uv run pytest tests/unit/test_settings_and_samples.py -q && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 6: Commit**

```bash
git add src/orionfold/storage/repository.py src/orionfold/sample_data.py tests/unit/test_settings_and_samples.py
git commit -m "feat(storage): sample-data seed/remove/clear + is_sample on save_report"
```

---

## Task 3: `selection_panel(sandbox)` reshape + invariant guard

**Files:**
- Modify: `src/orionfold/providers/selection.py`
- Test: `tests/unit/test_selection.py` (create if absent)

**Interfaces:**
- Consumes: `available_candidates()`, `build_candidates()`.
- Produces: `selection_panel(sandbox: bool = False) -> SelectionPanel`. When `sandbox`, the panel's first group is `provider_id="mock"`, `candidate_id=None`, `models=[Good model (mock_good), Bad model (mock_bad)]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_selection.py
from orionfold.providers.selection import selection_panel
from orionfold.providers.registry import build_candidates


def test_sandbox_off_has_no_mock_group():
    panel = selection_panel(sandbox=False)
    assert all(g.provider_id != "mock" for g in panel.providers)


def test_sandbox_on_shows_one_mock_group_with_two_models():
    panel = selection_panel(sandbox=True)
    mock = [g for g in panel.providers if g.provider_id == "mock"]
    assert len(mock) == 1
    g = mock[0]
    assert g.label == "Mock" and g.candidate_id is None and g.supports_custom is False
    by_id = {m.candidate_id: m.display_name for m in g.models}
    assert by_id == {"mock_good": "Good model", "mock_bad": "Bad model"}


def test_mock_ids_stay_bare_and_resolvable():
    # Invariant: the engine still resolves the bare ids the picker now nests under "mock".
    cands = build_candidates(["mock_good", "mock_bad"])
    assert [c.id for c in cands] == ["mock_good", "mock_bad"]
    assert [c.label for c in cands] == ["Mock · good", "Mock · bad"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_selection.py -q`
Expected: FAIL — `selection_panel()` takes no `sandbox` arg / mock groups still appear when off.

- [ ] **Step 3: Implement the reshape**

In `src/orionfold/providers/selection.py`, add near the top (after imports):
```python
_MOCK_DISPLAY = {"mock_good": "Good model", "mock_bad": "Bad model"}
```

Replace the function signature and the "Mocks first" loop:
```python
def selection_panel(sandbox: bool = False) -> SelectionPanel:
    """Build the picker panel. The simulated Mock provider only appears when sandbox is on."""
    registry = _build()
    available_ids = set(registry)
    catalog = load_catalog()
    catalog_ids = {p.id for p in catalog.providers}
    groups: list[SelectionGroup] = []

    # Sandbox only: one "Mock" provider exposing the two keyless mocks as Good/Bad models.
    # The candidate ids stay bare (mock_good / mock_bad) so the engine routing is unchanged.
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
    # Catalog providers — unchanged from here down.
```
(Keep the existing catalog-providers loop and `return SelectionPanel(...)` exactly as-is.)

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/test_selection.py tests/unit/test_settings_and_samples.py -q`
Expected: PASS.

- [ ] **Step 5: Guard the byte-identity invariant**

Run the full backend suite — the existing model-compare/config_hash tests must still pass:
Run: `uv run pytest -q`
Expected: PASS (including the existing `config_hash 467ddd96c9a5` assertion).

- [ ] **Step 6: Commit**

```bash
git add src/orionfold/providers/selection.py tests/unit/test_selection.py
git commit -m "feat(selection): gate mocks behind sandbox as one Mock provider (Good/Bad models)"
```

---

## Task 4: API endpoints (settings, sample-data, sandbox-aware selection, dataset rows)

**Files:**
- Modify: `src/orionfold/server/routes.py`
- Test: `tests/integration/test_proof_api.py` (extend, mirroring its existing TestClient fixture)

**Interfaces — Produces (HTTP):** `GET/PUT /api/settings`, `POST /api/sample-data/seed`, `DELETE /api/sample-data`, `DELETE /api/data`; `GET /api/datasets` now returns rows with `is_sample`; `GET /api/selection` is sandbox-aware.

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_proof_api.py  (append; reuse the module's existing `client` fixture
# that builds the app with a temp ORIONFOLD_DB. If the fixture name differs, match it.)

def test_settings_default_and_update(client):
    assert client.get("/api/settings").json() == {"sandbox_enabled": False}
    assert client.put("/api/settings", json={"sandbox_enabled": True}).json() == {
        "sandbox_enabled": True
    }
    assert client.get("/api/settings").json() == {"sandbox_enabled": True}


def test_selection_is_sandbox_aware(client):
    assert all(g["provider_id"] != "mock" for g in client.get("/api/selection").json()["providers"])
    client.put("/api/settings", json={"sandbox_enabled": True})
    mock = [g for g in client.get("/api/selection").json()["providers"] if g["provider_id"] == "mock"]
    assert len(mock) == 1 and len(mock[0]["models"]) == 2


def test_seed_then_remove_sample_data(client):
    assert client.post("/api/sample-data/seed").json() == {"datasets": 1, "receipts": 1}
    ds = client.get("/api/datasets").json()
    assert any(d["is_sample"] for d in ds)
    assert len(client.get("/api/runs").json()) == 1
    assert client.request("DELETE", "/api/sample-data").json() == {"datasets": 1, "receipts": 1}
    assert not any(d["is_sample"] for d in client.get("/api/datasets").json())
    assert client.get("/api/runs").json() == []


def test_clear_all_data(client):
    client.post("/api/sample-data/seed")
    out = client.request("DELETE", "/api/data").json()
    assert out["receipts"] == 1 and out["datasets"] >= 1
    assert client.get("/api/datasets").json() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_proof_api.py -q`
Expected: FAIL — 404/405 for new routes; `/api/datasets` has no `is_sample`.

- [ ] **Step 3: Implement the routes**

In `src/orionfold/server/routes.py`, add imports:
```python
from orionfold.domain.models import Example  # if not already imported
from orionfold.sample_data import seed_sample_data
from orionfold.storage.settings import get_sandbox_enabled, set_sandbox_enabled
from orionfold.storage.repository import (
    clear_all_data,
    list_dataset_rows,
    remove_sample_data,
)
```

Add response models (near the other `BaseModel`s):
```python
class SettingsModel(BaseModel):
    sandbox_enabled: bool


class DataCounts(BaseModel):
    datasets: int
    receipts: int


class DatasetRow(BaseModel):
    id: str
    name: str
    description: str
    examples: list[Example]
    is_sample: bool
```

Replace `get_datasets` and `get_selection`:
```python
@router.get("/datasets")
def get_datasets(request: Request) -> list[DatasetRow]:
    conn = _conn(request)
    try:
        return [
            DatasetRow(
                id=d.id, name=d.name, description=d.description,
                examples=d.examples, is_sample=is_sample,
            )
            for d, is_sample in list_dataset_rows(conn)
        ]
    finally:
        conn.close()


@router.get("/selection")
def get_selection(request: Request) -> SelectionPanel:
    conn = _conn(request)
    try:
        return selection_panel(sandbox=get_sandbox_enabled(conn))
    finally:
        conn.close()
```

Add the new endpoints (anywhere after `_conn`):
```python
@router.get("/settings")
def read_settings(request: Request) -> SettingsModel:
    conn = _conn(request)
    try:
        return SettingsModel(sandbox_enabled=get_sandbox_enabled(conn))
    finally:
        conn.close()


@router.put("/settings")
def update_settings(request: Request, body: SettingsModel) -> SettingsModel:
    conn = _conn(request)
    try:
        set_sandbox_enabled(conn, body.sandbox_enabled)
        return SettingsModel(sandbox_enabled=get_sandbox_enabled(conn))
    finally:
        conn.close()


@router.post("/sample-data/seed")
def seed_samples(request: Request) -> DataCounts:
    conn = _conn(request)
    try:
        datasets, receipts = seed_sample_data(conn)
        return DataCounts(datasets=datasets, receipts=receipts)
    finally:
        conn.close()


@router.delete("/sample-data")
def delete_samples(request: Request) -> DataCounts:
    conn = _conn(request)
    try:
        datasets, receipts = remove_sample_data(conn)
        return DataCounts(datasets=datasets, receipts=receipts)
    finally:
        conn.close()


@router.delete("/data")
def clear_data(request: Request) -> DataCounts:
    conn = _conn(request)
    try:
        datasets, receipts = clear_all_data(conn)
        return DataCounts(datasets=datasets, receipts=receipts)
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests + ruff + full suite**

Run: `uv run pytest tests/integration/test_proof_api.py -q && uv run pytest -q && uv run ruff check src tests`
Expected: PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/server/routes.py tests/integration/test_proof_api.py
git commit -m "feat(api): settings + sample-data endpoints; is_sample on /datasets; sandbox-aware /selection"
```

---

## Task 5: Frontend API client

**Files:**
- Modify: `web/src/lib/api.ts`
- Test: `web/src/lib/api.test.ts` (extend)

**Interfaces — Produces:**
- `datasetSchema` gains `is_sample: boolean` (default false).
- `getSettings(): Promise<{ sandbox_enabled: boolean }>`
- `setSandbox(enabled: boolean): Promise<{ sandbox_enabled: boolean }>`
- `seedSampleData(): Promise<{ datasets: number; receipts: number }>`
- `removeSampleData(): Promise<{ datasets: number; receipts: number }>`
- `clearAllData(): Promise<{ datasets: number; receipts: number }>`

- [ ] **Step 1: Write the failing test**

```typescript
// web/src/lib/api.test.ts  (append)
import { describe, expect, it, vi } from "vitest";
import { getSettings, setSandbox, seedSampleData } from "./api";

function mockFetchOnce(body: unknown) {
  vi.spyOn(global, "fetch").mockResolvedValueOnce(
    new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } }),
  );
}

describe("settings + sample-data client", () => {
  it("getSettings parses sandbox_enabled", async () => {
    mockFetchOnce({ sandbox_enabled: true });
    expect(await getSettings()).toEqual({ sandbox_enabled: true });
  });

  it("setSandbox PUTs the flag", async () => {
    const spy = vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ sandbox_enabled: false }), { status: 200 }),
    );
    await setSandbox(false);
    expect(spy).toHaveBeenCalledWith("/api/settings", expect.objectContaining({ method: "PUT" }));
  });

  it("seedSampleData parses counts", async () => {
    mockFetchOnce({ datasets: 1, receipts: 1 });
    expect(await seedSampleData()).toEqual({ datasets: 1, receipts: 1 });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test src/lib/api.test.ts`
Expected: FAIL — `getSettings`/`setSandbox`/`seedSampleData` not exported.

- [ ] **Step 3: Implement the client additions**

In `web/src/lib/api.ts`, extend `datasetSchema`:
```typescript
export const datasetSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  examples: z.array(exampleSchema),
  is_sample: z.boolean().optional().default(false),
});
```

Add at the end of the file:
```typescript
export const settingsSchema = z.object({ sandbox_enabled: z.boolean() });
export type Settings = z.infer<typeof settingsSchema>;

export const dataCountsSchema = z.object({ datasets: z.number(), receipts: z.number() });
export type DataCounts = z.infer<typeof dataCountsSchema>;

export function getSettings(): Promise<Settings> {
  return getJson("/api/settings", settingsSchema);
}

async function mutate<T>(url: string, method: string, schema: z.ZodType<T>, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method,
    headers: body === undefined ? undefined : { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `${method} ${url} → HTTP ${res.status}`);
  }
  return schema.parse(await res.json());
}

export function setSandbox(enabled: boolean): Promise<Settings> {
  return mutate("/api/settings", "PUT", settingsSchema, { sandbox_enabled: enabled });
}

export function seedSampleData(): Promise<DataCounts> {
  return mutate("/api/sample-data/seed", "POST", dataCountsSchema);
}

export function removeSampleData(): Promise<DataCounts> {
  return mutate("/api/sample-data", "DELETE", dataCountsSchema);
}

export function clearAllData(): Promise<DataCounts> {
  return mutate("/api/data", "DELETE", dataCountsSchema);
}
```

- [ ] **Step 4: Run tests + typecheck**

Run: `pnpm --dir web test src/lib/api.test.ts && pnpm --dir web exec tsc --noEmit`
Expected: PASS, tsc clean.

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/api.ts web/src/lib/api.test.ts
git commit -m "feat(web): api client for settings + sample-data; is_sample on dataset"
```

---

## Task 6: SettingsView + rail navigation

**Files:**
- Create: `web/src/features/proof/SettingsView.tsx`
- Modify: `web/src/app/App.tsx`
- Test: `web/src/features/proof/SettingsView.test.tsx`

**Interfaces:**
- Consumes: `getSettings`, `setSandbox`, `seedSampleData`, `removeSampleData`, `clearAllData`.
- Produces: `<SettingsView />`; `View` union gains `"settings"`.

- [ ] **Step 1: Write the failing test**

```tsx
// web/src/features/proof/SettingsView.test.tsx
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { expect, test, vi, beforeEach } from "vitest";
import { renderWithQuery } from "../../test/renderWithQuery";
import { SettingsView } from "./SettingsView";

beforeEach(() => {
  vi.spyOn(global, "fetch").mockImplementation(async (url, init) => {
    const method = (init?.method ?? "GET").toUpperCase();
    if (String(url).endsWith("/api/settings") && method === "GET")
      return new Response(JSON.stringify({ sandbox_enabled: false }), { status: 200 });
    if (String(url).endsWith("/api/settings") && method === "PUT")
      return new Response(JSON.stringify({ sandbox_enabled: true }), { status: 200 });
    if (String(url).endsWith("/api/data") && method === "DELETE")
      return new Response(JSON.stringify({ datasets: 0, receipts: 0 }), { status: 200 });
    return new Response("{}", { status: 200 });
  });
});

test("renders the three data actions and the sandbox toggle", async () => {
  renderWithQuery(<SettingsView />);
  expect(await screen.findByRole("button", { name: /Seed sample data/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Remove sample data/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Clear all data/i })).toBeInTheDocument();
  expect(screen.getByRole("switch", { name: /Sandbox/i })).toBeInTheDocument();
});

test("Clear all data needs a second confirm step", async () => {
  renderWithQuery(<SettingsView />);
  const clear = await screen.findByRole("button", { name: /Clear all data/i });
  fireEvent.click(clear);
  // First click reveals an explicit Confirm; nothing destructive fired yet.
  const confirm = await screen.findByRole("button", { name: /Confirm clear/i });
  fireEvent.click(confirm);
  await waitFor(() =>
    expect(global.fetch).toHaveBeenCalledWith("/api/data", expect.objectContaining({ method: "DELETE" })),
  );
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test src/features/proof/SettingsView.test.tsx`
Expected: FAIL — `./SettingsView` does not exist.

- [ ] **Step 3: Create `SettingsView.tsx`**

```tsx
// web/src/features/proof/SettingsView.tsx
import { useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Database, Trash2 } from "lucide-react";

import {
  clearAllData,
  getSettings,
  removeSampleData,
  seedSampleData,
  setSandbox,
} from "../../lib/api";
import { ViewShell } from "./ViewShell";

// One Data Management card: a Sandbox toggle plus seed / remove-samples / clear-all. Destructive
// actions use an inline two-step confirm (no modal dependency); Clear all is the only red control.
export function SettingsView() {
  const qc = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: getSettings });

  const invalidateData = () => {
    void qc.invalidateQueries({ queryKey: ["datasets"] });
    void qc.invalidateQueries({ queryKey: ["runs"] });
    void qc.invalidateQueries({ queryKey: ["selection"] });
  };

  const sandbox = useMutation({
    mutationFn: (enabled: boolean) => setSandbox(enabled),
    onSuccess: (s) => {
      qc.setQueryData(["settings"], s);
      void qc.invalidateQueries({ queryKey: ["selection"] });
    },
  });
  const seed = useMutation({ mutationFn: seedSampleData, onSuccess: invalidateData });
  const removeSamples = useMutation({ mutationFn: removeSampleData, onSuccess: invalidateData });
  const clearAll = useMutation({ mutationFn: clearAllData, onSuccess: invalidateData });

  const on = settings.data?.sandbox_enabled ?? false;

  return (
    <ViewShell
      title="Settings"
      subtitle="Manage your local data and the simulated sandbox. Everything here stays on this machine."
    >
      <section className="grid max-w-2xl gap-6 rounded-xl border border-(--color-panel-line) bg-(--color-panel-card) p-6">
        <div>
          <h3 className="text-sm font-medium text-(--color-ink)">Data management</h3>
          <p className="mt-1 text-sm text-(--color-ink-muted)">
            Reset or populate this install. Sample data is generated by the simulated mocks and is
            clearly flagged.
          </p>
        </div>

        {/* Sandbox toggle */}
        <div className="flex items-start justify-between gap-4 border-t border-(--color-panel-line) pt-4">
          <div>
            <p className="text-sm text-(--color-ink)">Sandbox</p>
            <p className="text-xs text-(--color-ink-faint)">
              Show simulated Mock models in the picker for keyless trial runs. Off by default —
              mock runs are not a real evaluation.
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={on}
            aria-label="Sandbox"
            disabled={settings.isLoading || sandbox.isPending}
            onClick={() => sandbox.mutate(!on)}
            className={
              "relative h-6 w-11 shrink-0 rounded-full transition-colors " +
              (on ? "bg-(--color-accent)" : "bg-(--color-panel-line-strong)")
            }
          >
            <span
              className={
                "absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all " +
                (on ? "left-[1.375rem]" : "left-0.5")
              }
            />
          </button>
        </div>

        {/* Seed */}
        <ActionRow
          label="Seed sample data"
          description="Add a sample dataset and a finished Proof Receipt so the product isn't empty. Re-running replaces the previous sample."
          actionLabel="Seed sample data"
          icon={<Database aria-hidden className="h-4 w-4" />}
          pending={seed.isPending}
          onConfirm={() => seed.mutate()}
          done={seed.isSuccess ? `Seeded ${seed.data?.datasets} dataset, ${seed.data?.receipts} receipt.` : null}
        />

        {/* Remove samples */}
        <ActionRow
          label="Remove sample data"
          description="Delete only the seeded sample dataset and receipts. Your own datasets and receipts are kept."
          actionLabel="Remove sample data"
          pending={removeSamples.isPending}
          onConfirm={() => removeSamples.mutate()}
          done={removeSamples.isSuccess ? "Sample data removed." : null}
        />

        {/* Clear all — destructive */}
        <ActionRow
          label="Clear all data"
          description="Permanently delete ALL datasets and receipts on this install (samples and your own). Settings are kept. This cannot be undone."
          actionLabel="Clear all data"
          confirmLabel="Confirm clear"
          destructive
          icon={<Trash2 aria-hidden className="h-4 w-4" />}
          pending={clearAll.isPending}
          onConfirm={() => clearAll.mutate()}
          done={clearAll.isSuccess ? "All data cleared." : null}
        />
      </section>
    </ViewShell>
  );
}

// An action with an inline two-step confirm: first click reveals Confirm/Cancel; only Confirm fires.
function ActionRow({
  label,
  description,
  actionLabel,
  confirmLabel = "Confirm",
  destructive = false,
  icon,
  pending,
  onConfirm,
  done,
}: {
  label: string;
  description: string;
  actionLabel: string;
  confirmLabel?: string;
  destructive?: boolean;
  icon?: ReactNode;
  pending: boolean;
  onConfirm: () => void;
  done: string | null;
}) {
  const [armed, setArmed] = useState(false);
  const base =
    "inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm transition-colors disabled:opacity-50";
  return (
    <div className="grid gap-2 border-t border-(--color-panel-line) pt-4">
      <p className="text-sm text-(--color-ink)">{label}</p>
      <p className="text-xs text-(--color-ink-faint)">{description}</p>
      <div className="flex items-center gap-2">
        {!armed ? (
          <button
            type="button"
            aria-label={actionLabel}
            disabled={pending}
            onClick={() => setArmed(true)}
            className={
              base +
              " " +
              (destructive
                ? "border-(--color-danger)/50 text-(--color-danger) hover:bg-(--color-danger)/10"
                : "border-(--color-panel-line) text-(--color-ink) hover:border-(--color-panel-line-strong)")
            }
          >
            {icon}
            {actionLabel}
          </button>
        ) : (
          <>
            <button
              type="button"
              aria-label={confirmLabel}
              disabled={pending}
              onClick={() => {
                onConfirm();
                setArmed(false);
              }}
              className={
                base +
                " " +
                (destructive
                  ? "border-(--color-danger) bg-(--color-danger)/10 text-(--color-danger)"
                  : "border-(--color-accent) bg-(--color-accent)/10 text-(--color-ink)")
              }
            >
              {confirmLabel}
            </button>
            <button
              type="button"
              onClick={() => setArmed(false)}
              className={base + " border-(--color-panel-line) text-(--color-ink-muted)"}
            >
              Cancel
            </button>
          </>
        )}
        {done ? <span className="text-xs text-(--color-ink-faint)">{done}</span> : null}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Wire the rail nav**

In `web/src/app/App.tsx`: import `Settings` from `lucide-react` and `SettingsView`:
```tsx
import { Boxes, Database, Gauge, Monitor, Moon, ReceiptText, Settings, Sun, type LucideIcon } from "lucide-react";
import { SettingsView } from "../features/proof/SettingsView";
```
Extend the `View` union and `NAV`:
```tsx
type View = "proof" | "datasets" | "candidates" | "receipts" | "settings";
```
```tsx
  { id: "receipts", label: "Receipts", Icon: ReceiptText },
  { id: "settings", label: "Settings", Icon: Settings },
```
Render the view (after the `receipts` block in `App`):
```tsx
      {view === "settings" && <SettingsView />}
```

- [ ] **Step 5: Run tests + typecheck**

Run: `pnpm --dir web test src/features/proof/SettingsView.test.tsx && pnpm --dir web exec tsc --noEmit`
Expected: PASS, tsc clean.

- [ ] **Step 6: Commit**

```bash
git add web/src/features/proof/SettingsView.tsx web/src/features/proof/SettingsView.test.tsx web/src/app/App.tsx
git commit -m "feat(web): Settings view — sandbox toggle + seed/remove/clear with inline confirm"
```

---

## Task 7: Picker default-selection, first-run copy, Mock icon, Sample badges

**Files:**
- Modify: `web/src/features/proof/ProofCockpit.tsx`
- Modify: `web/src/features/proof/ProviderLogo.tsx`
- Modify: `web/src/features/proof/DatasetsView.tsx`
- Modify: `web/src/features/proof/ReceiptsView.tsx`
- Test: `web/src/features/proof/ProviderLogo.test.tsx` (extend)

**Interfaces:** none new — behavior changes only.

- [ ] **Step 1: Write the failing test (Mock icon)**

```tsx
// web/src/features/proof/ProviderLogo.test.tsx  (append)
import { render } from "@testing-library/react";
import { expect, test } from "vitest";
import { ProviderLogo } from "./ProviderLogo";

test("mock provider renders a flask icon (not a brand glyph or bare dot)", () => {
  const { container } = render(<ProviderLogo providerId="mock" available label="Mock" />);
  // lucide FlaskConical renders an <svg> with aria-hidden; assert an icon SVG is present.
  expect(container.querySelector("svg")).toBeTruthy();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test src/features/proof/ProviderLogo.test.tsx`
Expected: FAIL — `mock` falls through to the non-SVG availability dot (`<span>`), no `<svg>`.

- [ ] **Step 3: Add the Mock icon to `ProviderLogo`**

In `web/src/features/proof/ProviderLogo.tsx`, import the icon and add a branch before the `BRAND_PATHS` lookup:
```tsx
import { FlaskConical } from "lucide-react";
```
Inside `ProviderLogo`, before `const path = BRAND_PATHS[providerId];`:
```tsx
  if (providerId === "mock") {
    return (
      <FlaskConical
        aria-hidden
        className={"h-4 w-4 shrink-0 " + (available ? "text-(--color-ink)" : "text-(--color-ink-faint)")}
      />
    );
  }
```

- [ ] **Step 4: Default-selection from the mock group (ProofCockpit)**

In `web/src/features/proof/ProofCockpit.tsx`, replace the `resolvedSelected` memo body:
```tsx
  const resolvedSelected = useMemo(() => {
    if (selected.length > 0) return selected;
    // Mocks are now one "mock" provider group, present only when Sandbox is on. Pre-select its
    // models (mock_good / mock_bad) so a sandbox user gets the one-click keyless run. Off → none.
    const mock = (selection.data?.providers ?? []).find((g) => g.provider_id === "mock");
    return mock ? mock.models.map((m) => m.candidate_id) : [];
  }, [selected, selection.data]);
```

- [ ] **Step 5: Update the first-run empty copy (ProofCockpit)**

Find the `EmptyResults` first-run line that reads "The sample dataset and both mock providers are pre-selected — press …" (around line 337) and replace the mock clause with a calm, accurate pointer:
```tsx
        to trust. No keys yet? Add a provider key, enable <span className="text-(--color-ink)">Sandbox</span>{" "}
        in Settings to try the simulated mocks, or seed sample data to explore a finished receipt.
```
(Keep the surrounding JSX/structure; only swap the sentence that referenced pre-selected mocks.)

- [ ] **Step 6: Sample badge — DatasetsView**

In `web/src/features/proof/DatasetsView.tsx`, in the dataset card header, after the `<h3>`:
```tsx
                {d.is_sample ? (
                  <span className="rounded border border-(--color-panel-line) bg-(--color-panel-card) px-2 py-0.5 text-[11px] font-medium text-(--color-ink-muted)">
                    Sample
                  </span>
                ) : null}
```

- [ ] **Step 7: Sample badge — ReceiptsView**

In `web/src/features/proof/ReceiptsView.tsx`, inside `ReceiptCard`, next to the heading (run ids `run_sample…` are sample receipts — hex run ids can never collide):
```tsx
          <span className="font-medium text-(--color-ink)">{heading}</span>
          {run.id.startsWith("run_sample") ? (
            <span className="rounded border border-(--color-panel-line) px-2 py-0.5 text-[11px] font-medium text-(--color-ink-muted)">
              Sample
            </span>
          ) : null}
```
(Place it within the existing flex row that holds the heading.)

- [ ] **Step 8: Run web tests + typecheck**

Run: `pnpm --dir web test && pnpm --dir web exec tsc --noEmit`
Expected: PASS (84 prior + new), tsc clean. Note: any existing test asserting mocks are pre-selected by default will need updating — see Task 8 for the e2e; if a unit test asserts it, update it to reflect sandbox-off default.

- [ ] **Step 9: Commit**

```bash
git add web/src/features/proof/ProofCockpit.tsx web/src/features/proof/ProviderLogo.tsx web/src/features/proof/ProviderLogo.test.tsx web/src/features/proof/DatasetsView.tsx web/src/features/proof/ReceiptsView.tsx
git commit -m "feat(web): default-selection from sandbox mock group, Mock flask icon, Sample badges, first-run copy"
```

---

## Task 8: e2e rework + new settings spec + full verification

**Files:**
- Modify: `e2e/playwright/proof.spec.ts`
- Create: `e2e/playwright/settings.spec.ts`

**Interfaces:** none — end-to-end behavior.

- [ ] **Step 1: Rebuild the embed (the e2e server serves it)**

Run: `bash scripts/build.sh`
Expected: builds web/dist, copies to `src/orionfold/server/static`, builds the wheel.

- [ ] **Step 2: Rework `proof.spec.ts` to enable Sandbox first**

The default no longer pre-selects mocks. At the start of the "proof loop" test (after `await page.goto("/")` and the heading/Connected assertions), enable Sandbox and select the mocks:
```typescript
  // Mocks are off the happy path now — turn on Sandbox, then pick the Mock provider's models.
  await page.getByRole("button", { name: "Settings" }).click();
  await page.getByRole("switch", { name: /Sandbox/i }).click();
  await page.getByRole("button", { name: "Proof Run" }).click();

  await expect(page.getByRole("checkbox", { name: "Good model" })).toBeVisible();
  await page.getByRole("checkbox", { name: "Good model" }).check();
  await page.getByRole("checkbox", { name: "Bad model" }).check();
```
Then keep the existing run + leaderboard assertions. The leaderboard label is unchanged (`Mock · good`), so `await expect(leaderboard.getByText("100% (5/5)")).toBeVisible();` and the "Recommended" / "Failure cases (5)" / "simulated provider failure" assertions stay. Remove the old `await expect(page.getByRole("checkbox", { name: "Mock · good" })).toBeChecked();` line and the `+ custom for Ollama` default assertion if it depended on the mock-default screen (keep it only if still valid with Sandbox on).

- [ ] **Step 3: Create `settings.spec.ts`**

```typescript
// e2e/playwright/settings.spec.ts
import { expect, test } from "@playwright/test";

test("seed populates Receipts with a Sample receipt, then remove clears it", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Settings" }).click();

  await page.getByRole("button", { name: /^Seed sample data$/ }).click();
  await page.getByRole("button", { name: /^Confirm$/ }).click();

  await page.getByRole("button", { name: "Receipts" }).click();
  await expect(page.getByText("Sample").first()).toBeVisible();

  await page.getByRole("button", { name: "Settings" }).click();
  await page.getByRole("button", { name: /^Remove sample data$/ }).click();
  await page.getByRole("button", { name: /^Confirm$/ }).click();

  await page.getByRole("button", { name: "Receipts" }).click();
  await expect(page.getByText(/No proof runs yet/i)).toBeVisible();
});

test("sandbox toggle shows and hides the Mock provider in the picker", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("checkbox", { name: "Good model" })).toHaveCount(0);

  await page.getByRole("button", { name: "Settings" }).click();
  await page.getByRole("switch", { name: /Sandbox/i }).click();
  await page.getByRole("button", { name: "Proof Run" }).click();
  await expect(page.getByRole("checkbox", { name: "Good model" })).toBeVisible();
});
```

- [ ] **Step 4: Run e2e**

Run: `pnpm --dir web e2e`
Expected: all specs PASS (the webServer boots the embedded build with a fresh temp DB; sandbox starts off).

- [ ] **Step 5: Full verification sweep**

Run:
```bash
uv run pytest -q
uv run ruff check src tests
pnpm --dir web test
pnpm --dir web exec tsc --noEmit
pnpm --dir web build
bash scripts/build.sh && pnpm --dir web e2e
```
Expected: backend green (config_hash 467ddd96c9a5 intact), ruff clean, web tests green, tsc clean, build clean, e2e green.

- [ ] **Step 6: Browser visual check (both themes)**

Use the `browser-visual-verification` skill: start `orionfold up`, open Settings (sandbox toggle + three buttons; Clear all is red), seed → Receipts shows a "Sample" badge, enable Sandbox → Proof Run shows the "Mock" provider (flask icon) with Good/Bad model chips. Confirm light + dark + AA, and that mocks are absent from Proof Run when sandbox is off.

- [ ] **Step 7: Commit**

```bash
git add e2e/playwright/proof.spec.ts e2e/playwright/settings.spec.ts
git commit -m "test(e2e): gate mock run behind Sandbox; add settings/sample-data spec"
```

---

## Self-review notes

- **Spec coverage:** settings store (Task 1), sample-data ops + seed-time generation (Task 2), `selection_panel(sandbox)` reshape + bare-id invariant (Task 3), five endpoints + `is_sample` exposure + sandbox-aware selection (Task 4), api client (Task 5), Settings UI + nav + inline confirm + sandbox toggle (Task 6), default-selection/first-run/Mock icon/Sample badges (Task 7), e2e rework + verification (Task 8). All spec sections map to a task.
- **Deviation from spec (documented):** the spec mentioned a "stale-selection guard" when sandbox flips off. It is intentionally omitted — the picker renders only panel groups (no phantom chips), mock ids always resolve server-side, and a blanket prune would wrongly drop valid custom-model selections (`provider:model` ids not in `group.models`). No guard needed.
- **Receipt sample detection** uses the `run_sample…` id prefix (hex run ids can't collide) to avoid changing the `/runs` response shape; dataset samples use the exposed `is_sample` field (a user dataset named "Sample …" slugs to `sample-…`, so id-prefix detection would be unsafe there — hence the column).
- **Invariants:** domain `Dataset` model untouched (is_sample lives only in the API `DatasetRow`); engine candidate labels and `config_hash` untouched; `build_candidates(["mock_good","mock_bad"])` still resolves (Task 3 guard + full suite in Tasks 3/4/8).
