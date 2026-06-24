# Spec — Proof Field Note Layer B (the private authoring/publish skill)

> **Status:** APPROVED for implementation (brainstormed + operator-approved 2026-06-24).
> **Date:** 2026-06-24 · **Owner:** operator + Claude Code
> **Backlog home:** B6 Slice 2 (MERGED BACKLOG #1). Slice 1 (Layer A public export) SHIPPED `112776e`.
> **Parent spec:** `_SPECS/2026-06-23-proof-field-notes.md` §2 (Layer B) + §8 (slice 2).
> **Ratifies:** ADR-0004 (core/shells — the skill is a *consuming use* of the public CLI),
> ADR-0005 (dogfooding loop & artifact taxonomy).
> **Source study (verified this session):** the peer `sync-field-notes` skill
> (`~/Developer/ainative-business.github.io/.claude/skills/sync-field-notes/`); the website
> Astro content contract (`~/orionfold/website/src/content.config.ts`, the `story` collection).

---

## 1. What this slice builds

A single **dev-only skill** at `.claude/skills/proof-field-note/` that wraps the already-shipped
public `orionfold field-note` export (Layer A) with an editorial workflow: **scaffold from a run →
operator authors the trust narrative by hand → emit a website-ready bundle**. The bundle targets the
peer website's Astro `story` collection and is staged (gitignored) in *this* repo; the operator
syncs it into `~/orionfold/website` when ready.

**The package never authors a narrative** (parent spec §2, the load-bearing boundary). This skill is
**purely the editorial/sync wrapper** — no browser, no scoring, no receipt change, no package change.
It only *consumes* the public CLI.

**Out of scope (logged, not built — parent spec §8):** the website `proofFieldNotes` Astro
collection/route (lives in `~/orionfold/website`); the `·fmt` retrofit across
leaderboard/track-record/receipt; the operator's narrative prose itself.

---

## 2. Why Layer A's frontmatter needs no transformation

Verified against `~/orionfold/website/src/content.config.ts`. The closest collection is **`story`**
(parent spec §6 named it), whose schema is:

```
title: string        date: coerce.date     summary: string     tags: string[] (default [])
accent?: string      hero?: image()        heroAlt?: string
```

Layer A already emits frontmatter with `title` / `date` / `summary` / `tags` (a `[proof, <kind>]`
list) **plus** proof-provenance keys (`run_id`, `config_hash`, `decision_question`, `dataset`,
`rubric`, `recommended`, `fmt_check`, `candidates`, `cost_usd`, `artifact`). This is a **clean
superset** of the `story` schema. Astro content collections ignore unknown frontmatter keys unless
the schema is `.strict()` — `story` is not — so the bundle's `article.md` needs **no frontmatter
rewrite**. The only fields the operator adds by hand are the optional `hero`/`heroAlt` (an image is a
human choice). The `productDetail.sources` enum already lists `'field-notes'` as a known type, so the
route is anticipated (parent spec §6 confirmed).

**Consequence:** `emit_bundle.py` copies `article.md` verbatim — it does not parse or rewrite
frontmatter for schema-fit. It only derives the slug from `title` and assembles the bundle layout.

---

## 3. Skill structure

```
.claude/skills/proof-field-note/
├── SKILL.md                    # the procedural workflow (scaffold → author → emit)
└── scripts/
    └── emit_bundle.py          # the one helper: marker guard + bundle assembly + secret backstop
```

Two operations, both driven from `SKILL.md`:

1. **`scaffold <run_id>`** (Claude runs it):
   - `orionfold field-note <run_id> --out _field-notes/<slug-or-run_id>/article.md`
     (slug not yet known at scaffold time — stage under the `run_id` first; `emit` derives the real
     slug from the authored `title`). *Decision: stage under `run_id`, rename/place by slug at emit.*
   - Open the note in Obsidian for authoring (the `open-review-markdown-in-obsidian` memory).
2. **`emit <run_id>`** (Claude runs it after the operator authors):
   - `python3 .claude/skills/proof-field-note/scripts/emit_bundle.py _field-notes/<run_id>/article.md`
   - The helper guards, derives the slug, and writes the bundle.

`SKILL.md` carries a `description:` rich in trigger phrases (mirroring the peer skill) so it activates
on "make a field note", "publish a proof field note", "field note from run …", etc. It documents the
B7 deferral in its header (the skill is a real dir now; the symlink-into-strategy migration is B7).

---

## 4. `emit_bundle.py` — the one helper (pure stdlib, no new deps)

Single CLI: `emit_bundle.py <path-to-scaffold-article.md>`. ~80–110 lines. Behavior, in order:

1. **Read** the scaffold `article.md`.
2. **Marker guard** — if `<!-- author: replace this section -->` is still present, print
   `narrative not authored — write the "## Why this can be trusted" section, then re-run emit` to
   stderr and **exit non-zero**. No bundle is written. *(Load-bearing: an unauthored stub never
   ships.)*
3. **Slug derivation** — parse the frontmatter `title:` (the first `title:` line in the leading
   `---` block), slugify: NFKD-normalize → ASCII → lowercase → non-alphanumerics to `-` → collapse →
   trim. Matches the website's filename-is-slug convention (`<slug>.md` → `/story/<slug>/`). Fall back
   to the run_id-derived dir name if the title is empty.
4. **Provenance extraction** — pull `run_id`, `config_hash`, `recommended` from the frontmatter (for
   `bundle.json`). Simple line scans of the leading `---` block; no YAML dep (consistent with Layer
   A's hand-rendered frontmatter posture).
5. **Secret backstop** — re-scan the full `article.md` for key-shaped patterns
   (`sk-`, `sk-ant-`, `AIza`, long base64-ish bearer tokens). Layer A is secret-free by construction;
   this is defense in depth. Any hit → exit non-zero, no bundle. (The PreToolUse secrets-guard hook
   also backstops any Write.)
6. **Assemble** `_field-notes/<slug>/bundle/`:
   - `article.md` — the authored note, copied verbatim (SVG figures stay **inline** — parent spec §3
     chose inline SVG so figures theme with the site; no asset extraction).
   - `bundle.json` — `{ slug, target_collection: "story", run_id, config_hash, recommended,
     source_export: "orionfold field-note", hero_convention:
     "src/assets/story/<slug>/hero.png" }`.
   - `hero/README.md` — one line: drop `hero.png` here → it lands at
     `src/assets/story/<slug>/hero.png`; add `hero: ../../assets/story/<slug>/hero.png` +
     `heroAlt:` to the frontmatter (the `story` schema's optional image fields).
7. **Print** the bundle path to stderr and a one-line "next: copy into ~/orionfold/website" note.

Idempotent — re-running overwrites the same bundle dir.

---

## 5. Data flow & boundaries

```
stored ProofReport (DB)
   │  orionfold field-note <run_id>          (Layer A, PUBLIC — already shipped 112776e)
   ▼
_field-notes/<run_id>/article.md             (scaffold: frontmatter + figures + evidence + STUB)
   │  ← operator authors "## Why this can be trusted" in Obsidian
   ▼
emit_bundle.py  →  marker guard → slug → secret backstop → assemble
   ▼
_field-notes/<slug>/bundle/{article.md, bundle.json, hero/README.md}   (gitignored)
   │  ← operator copies into ~/orionfold/website when ready (manual, cross-repo)
   ▼
website src/content/story/<slug>.md + src/assets/story/<slug>/hero.png
```

**Boundaries held:**
- `_field-notes/` added to `.gitignore` (staging is local, never committed here).
- **No cross-repo writes** — the skill emits to *this* repo's staging dir; the operator syncs to the
  website (parent spec §6: "no code in the website repo from this effort").
- **B7 deferral** — the skill is a real dir at `.claude/skills/proof-field-note/` now; the
  symlink-into-strategy migration is B7's job (operator decision this session). Noted in the skill
  header + worklog.
- **No package change** — Layer A's `field_note.py` / `figures.py` / CLI are untouched. Mock
  `config_hash 467ddd96c9a5`, the receipt (`export.py`, `RECEIPT_VERSION` 8), and every freeze/palette
  guard are untouched **by construction** — the skill only *consumes* the CLI, it edits no `src/`.

---

## 6. Verification

This is a **dev-only, gitignored skill**, outside the package pytest suite. `emit_bundle.py` still has
real logic (guard, slug, assembly) and gets a focused self-test:

- **`scripts/` self-test** (documented in SKILL.md, run directly — not in the package `tests/`):
  - scaffold-with-marker fixture → asserts non-zero exit + **no** bundle written.
  - authored fixture → asserts `bundle/` has all three files; `bundle.json` carries the right
    `run_id`/`config_hash`/`slug`; the secret scan passes; the figures stayed inline in `article.md`.
  - a fixture carrying a fake `sk-ant-…` token → asserts the secret backstop trips (non-zero, no
    bundle).
- **End-to-end manual:** scaffold from a real stored run (one already exists in
  `~/.orionfold/proof.db`), author a throwaway narrative, emit, confirm the bundle is well-formed and
  the frontmatter still parses as the `story` superset.
- **No package regression:** `ruff` + `pyright` clean on `emit_bundle.py`; the package test count is
  **unchanged at 366 BE** (proves Layer A wasn't touched); receipt HTML byte-identical (palette guard
  not even exercised — no `src/` edit).
- **Fresh-context diff-reviewer** on the slice.

---

## 7. Build sequence (single slice)

1. `.gitignore` — add `_field-notes/`.
2. `.claude/skills/proof-field-note/scripts/emit_bundle.py` — the helper (§4).
3. `.claude/skills/proof-field-note/scripts/test_emit_bundle.py` — the self-test (§6).
4. `.claude/skills/proof-field-note/SKILL.md` — the workflow (§3), trigger-rich `description`,
   B7-deferral note in the header.
5. Verify (§6): self-test green, e2e manual scaffold→author→emit, ruff/pyright on the helper, package
   test count unchanged, diff-reviewer.
6. Worklog entry + HANDOFF refresh.

---

## 8. Open questions — all resolved in the brainstorm (2026-06-24)

- **Skill shape:** SKILL.md + one thin Python helper (not script-suite, not skill-only) — operator pick.
- **Bundle target:** a gitignored staging dir in this repo (`_field-notes/`), operator syncs to the
  website by hand — operator pick (honors parent spec §6's no-website-repo-writes boundary).
- **Narrative flow:** open in Obsidian, **emit refuses while the author marker survives** — operator
  pick (an unauthored stub can never ship).
- **Bundle contents:** `article.md` (verbatim, inline SVG) + `bundle.json` provenance manifest + a
  `hero/README.md` placeholder — operator pick (not asset-extraction, which would defeat inline-SVG
  theming; not bare-md, which loses provenance).
- **B7 dependency:** author the skill in-repo now as a real dir; defer the symlink-into-strategy
  migration to B7 — operator pick.
