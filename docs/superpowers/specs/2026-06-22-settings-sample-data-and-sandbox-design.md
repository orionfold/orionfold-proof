# Design — Settings: sample data, sandbox, and mocks out of the happy path

- **Date:** 2026-06-22
- **Status:** Approved (brainstorm) — pending spec review
- **Scope:** `web/` cockpit + `src/orionfold` backend. Local-first, single-user. No cloud.

## Problem

Mock providers (`mock_good` / `mock_bad`) are pre-selected in the **Candidates** picker and are the
default keyless run. But mocks are **simulated output, not a real evaluation** — the scoring pipeline
is real, the thing being scored is authored. Defaulting a serious user into comparing two fakes is a
credibility risk: a mock receipt is shaped identically to a real one but is evidence of nothing.

We are **removing mocks from the default customer happy path** while **keeping the mock
infrastructure** for two opt-in purposes, exposed through a new **Settings** area (modeled on the
`ainative` "Data Management" Settings section):

1. **Seed sample data** — populate a new/empty install with realistic sample Datasets + finished
   Proof Receipts (generated via the mocks) + a staged brief, so the product isn't empty on first
   run and a keyless user can *explore* a real-looking receipt.
2. **Sandbox toggle** — re-enable the mocks in the picker for keyless trial runs, opt-in only.

Plus destructive data controls: **Remove sample data** (targeted) and **Clear all data** (nuclear).

## Goals / Non-goals

**Goals**
- No mock candidates in the picker unless Sandbox is explicitly ON (default OFF).
- A Settings destination with a Data Management card: Sandbox toggle, Seed, Remove samples, Clear all.
- Seeded artifacts are flagged (`is_sample`) so they're distinguishable and individually removable.
- Preserve all standing invariants: mocks stay **bare-id** (`mock_good`/`mock_bad`), engine candidate
  labels stay `Mock · good` / `Mock · bad`, model-compare byte-identity (`config_hash 467ddd96c9a5`)
  and `RECEIPT_VERSION 6` unchanged.

**Non-goals**
- No multi-user / auth / cloud settings. No general settings framework beyond one KV table.
- No new modal/dialog dependency (use an inline two-step confirm).
- No change to the receipt schema or the engine's candidate labels.
- No production environment guard (this is a local app; destructive ops are confirm-gated instead).

## Architecture

Three small, isolated capabilities:

1. **Settings store (backend):** a KV `settings` table + a thin repo (`get_setting`/`set_setting`).
   One key today: `sandbox_enabled` (default `false`).
2. **Sample-data ops (backend):** `seed` / `remove_samples` / `clear_all` on the repository, keyed off
   an `is_sample` flag on `datasets` and `runs`.
3. **Settings UI (frontend):** a new "Settings" rail destination with a Data Management card and the
   Sandbox toggle.

**Gating flow:** the cockpit reads `GET /api/settings`; `selection_panel(sandbox: bool)` emits the
Mock provider group only when sandbox is on. Default off → mocks absent from the happy path.

## Data model & migrations (append-only)

Append three migrations (existing indices are 0–1):
```sql
-- index 2
ALTER TABLE datasets ADD COLUMN is_sample INTEGER NOT NULL DEFAULT 0;
-- index 3
ALTER TABLE runs     ADD COLUMN is_sample INTEGER NOT NULL DEFAULT 0;
-- index 4
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
```
- Existing `datasets` / `runs` list queries are **unchanged** — samples appear alongside real data
  (the point: populated views). `is_sample` is used only for targeted removal + a "Sample" badge.
- **Stable sample ids** make Seed idempotent: dataset id `sample-investment-memo`, run id
  `run_sample01` (fixed `created_at`). Seeding = delete `is_sample` rows, then insert — no duplicates.
- Pre-existing DBs gain the columns/table via `apply_migrations` on next connect.

## Backend

