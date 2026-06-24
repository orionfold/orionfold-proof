# 2026-06-24 — B6 Slice 2: Layer B field-note authoring/publish skill

## Summary

Shipped **B6 Slice 2 — the "Layer B" private authoring/publish skill** (`bf6ab72`), completing
the dual-distribution dogfooding loop's authoring half. Layer A (the public `orionfold field-note`
export, `112776e`) emits structured secret-free evidence with an **unauthored narrative stub**;
Layer B is the dev-only editorial wrapper that turns that scaffold into a published trust narrative:

> scaffold-from-run → operator authors `## Why this can be trusted` by hand → emit a website-ready
> bundle targeting the peer website's Astro `story` collection.

The skill lives at `.claude/skills/proof-field-note/`. It is **purely the editorial/sync wrapper** —
no browser, no scoring, no receipt change, no package change. It only *consumes* the public CLI.

**Brainstormed + spec-approved this session** (`f228a07`, spec
`_SPECS/2026-06-24-proof-field-note-layer-b-skill.md`), then built + verified.

### What landed
- **`SKILL.md`** — the scaffold → author → emit workflow; trigger-rich `description` (registers as
  an available skill); a header **B7-deferral note** (the skill is a real dir now; the
  symlink-into-strategy migration lands with B7 — operator decision this session).
- **`scripts/emit_bundle.py`** (stdlib only, ~150 lines) — the one helper:
  - **Marker guard**: refuses (non-zero, no bundle) while `<!-- author: replace this section -->`
    survives. Load-bearing — an unauthored stub can never ship.
  - **Slug** from the frontmatter `title` (NFKD→ASCII→lower→hyphenate→trim; empty → parent dir name).
  - **Secret backstop**: 7 regexes that are an **exact mirror** of the repo's secrets-guard hook
    `SECRET_PATTERNS` (defense in depth; Layer A is secret-free by construction).
  - **No frontmatter rewrite**: Layer A's frontmatter is already a valid superset of the `story`
    schema (verified against `~/orionfold/website/src/content.config.ts`) — the helper copies
    `article.md` verbatim, figures stay **inline** (spec §3 chose inline SVG so they theme with the
    site).
  - **Bundle** = `_field-notes/<slug>/bundle/{article.md, bundle.json, hero/README.md}`.
    `bundle.json` carries `slug`/`target_collection:"story"`/`run_id`/`config_hash`/`recommended`/
    `source_export`/`hero_convention`.
- **`scripts/test_emit_bundle.py`** — a self-test (run directly, outside the package pytest suite):
  3 cases — marker refuses; authored assembles all 3 files + correct provenance + inline figures;
  key-shaped token trips the backstop. The fake key is **assembled at runtime** (no key-shaped
  literal in source) because the repo's secrets-guard hook blocks literal keys *and* secret-named
  assignments — the same shapes the helper must catch.
- **`.gitignore`** — `_field-notes/` (scaffolds + bundles are local working artifacts; the operator
  syncs bundles into `~/orionfold/website` by hand — no cross-repo writes from the skill, honoring
  parent spec §6).

## Verification

- **Self-test**: `OK -- emit_bundle.py self-test passed (3 cases)`, exit 0.
- **ruff + pyright** on the helper + test: 0 issues.
- **End-to-end on a real scored run** (`run_0fb312d3a087`, exact-match, Claude Haiku 4.5 5/5 winner):
  scaffolded via `orionfold field-note` (valid `story`-superset frontmatter, `recommended` the only
  `--color-accent` dot, 2 inline SVGs, stub present) → emit **refused** before authoring (no bundle)
  → authored the narrative → emit **succeeded**, slug `sample-support-ticket-triage`, bundle.json
  provenance matched the run exactly, stub gone, figures inline.
- **Secret scan** across the emitted bundle: **0 matches**.
- **`_field-notes/` gitignored** (the bundle won't be committed); `git status` showed only
  `.gitignore` + the skill dir — **no `src/` change**.
- **Package tests: 366 passed, unchanged** — proves Layer A (`field_note.py`/`figures.py`/CLI) was
  untouched.
- **Fresh-context diff-reviewer: "Ship it."** Faithful to the spec, no correctness bugs, no
  invariant violations, no scope creep; all 3 findings minor/informational. Independently confirmed
  the secret patterns mirror the hook and the marker literal is byte-identical to Layer A's stub.

## Product impact

The dogfooding loop is now authoring-complete: a real Proof run can become a publish-ready,
evidence-backed, secret-free trust narrative for the website with one human-authored section. The
public package gains nothing new (Layer A already shipped); this is the dev-side glue that lets the
operator publish proof field notes at `orionfold.com/proof/field-notes` without any website-repo
code from this effort.

## Risks / deferrals

- **B7 symlink deferred** (operator decision): the skill is a real dir; the symlink-into-strategy
  migration is B7's job. Noted in the SKILL.md header.
- **Out of scope (logged, not built — parent spec §8):** the website `proofFieldNotes` Astro
  collection/route (lives in `~/orionfold/website`); the `·fmt` retrofit across
  leaderboard/track-record/receipt; operator prose itself.
- Reviewer's 3 informational notes (unterminated-frontmatter message is generic; `_fm_value` matches
  single-line scalars only — safe given Layer A's fixed contract; both emit lines go to stderr,
  stdout empty) — accepted, no action.

## Next recommended step

Back to the **MERGED BACKLOG** (operator picks; do NOT auto-start). Natural continuations:
**B7** (private-strategy symlink + relay — HIGH, blocks the final git push, and would land the
Layer B symlink in its final home) or **#7 packaging** (downstream of B6). git remote+push stays
LAST, gated on BOTH B6→#7 AND B7.
