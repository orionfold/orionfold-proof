# Worklog — 2026-06-23 · WS-A1 Models-mode Task-instruction field

## Summary
Shipped the first Stage-3 point-task from the approved spec
(`_SPECS/2026-06-22-trustworthy-proof-and-polish.md` §WS-A1): an optional **Task instruction**
textarea in the Proof Run Configure step (Models mode). It sets one `system_prompt` on every selected
candidate via the new `RunRequest.system_prompt` field, so classification/extraction proofs make the
models *classify* rather than "help the user" — the root of the first-real-proof "NO CLEAR WINNER"
experience (issue #4 / feature #1).

The capability was already plumbed end-to-end (`Candidate.system_prompt` → providers → engine →
receipt; it feeds `config_hash` only when set). The only missing link was the **Models-mode entry
path**: `build_candidates()` resolves bare IDs with `system_prompt=None` and `RunRequest` had no field
to carry one. `_resolve_candidates` now copies the instruction onto each base candidate when there are
no `prompt_variants` and the field is non-blank (whitespace-stripped). The Prompts-mode path is
untouched (its per-variant prompt wins).

## Verification (evidence, not claims)
- **New unit tests** `tests/unit/test_resolve_candidates.py` (6): instruction set on every candidate;
  absent/blank → `None`; stripped; prompt-variants path ignores it; config_hash changes only when set.
- **Backend** `uv run pytest` → **281 passed**. Mock matrix `config_hash 467ddd96c9a5` invariant intact.
- **Frontend** `pnpm test` → **121 passed** (2 new RunSetup tests: textarea wires to
  `onModelInstructionChange`; hidden outside Models mode). `pnpm build` (tsc + vite) clean.
- **Real-model end-to-end contrast** (cloud, Sandbox OFF, operator-OK'd cost), support-triage classify,
  exact-match rubric, haiku-4.5 + gpt-5.4-nano:
  - *Without* instruction (`config_hash e00e4b0fb416`): models write helpful prose → **0/5 passes** →
    "NO CLEAR WINNER".
  - *With* instruction (`config_hash 45a2370a09c9`): models emit bare labels → **4/5 passes each**,
    clear winner recommended.
- **Browser** (`http://localhost:5174/`): Task-instruction field renders below the Candidates picker
  in Models mode with the classify placeholder + helper copy + resize handle; correctly **absent** in
  Prompts mode.

## Product impact
Unblocks the demo-critical classification/extraction proof. A cloud-only ICP can now steer the models
to produce gradeable outputs, turning a discouraging "no winner" first run into a clear, trustworthy
proof. This is part 1 of the 3-part WS-A "trustworthy first proof" story (A2 thresholds, A3 cloud
judge remain).

## Risks / notes
- The instruction intentionally becomes part of the proof identity (different `config_hash`). A run
  *without* it stays byte-identical, preserving reproducibility and the mock invariant.
- A1 ships the **raw field only**; the starter-blueprint gallery (Classify/Extract/Summarize presets)
  is deferred per the spec.
- No bundled triage dataset exists yet — the classify verification used an ad-hoc inline example set.
  A bundled label dataset would strengthen WS-B + E2; not in A1 scope.
- Dev-server gotcha recorded in HANDOFF: Vite binds **IPv6 only**, so use `localhost:5174`, not
  `127.0.0.1:5174`.

## Next recommended step
**Task 2 — WS-A2** (per-method default thresholds + Settings sliders). Resolve the settings-persistence
open question first (no app-settings store exists; default to a new `app_settings` SQLite table +
`/api/settings`).
