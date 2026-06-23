# 2026-06-22 — `_IDEAS/` → `_SPECS/` pipeline: comprehensive spec written + approved

## Summary

Executed Stages 1+2 of the operator-chosen pipeline. Reviewed all **16 ICP findings** in `_IDEAS/`,
confirmed scope with the operator (**comprehensive — all 16, severity-ordered HIGH→MED→LOW; lightweight
planning, the spec doc is the plan**), re-verified the findings' `file:line` plumbing anchors with **3
parallel read-only agents**, and authored one comprehensive, operator-**approved** specification:
`_SPECS/2026-06-22-trustworthy-proof-and-polish.md` (6 workstreams A–F). Then decomposed it into a
**10-task point-queue** in `HANDOFF.md`. **No product code changed** — spec + breakdown only.

## Verification (evidence)

- **Anchor re-verification** (3 Explore agents, read-only): scoring/threshold/judge plumbing;
  run-config UI surfaces; leaderboard + DS surfaces + reuse-root existence. Caught **3 imprecise
  `_IDEAS` claims** and corrected them in the spec (flagged ⚠):
  - **Judge picker (#6):** not a hardcoded cloud-excluding list — `filterJudgeModels()`
    (`scoring.ts:41-93`) filters `panel.providers` by a `(privacy,tier)` cell; the **default cell
    (Local+Economy) only yields `mock_judge`**. Fix = re-default the cell + emit cloud judges in
    `selection.py`, not "add cloud to a dropdown."
  - **Feature #1 "UI-only":** `system_prompt` is plumbed through providers/engine/receipt, but the
    **Models-mode `RunRequest` doesn't carry it** (`registry.py:133-173`). So it's **UI + a thin
    backend seam** (`RunRequest.system_prompt` + `_resolve_candidates`).
  - **DS Mock badge + dataset metadata:** code already follows the accent/status split; real gaps are
    Mock==Cloud neutral ink (`badges.tsx:19-25`) and the seed not setting `created_at/source/check_hint`
    (`repository.py:112-119`).
- `check_hint` confirmed **display-only today** (`tags.ts:13` "the engine never reads these"); backend
  already has `exact`/`contains` kinds (`models.py:15`, `rubric.py:24-41`) → WS-B maps, doesn't build.
- Reuse roots confirmed to exist: Arena `FrontierScatter.jsx`; ainative `lib/usage/ledger.ts` +
  `components/costs/cost-dashboard.tsx`.

## Operator decisions locked

1. Scope = **all 16 findings**, comprehensive, severity-ordered. Planning = lightweight (spec is the plan).
2. **A2 threshold:** per-method default map (Similarity ~0.55, Keypoint/Judge 0.8) — **and made
   user-configurable as persisted Settings sliders** (later operator add; needs an app-settings
   persistence surface, scoped (a) new `app_settings` table + `/api/settings`, or (b) reuse existing).
3. **WS-B:** add a **selectable Exact card** (not just silent Auto mapping).
4. **WS-C:** **clear-unless-touched** decision question (symmetric to task name).
5. **Sequencing:** strict severity order A→B→C→D→E→F.

## Product impact

Converts the loose 16-finding idea backlog into an approved, anchor-accurate implementation plan whose
HIGH thread (tasks 1–3) directly fixes the demo-blocking "NO CLEAR WINNER" first-real-proof experience.
The spec's corrections prevent ≥2 sessions from being built on wrong assumptions.

## Risks

- **A2 grew scope:** sliders need an app-settings store Orionfold lacks today. Flagged as an Open
  question to resolve at the *start* of Task 2 (quick scoping before coding). Don't let it balloon —
  default to a minimal `app_settings` table + `/api/settings` if no store exists.
- Tasks 1–5 are demo-critical and somewhat coupled (A1→B re-verify; A2→E2 dependency). Keep each
  vertical + independently verifiable; re-verify the triage proof after B.

## Next recommended step

Execute **Task 1 — WS-A1 (Models-mode Task-instruction field)** next session. Read spec §WS-A1 first
(UI + backend seam), TDD the `_resolve_candidates`/`config_hash` behavior, then browser-verify a
classify run scores non-zero. Check the box in `HANDOFF.md` and re-handoff.
