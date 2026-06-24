# 2026-06-23 — Dual-distribution pivot: ADRs + `orionfold run` vertical slice

## Summary

Operator paused the B4 brainstorm (cross-run leaderboard) on realizing the FE-only rollup reflex
was at odds with Proof's **CLI/package distribution**. Pivoted to the strategic **dual-distribution
model**, studied ainative.business's **fieldkit → arena → field-notes** dogfooding loop deeply
(4 parallel agent studies + direct reads), wrote **ADRs 0004/0005/0006** + an elaborated origin spec,
got operator approval (incl. **Apache-2.0 confirmed**), then implemented the **first vertical slice**:
a headless `orionfold run` command driving the full proof workflow through a new shared core function.

## What shipped (commits)

- `7ee28e7` — ADRs 0004 (dual-distribution architecture), 0005 (dogfooding loop & artifact taxonomy),
  0006 (distribution & licensing); origin-spec section in `docs/opportunity.md`; findings memo
  (`_SPECS/2026-06-23-dual-distribution-findings.md`); B4 paused + B6 added to backlog.
- `58cee89` — the vertical-slice implementation plan.
- `7cb5ef7` — B7 backlog: private-strategy symlink + peer relay mechanism (blocks #8 git remote).
- `3ffe724` — `execute_run()`: pure core run-stitch (`proof/runner.py`).
- `81d5285` — curated `proof` package `__all__` (first deliberate public API surface).
- `cb1dcbf` — `orionfold run` CLI command (+ applies migrations on its own connection — a real gap
  the headless path exposed; the web app applies them at startup).
- `e331896` — route + CLI share `execute_resolved()` (the "one core, two shells" keystone).
- `134e9e5` — `docs/api/proof.md` public-API card.

## Verification

- **Tests:** 319 backend pass (was 309 pre-session + the runner/CLI tests added). Route+integration
  baseline 105 unchanged → no regression. `config_hash 467ddd96c9a5` guard (7 tests) green — mock
  matrix untouched.
- **Lint/type:** ruff clean on all changed files; pyright 0 errors on `runner.py` (the 3 pre-existing
  `export.py`/`resolution.py` baseline errors are unrelated, per prior handoff).
- **Real e2e (keyless, from the shell):** `orionfold run --dataset … --candidates mock_good,mock_bad`
  → full Proof Receipt, verdict "Ship — Mock · good 3/3 (100%)", clear loser `mock_bad` 0/3 with 3
  failure cases; JSON receipt valid (19 keys); persisted to the DB (2 rows); **secret-free** ✓.

## Product impact

Proof now has a **headless workflow path**: a researcher/engineer can drive a full proof → receipt
from the CLI (or the curated Python API), not just the web cockpit. The route and CLI share one core
(`execute_resolved`), proving ADR-0004's architecture on a thin slice. This is the foundation for the
"widen" phase (dataset/runs/track-record commands, threshold single-source) and the dogfooding loop.

## Risks / follow-ups

- **B7 (private-strategy symlink) blocks #8 git remote** — Proof's `_IDEAS`/`_SPECS` are still real
  committed dirs; must migrate to `~/orionfold/strategy/orionfold-proof/` + gitignored symlinks before
  any public push (else strategy content publishes). Full steps + history caveat in backlog §B7.
- **Apache-2.0 flip is recorded, not applied** — `pyproject.toml` still says `Proprietary`; the
  LICENSE + `license=` change is sequenced into packaging #7 (ADR-0006 §1).
- The "widen" CLI surface (`dataset import|list`, `runs list|show`, `track-record`) + the
  threshold single-source are the next slice (ADR-0004 §8).

## Next recommended step

Either (a) **widen the CLI** (next slice of ADR-0004 — dataset/runs/track-record + threshold
single-source), or (b) **B7 private-strategy migration** (unblocks the git remote), or (c) **resume
B4** now that its rollup has a home (`track_record()` core function). Operator picks.
