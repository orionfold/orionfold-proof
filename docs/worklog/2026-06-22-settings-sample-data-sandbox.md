# Worklog — 2026-06-22 — Settings: sample data, sandbox, mocks out of the happy path

## Summary
Removed the mock providers from the default Candidates picker and added a **Settings** area to manage
local data and an opt-in **Sandbox**. Mocks are simulated output, not a real evaluation, so defaulting
a user into comparing two fakes was a credibility risk; they're now infrastructure (tests, keyless
onboarding) rather than the default customer path.

Brainstormed → spec (`docs/superpowers/specs/2026-06-22-settings-sample-data-and-sandbox-design.md`)
→ plan (`docs/superpowers/plans/2026-06-22-settings-sample-data-and-sandbox.md`) → executed in 8 TDD
tasks. Modeled on the `ainative` "Data Management" Settings section.

## What shipped (file by file)
- **Migrations + settings store** — append-only `is_sample` columns on `datasets`/`runs` + a `settings`
  KV table (`storage/db.py`); `storage/settings.py` (`get/set_setting`, `get/set_sandbox_enabled`).
- **Sample-data ops** — `repository.py`: `is_sample` on `save_report`, `insert_sample_dataset`,
  `list_dataset_rows`, `remove_sample_data`, `clear_all_data`. `sample_data.py`: `seed_sample_data`
  runs the mocks through `run_proof` (deterministic, no network) to produce a sample dataset + receipt.
- **Selection reshape** — `selection_panel(sandbox: bool)`: with sandbox on, one `mock` provider group
  exposing Good/Bad models; off → no mocks. Candidate ids stay bare (`mock_good`/`mock_bad`).
- **API** — `GET/PUT /api/settings`, `POST /api/sample-data/seed`, `DELETE /api/sample-data`,
  `DELETE /api/data`; `is_sample` on `/datasets` (via `DatasetRow`); sandbox-aware `/selection`.
- **Frontend** — `lib/api.ts` client + `is_sample` on dataset schema; `SettingsView.tsx` (Data
  Management card: Sandbox toggle + Seed/Remove/Clear with an inline two-step confirm, Clear all in
  `--color-danger`); Settings rail nav; cockpit default-selection from the mock group + first-run copy;
  `ProviderLogo` flask icon for `mock`; "Sample" badges in Datasets/Receipts.
- **e2e** — `proof.spec` enables Sandbox via the API before the mock run; new `settings.spec`
  (seed→badge→remove, sandbox toggle shows/hides Mock); Playwright set to serial (`workers: 1`) since
  the suite shares one embedded server + one DB and now mutates global state.

## Verification
- `uv run pytest` **239 passed** (1 pre-existing Starlette deprecation warning) · `ruff` clean.
- `pnpm --dir web test` **90 passed** · `tsc --noEmit` clean · `pnpm --dir web build` clean.
- `bash scripts/build.sh` (embed rebuilt) · `pnpm --dir web e2e` **8 passed** (serial).
- Real-browser visual check (both themes): sandbox-off Proof Run shows no mocks (only real providers,
  none pre-selected); SettingsView renders correctly in light + dark (neutral Seed/Remove, red Clear
  all, cyan Sandbox toggle); sandbox-on shows the **Mock** provider (flask icon) with Good/Bad model
  chips pre-selected. AA legible.
- **Invariants intact:** `config_hash 467ddd96c9a5` reproduced (guarded test); `RECEIPT_VERSION` 6;
  domain `Dataset` model unchanged (`is_sample` lives only in the API `DatasetRow`); engine candidate
  labels stay `Mock · good`/`Mock · bad`.

## Product impact
A new keyless user no longer compares two fakes by default; the happy path shows real providers (add a
key to run) with Sandbox + Seed sample data as opt-in ways to explore. The mock infrastructure is
preserved for the pivot and for the deterministic test suite.

## Risks / notes
- `sandbox_enabled` is a single global setting; e2e runs serially to avoid shared-DB races. If the
  suite grows, consider per-test DB isolation.
- Sample receipts are detected in the UI by the stable `run_sample…` id prefix (hex run ids never
  collide); sample datasets use the `is_sample` column (a user dataset named "Sample …" would slug to
  `sample-…`, so id-prefix detection would be unsafe there).
- Deviation from spec (documented in the plan): the stale-selection guard was omitted — it would
  wrongly drop valid custom-model selections, and the picker only renders panel groups anyway.

## Next recommended step
Backlog (non-blocking): set up a git remote + push (no remote configured); DS-skin polish from the
roadmap write-back (cyan `m-fill` leaderboard bars, shared badge/chip kit). Any further mock-data
authoring (richer sample datasets) can extend `sample_data.py`.
