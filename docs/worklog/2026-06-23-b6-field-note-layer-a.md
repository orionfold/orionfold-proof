# Worklog — 2026-06-23 · B6 Proof field-note, Layer A (public export)

## Summary

Shipped **Slice 1** of B6 (the dual-distribution dogfooding artifact), the top of the
merged backlog. Two commits:

- `457baca` — committed the approved spec `_SPECS/2026-06-23-proof-field-notes.md` (written
  + operator-interviewed in the prior session but never committed; it was the lone untracked
  file in the worktree).
- `112776e` — **Layer A: the public field-note export.** `orionfold field-note <run_id>
  [--out note.md]` emits a publish-ready Markdown field note from a stored `ProofReport`:
  - **YAML frontmatter spine** (§4) — `run_id`, `config_hash`, `decision_question`, `dataset`,
    `rubric`, `recommended`, `fmt_check`, `candidates`, `cost_usd`, `tags`. Derived only;
    **hand-rendered** (no `yaml.dump`) so output is byte-deterministic and `import orionfold`
    carries no YAML dependency. `recommended` reads the leaderboard's own `recommended` flag
    (single source of truth — can't disagree with the receipt verdict; reviewer note applied).
    `fmt_check` is true iff `rubric.kind ∈ {exact, contains}` (ADR-0005 §4 format-vs-correctness).
  - **Two inline SVG figures** (`receipts/figures.py`, new) — a cost-vs-quality **Pareto
    scatter** and **pass-rate bars**, pure Python, themeable via `var(--color-*)`, **no
    browser**. The Pareto kernel `_pareto_frontier` is a faithful port of the cockpit's
    `web/.../paretoFrontier.ts` (lower-cost-better; tier-resolved equal-cost ties). DS
    accent/status split held: recommended = the **only** `--color-accent`; bars `--color-ok`;
    other dots status-toned (ok/warn/danger via `_pass_rate_tone`). Deterministic — every
    coordinate routes through `_num()` (fixed 2-dp, trailing-zeros-trimmed). Graceful degrade:
    bars omitted when `rubric.kind == "none"` (a quick/unscored run rolls pass-rate to 0,
    indistinguishable from "scored, all failed" — read the kind, never draw a fake bar); the
    scatter omits its dashed frontier polyline when `<2` frontier points or no cost spread
    (dots still render).
  - **Receipt evidence body** reused verbatim from `export.to_markdown` (its `# Proof Receipt`
    H1 demoted to `## Evidence`) — **never a second copy** of receipt logic.
  - **Narrative stub** (`## Why this can be trusted` + `<!-- author: … -->` markers) — the
    package does **not** author the prose.
  - `build_field_note` graduates to `receipts.__all__` (the CLI is the second consuming use,
    ADR-0004 §7). New `docs/api/receipts.md` documents the public surface.

## Verification

- **366 BE tests** (+22: `tests/unit/test_field_note.py` new + field-note tests in
  `test_cli_workflow.py`).
- `ruff check` + `ruff format` clean; `pyright` 0 errors on changed files.
- **7 `config_hash`/`467ddd96c9a5` freeze tests pass** (mock matrix untouched).
- **19 receipt tests pass** incl. the **byte-identical palette guard** — confirms `export.py`
  is unedited and the protected artifact is unchanged.
- Codegen staleness guard passes.
- **Headless e2e** (real `orionfold run` → `orionfold field-note --out`): frontmatter spine +
  evidence body + `<svg` present; unknown id → exit 1, no traceback; secret scan clean.
- **Fresh-context diff-reviewer: PASS** on all 8 invariants (receipt untouched, no scoring/hash
  path, DS accent/status split, determinism, Pareto port fidelity, graceful degrade, fmt_check,
  secret-free). Two non-blocking notes; the cheaper one (recommended re-derivation) was applied.

## Product impact

Proof now has an **end-user capability** beyond the receipt: a consultant/AI-builder can export
a shareable, evidence-backed write-up of *"why I chose this model for this task"* — repeatable,
hashed, secret-free, with real charts — straight from a run. This is the public half of the
dual-distribution model; it stands alone without our website. It's also the first artifact that
deliberately leaves a human-authored slot (the package emits evidence; the operator/Layer-B skill
writes the narrative).

## Risks

- `_evidence_body` couples to `export.to_markdown`'s exact `# Proof Receipt\n` H1 string; if the
  exporter ever renames its title the demotion silently no-ops (two H1s). Guarded today by
  `test_field_note_has_a_single_h1...`. Acceptable for Slice 1; revisit if the receipt title moves.
- SVG figures are minimal (fixed 320×200 viewBox, no gridlines/ticks beyond axes). Sufficient as
  proof artifacts; richer styling can come when the website collection (downstream) needs it.

## Next recommended step

**Slice 2 — Layer B: the private authoring/publish skill** (`.claude/skills/proof-field-note/`):
scaffold-from-run (figures already in the scaffold via Layer A), open the narrative for the
operator, emit a website-ready bundle for `~/orionfold/website`. **Gated on B7** for the
symlink-into-strategy step — Layer B can be authored privately first, but the symlink lands after
B7 converts `_IDEAS`/`_SPECS` from real dirs to symlinks. Operator picks whether to do B7 first
or author Layer B in parallel. Per spec §8, out of scope (logged, not built): the `·fmt` retrofit
across leaderboard/track-record/receipt, the safe-slice publish surface (ADR-0005 §5), and the
website Astro `proofFieldNotes` collection.