### Endpoints (all local, under `/api`)
| Method | Path | Body / returns |
| --- | --- | --- |
| GET | `/api/settings` | → `{ "sandbox_enabled": bool }` |
| PUT | `/api/settings` | `{ "sandbox_enabled": bool }` → updated settings |
| POST | `/api/sample-data/seed` | → `{ "datasets": int, "receipts": int }` |
| DELETE | `/api/sample-data` | → `{ "datasets": int, "receipts": int }` (removed) |
| DELETE | `/api/data` | → `{ "datasets": int, "receipts": int }` (cleared) |

- `GET /selection` reads `sandbox_enabled` from settings and passes it to `selection_panel`.

### `settings` repo
- `get_setting(conn, key, default) -> str | None`; `set_setting(conn, key, value)`.
- Booleans stored as `"true"`/`"false"`. `sandbox_enabled` defaults to `false` when absent.

### `selection_panel(sandbox: bool)`
- When `sandbox` is True, **prepend one** group:
  ```
  SelectionGroup(provider_id="mock", label="Mock", privacy="local",
    available=True, supports_custom=False, candidate_id=None,
    models=[ SelectionModel(candidate_id="mock_good", model="good", display_name="Good model", ...),
             SelectionModel(candidate_id="mock_bad",  model="bad",  display_name="Bad model",  ...) ])
  ```
- When False, omit it entirely (the two old single-candidate mock groups are gone).
- **`build_candidates` is unchanged** — the ids sent to the run are still bare `mock_good`/`mock_bad`;
  the reshaping is presentation-only. `tier`/`cost_class` for the mock models use neutral/free values.

### Seeding (`seed` module)
- Upsert the bundled sample dataset(s) (`investment-memo-summarization`) into `datasets` with
  `is_sample=1` and stable id.
- Call `run_proof` with the mock candidates on that dataset — deterministic, no network, mirroring
  `scripts/gen_samples.py` (fixed `run_id`/`created_at`) — and save the resulting `ProofReport` JSON
  into `runs` with `is_sample=1`. Always matches the current `RECEIPT_VERSION`.
- Return counts. Idempotent via the delete-samples-then-insert path.

## Frontend

- **Rail:** add a 5th nav item "Settings" (lucide `Settings`); extend the `View` union and `NAV`.
  Theme switcher stays in the footer.
- **`SettingsView`** (wrapped in `ViewShell`) with one **Data Management** card, styled to the
  Orionfold skin (neutral secondary buttons; red `--color-danger` for Clear all):
  - **Sandbox toggle** — labeled switch: "Sandbox — show simulated Mock models for keyless trial
    runs." Off by default. On change → `setSandbox` mutation → invalidate `selection`.
  - **Seed sample data** — neutral button + description → light inline confirm → `seedSampleData`
    → toast/inline feedback with counts → invalidate `datasets`, `receipts`, `selection`.
  - **Remove sample data** — neutral button → inline confirm → `removeSampleData` → invalidate.
  - **Clear all data** — red button + "Irreversible" warning → **strong** inline confirm →
    `clearAllData` → invalidate.
  - Confirmations are an **inline two-step confirm** (button reveals Confirm/Cancel) — no modal dep.
- **API client (`lib/api.ts`):** `getSettings`, `setSandbox`, `seedSampleData`, `removeSampleData`,
  `clearAllData`. TanStack Query: a `settings` query + four mutations with the invalidations above.
