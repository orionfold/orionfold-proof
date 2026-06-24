# Worklog — 2026-06-23 · DEFAULT_THRESHOLDS single-source (codegen) + pyright hygiene

## Summary

Two commits this session, picked off the post-Stage-3 deferred backlog (operator chose
the order: pyright hygiene first as a standalone commit, then the DEFAULT_THRESHOLDS slice).

### 1. Pyright hygiene pass (`39b432b`)
Cleared the **9 pre-existing pyright errors** that lived on the clean tree (NOT from recent
work — prior "pyright clean" handoff claims had been inaccurate). All were `float | None` /
`LeaderboardEntry | None` narrowing failures pyright couldn't see through. Behavior-identical:
- `recipes/resolution.py`: extracted `_price_key(row, *, unpriced)` returning a non-None
  `float`, used as the `min(..., key=...)` for all three pick sites (cheapest→0.0, unmet-cloud
  fallback→inf — matching the old inline `... if ... is not None else <fallback>` exactly).
- `receipts/export.py`: `_scored_by` uses `labels.get(kind) or kind`; the verdict/recommendation
  ternaries lifted out of the `build_receipt` dict literal into `if/elif/else` so `top is not None`
  narrows for the `_verdict(top)` / `_recommendation_line(top)` calls.

The tree is now **genuinely pyright-clean (0 errors)** — future claims can be taken at face value.

### 2. DEFAULT_THRESHOLDS single-source via codegen (the deferred §6 slice)
The per-kind default thresholds map `{similarity:0.55, keypoint:0.8, judge:0.8}` was
**hand-mirrored** in `scoring/rubric.py` (canonical) and `web/.../scoring.ts` (TS), held in sync
only by twin freeze-tests. Made Python the single source of truth; the FE now consumes a
**codegen'd** TS module instead of a hand-written literal that could silently drift.

- **NEW `src/orionfold/codegen.py`** — pure `render_thresholds_ts()` renders the TS from the
  canonical Python `DEFAULT_THRESHOLDS` (keys in insertion order; `json.dumps` so `0.8` stays
  `0.8`; TS union type derived from the keys so a new kind flows through without a hand edit);
  `write_generated_files()` writes `web/src/features/proof/thresholds.generated.ts`.
- **NEW `orionfold codegen` CLI command** wires the writer (thin shell, ADR-0004 §3 idiom).
- **`web/.../scoring.ts`** imports `DEFAULT_THRESHOLDS` + `TunableKind` from
  `./thresholds.generated` and re-exports them — every existing import site (`ScoringMethod.tsx`,
  `scoring.test.ts`, …) is unchanged.
- **`web/.../thresholds.generated.ts`** committed (NOT gitignored — the FE builds without a
  codegen prebuild step; the backend test is the drift lock).
- **NEW `tests/unit/test_codegen.py`** — staleness guard asserting the committed file is
  byte-identical to a fresh render (fails CI if `rubric.py` is edited without
  `uv run orionfold codegen`), plus a values test pinning `keypoint: 0.8`.

**Operator decision (AskUserQuestion):** codegen `.generated.ts` over generated JSON or a
twin-maps-with-guard approach — truly single-source, type-checks natively, no JSON-import config.

**Scope:** BE/CLI + a 2-line FE import swap. The Python `DEFAULT_THRESHOLDS` map is byte-for-byte
unchanged — **zero scoring/hash logic touched**.

## Verification

- **342 BE pass** (+2 codegen tests) — incl. the receipt byte-identical HTML/palette guard,
  recipe resolution, and the 8 mock-matrix freeze tests.
- **230 FE pass** — the FE freeze-test (`scoring.test.ts`) now validates the **generated** values.
- **tsc + vite build clean** — proves the generated module resolves, types, and bundles.
- **ruff + pyright: 0 errors** (full tree).
- **Negative test:** temporarily drifted the Python map → the staleness guard **failed** as
  designed → restored (the restore briefly tripped a stale `.pyc`; cleared `__pycache__`,
  re-verified `0.55`/`keypoint=0.8`).
- **Mock-hash invariant:** `keypoint=0.8` confirmed → `467ddd96c9a5` safe; 8/8 freeze tests pass.

## Product impact

Removes a class of silent-drift bug from the proof's scoring defaults: the FE can no longer ship
a threshold that disagrees with the Python core. `orionfold codegen` is the regenerate command;
the committed file keeps the FE build dependency-free. Foundation for future shared constants.

## Risks

- Low. FE consumes a generated artifact; if someone edits `rubric.py` and forgets to regenerate,
  the backend test fails loudly (verified). The generated file is committed, so no build-order
  coupling.
- Watch: a stale `.pyc` can mask an edit to `rubric.py` within a fast edit→import round-trip
  (hit during the negative test). Real runs (`uv run pytest`) recompile correctly; only a
  hand-driven write-then-immediately-import can trip it. Not a product path.

## Next recommended step

Back to the operator-picks backlog (do NOT auto-start). Remaining dual-distribution candidates:
(b) resume the **B4 "Track Record" web screen** (now that `track_record()` is a core fn the
cockpit can render); (c) **B7 private-strategy symlink migration** (blocks #8 git remote);
(d) **#7 packaging** (Apache-2.0 flip + PyPI metadata, BRAINSTORM first). **#8 git remote + push
stays LAST**, gated on #7 AND B7. `main` local-only, all work committed, clean worktree.
