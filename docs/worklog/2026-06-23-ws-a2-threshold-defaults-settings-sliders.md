# Worklog — 2026-06-23 · WS-A2: Per-method default thresholds + Settings sliders

**Task:** Stage-3 Task 2 (WS-A2, HIGH) from `_SPECS/2026-06-22-trustworthy-proof-and-polish.md`.
Make the first real proof produce a **clear winner** instead of "NO CLEAR WINNER" by giving each
scoring method a realistic default threshold, and let the operator tune those defaults via persisted
Settings sliders.

## Summary

Two layers, exactly as the spec decided:

1. **Built-in per-kind default map (fallback).** `DEFAULT_THRESHOLDS = {similarity: 0.55,
   keypoint: 0.8, judge: 0.8}` in `src/orionfold/scoring/rubric.py`, mirrored in
   `web/src/features/proof/scoring.ts`. Similarity drops from the old universal 0.80 to a lenient
   0.55 (good paraphrased summaries score ~0.2–0.5 on lexical overlap; 0.80 wrongly read them as
   "no winner"). Keypoint/Judge stay strict at 0.80.
2. **User-configurable override (persisted).** Three 0–1 sliders in Settings → "Default scoring
   thresholds." The persisted value overrides the map for new runs; the map stays the fallback when
   unset. A Similarity calibration note in the run-setup method card shows the live default and
   points to Settings.

**Persistence surface — resolved the open question (operator-confirmed: reuse existing store).**
Scoping found a generic key/value `settings` table (migration index 4) already powering the Sandbox
toggle, with `/api/settings` GET/PUT and a wired `SettingsView`. So **no new `app_settings` table and
no migration** — extended the existing machinery: new `threshold_<kind>` keys via
`get/set_threshold_defaults` in `storage/settings.py`, widened `SettingsModel` (+ a partial
`SettingsUpdate` for PUT), extended the Zod `settingsSchema`, added a `setThresholds` client.

### Files touched

- **Backend (source):**
  - `scoring/rubric.py` — `DEFAULT_THRESHOLDS` map; new `threshold_for(kind, overrides)`;
    `default_rubric_for(dataset, overrides=None)` now resolves the kind's default via the map +
    optional persisted override.
  - `storage/settings.py` — `get_threshold_defaults` (resolved map, clamped/validated) +
    `set_threshold_defaults` (clamp 0..1, ignore unknown kinds), over the existing `settings` table.
  - `server/routes.py` — `ThresholdDefaults` + `SettingsModel.thresholds`; new partial
    `SettingsUpdate` so PUT stays backward-compatible (sandbox-only writes still work, thresholds-only
    writes work); `_read_settings` helper; both Auto-default sites (`create_run`, `create_run_stream`)
    pass persisted overrides into `default_rubric_for`.
- **Frontend (source):**
  - `lib/api.ts` — `thresholdsSchema`, widened `settingsSchema`, `setThresholds`.
  - `features/proof/scoring.ts` — mirrored `DEFAULT_THRESHOLDS` + `thresholdFor`.
  - `features/proof/ScoringMethod.tsx` — reads the shared `["settings"]` query; the three hardcoded
    `0.8`s become `thresholdFor(kind, thresholds)`; Similarity calibration note.
  - `features/proof/SettingsView.tsx` — "Default scoring thresholds" section + `ThresholdSliders`
    (local draft for smooth dragging, commit-on-release → PUT).
- **Tests:** `tests/unit/test_scoring.py` (+map/threshold_for/override + **mock-hash-safety** test),
  `tests/unit/test_settings_and_samples.py` (threshold store round-trip/clamp/partial),
  `tests/integration/test_proof_api.py` (full GET shape, partial PUT, threshold override drives the
  Auto similarity default), `web/.../scoring.test.ts`, `web/.../ScoringMethod.test.tsx`,
  `web/.../SettingsView.test.tsx`, `web/src/lib/api.test.ts`.

## Verification (evidence)

- **Backend:** `uv run pytest` → **291 passed** (was 281; +10). Ruff clean. Pyright clean on all three
  changed source files (pre-existing test-only `reportOptionalMemberAccess` noise in
  `test_registry.py`/`test_storage.py`/the openpyxl helper is unrelated and predates this change).
- **Frontend:** `pnpm test` → **128 passed** (was 121; +7). `pnpm build` (tsc + vite) clean.
- **Invariant — mock `config_hash` intact:** computed directly — the canonical mock matrix
  (`investment-memo-summarization` + mock_good/mock_bad) resolves to **keypoint @ 0.8** → config_hash
  **`467ddd96c9a5`** (byte-identical). The Similarity-only change never touches the keypoint path the
  mock uses. Frozen by a new explicit test.
- **Browser (real app, live source, :5174):**
  - Settings → "Default scoring thresholds" renders three sliders at 0.55 / 0.80 / 0.80 with the
    calibration copy; cyan accent thumbs, mono tabular values, dark-mode consistent.
  - Dragged Similarity to **0.30** → `GET /api/settings` confirms `similarity: 0.30` persisted to
    SQLite (survives a fresh read).
  - Proof Run → selected the Similarity method card → the calibration note reads **"Passing at 0.30…"**
    — proving the Settings → SQLite → `["settings"]` cache → run-setup prefill loop end-to-end. The
    resolved threshold travels in `config_hash`, so it's part of the proof's identity.
  - Restored the default to **0.55** for a clean demo state.

## Product impact

The flagship "Investment memo summarization" demo no longer steers a first-time real-model run toward
a discouraging "NO CLEAR WINNER" via an over-strict Similarity threshold. The operator can also tune
the per-method defaults to their own workflow, durably and locally. This is 1 of the 3 HIGH "NO CLEAR
WINNER" defects (A1 shipped last session; A3 next).

## Risks / deferrals

- **A2 out-of-scope (per spec):** per-dataset threshold overrides, auto-tuning from data, a
  thresholds-history UI — all deferred.
- **No `RECEIPT_VERSION` bump** — the resolved threshold was already recorded in `rubric`; receipt
  *content* is unchanged. Full-receipt HTML palette-count guard still passes.
- The slider commits on pointer-up / key-up; if a user drags wildly fast it commits the final value
  only (intended — we don't PUT per pixel).

## Next recommended step

**Stage-3 Task 3 — WS-A3 (Cloud LLM judge + sane Sandbox-OFF default, HIGH).** Emit key-gated cloud
providers as judge-eligible in the selection panel; with Sandbox OFF + a cloud key default Run-on →
Hosted + a real judge (never silently Mock); disable LLM judge with a hint when no real judge exists.
See `_SPECS` §WS-A3 and the HANDOFF NEXT TASKS queue.