- **Candidate picker / cockpit:**
  - When the panel includes the `mock` group, `CandidatePicker` renders it via the existing
    provider-group/model-chip path → "Mock" provider row with **Good model / Bad model** chips.
  - `ProviderLogo` gains a `mock → FlaskConical` icon; `ProviderTag` already maps `mock` → neutral
    "Mock" (id `mock` still satisfies `providerKind`'s `startsWith("mock")`).
  - **Default selection:** pre-select `mock_good`+`mock_bad` only when the mock group is present.
    Sandbox off + no keys → nothing pre-selected, Run disabled.
  - **Stale-selection guard:** when the panel changes (sandbox flips off), drop selected ids not in
    the panel.
  - **First-run copy** in `ProofCockpit` changes from "both mock providers are pre-selected" to a
    calm pointer: add a provider key, enable Sandbox in Settings, or seed sample data to explore.
  - **Staged brief:** after seeding, the cockpit defaults to the seeded sample dataset, and the
    existing `DEFAULT_BRIEF` (already "Investment memo summarization", matching the sample) headlines
    it — so re-running the sample is one click. No extra persistence; "staged" = default-dataset +
    the existing default brief, not a new stored brief.
- **Sample badges:** expose `is_sample` on the dataset/run API shapes; show a small neutral "Sample"
  tag on seeded rows in `DatasetsView` / `ReceiptsView`.

### Scope guard (invariants)
Only the **picker presentation** is reshaped. Engine candidate **labels stay `Mock · good` /
`Mock · bad`**, so seeded/sample receipts and `config_hash 467ddd96c9a5` byte-identity are untouched.
"Good model / Bad model" is the picker label only.

## Error handling & edge cases

- **Re-seed** = delete `is_sample` rows then insert (idempotent; never duplicates).
- **Sandbox off mid-session** → `selection` refetches without mocks; cockpit drops stale mock
  selections.
- **Clear all** from the Receipts view → invalidation yields the empty state.
- **Old DB** (no `is_sample`/`settings`) → migrations add them on next connect; `sandbox_enabled`
  defaults off.
- **Endpoint errors** → standard JSON error; UI shows an inline `--color-danger` message (existing
  pattern), no secret leakage (these endpoints touch only datasets/runs/settings).

## Testing

**Backend unit**
- Migrations add `is_sample` columns + `settings` table; idempotent re-apply.
- `settings` get/set; `sandbox_enabled` default false.
- `seed` creates `is_sample` dataset + run with stable ids; **re-seed is idempotent** (no dup);
  returns correct counts.
- `remove_samples` deletes only `is_sample` rows; real rows survive.
- `clear_all` deletes `datasets`+`runs`, leaves `settings`.
- `selection_panel(False)` → no mock group; `selection_panel(True)` → exactly one `mock` group with
  two models → candidate ids `mock_good`/`mock_bad`.
- **Invariant guards:** `build_candidates(["mock_good","mock_bad"])` still resolves; the model-compare
  sample reproduces `config_hash 467ddd96c9a5`.
- Route tests for all five endpoints (happy + a basic error).

**Frontend unit**
- `SettingsView` renders the toggle + three buttons; Clear all requires the second confirm step.
- New `api.ts` functions (mirroring `api.test.ts` patterns).
- `CandidatePicker` renders the Mock provider with "Good model"/"Bad model" chips when present.
- Cockpit default selection: panel with mocks → `mock_good`+`mock_bad` pre-selected; panel without →
  none.
- `ProviderLogo`/`ProviderTag` mock case (flask icon + neutral "Mock").

**e2e (contract change — called out)**
- `proof.spec` today assumes mocks are pre-selected. **Rework:** enable Sandbox via Settings first,
  then select the Mock provider's Good/Bad models and run; leaderboard assertions stay `Mock · good`
  (engine label unchanged).
- **New `settings.spec`:** seed → Receipts populated (Sample badge) → remove samples → empty; sandbox
  toggle → Mock provider appears/disappears in the picker.

## Implementation order (suggested)

1. Backend migrations (`is_sample` ×2, `settings`) + `settings` repo + tests.
2. Repository `seed` / `remove_samples` / `clear_all` + tests.
3. `selection_panel(sandbox)` reshape + `build_candidates` invariant tests.
4. Five API endpoints + route tests.
5. Frontend `api.ts` + `settings` query/mutations.
6. `SettingsView` + rail nav entry + inline confirm.
7. Candidate picker / cockpit default-selection + first-run copy + `ProviderLogo` mock icon +
   `is_sample` badges.
8. e2e rework (`proof.spec`) + new `settings.spec`; full verification (`pytest`, `vitest`, `tsc`,
   `build`, embed rebuild, `e2e`) + both-theme browser check.
