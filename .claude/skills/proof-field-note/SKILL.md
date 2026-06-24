---
name: proof-field-note
description: Author and publish a Proof field note from a real run — the private (Layer B) authoring/publish wrapper around the public `orionfold field-note` export. Scaffolds a publish-ready Markdown note (frontmatter spine + inline SVG figures + receipt evidence + a narrative stub), opens it for the operator to write the trust narrative by hand, then emits a website-ready bundle targeting the peer website's Astro `story` collection. Use when the user says "make a field note", "write a proof field note", "field note from run <id>", "publish this proof to the website", "turn this run into an article", "scaffold a field note", or "emit the field-note bundle". Dev-only; never bundled or exposed to end users.
---

# Proof field note (Layer B — private authoring + publish)

This skill turns a real Proof run into a published trust narrative. It is the **private,
dev-only** half of the dogfooding loop: the public package ships `orionfold field-note`
(Layer A), which emits structured, secret-free evidence with an **unauthored narrative stub**;
this skill opens that stub for the operator to author and then packages the result for the
website.

> **The package never authors a narrative — the operator does, by hand.** This boundary is
> load-bearing (parent spec `_SPECS/2026-06-23-proof-field-notes.md` §2). The narrative is human
> prose, never LLM-generated — consistent with Proof's no-LLM `decideInsights` posture.

> **B7 deferral (status 2026-06-24):** this skill currently lives as a **real directory** at
> `.claude/skills/proof-field-note/`. Per the spec it will be **symlinked into the strategy
> folder and gitignored here** once B7 (the private-strategy symlink migration) lands — the same
> pattern as the website repo's `_IDEAS` symlink. Do the symlink step as part of B7, not here.
> Until then the skill is authored in-repo. (`scripts/` output under `_field-notes/` is already
> gitignored.)

## Architecture

```
stored ProofReport (DB)
   │  orionfold field-note <run_id>          (Layer A, PUBLIC — already shipped)
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

The skill is **purely the editorial/sync wrapper** — no browser, no scoring, no receipt change,
no package change. It only *consumes* the public CLI. The website's `story` collection accepts
Layer A's frontmatter as-is (it is a superset; extra proof-provenance keys are tolerated), so the
bundle never rewrites frontmatter.

## Workflow

Run all steps from the **repo root** (`_field-notes/` paths are relative to CWD).

### Step 1 — Pick the run

If the user named a run id, use it. Otherwise list recent runs and ask which to write up:

```bash
uv run orionfold runs list
```

A field note is only meaningful for a **scored full run** (a clear or honest-no-winner verdict).
Quick/unscored runs degrade gracefully (Layer A omits the pass-rate bars), but they make a weak
article — prefer a run with a real rubric.

### Step 2 — Scaffold the note

Export Layer A's publish-ready scaffold into the staging dir, keyed by run id (the final slug
isn't known until the title is authored):

```bash
mkdir -p _field-notes/<run_id>
uv run orionfold field-note <run_id> --out _field-notes/<run_id>/article.md
```

The scaffold already contains: the YAML frontmatter spine, two inline SVG figures (Pareto
cost-vs-quality scatter + pass-rate bars), the receipt evidence body, and the
`## Why this can be trusted` **stub** with `<!-- author: replace this section -->` markers.

### Step 3 — Author the narrative (operator, by hand)

Open the note for the operator to write the trust narrative in place of the stub:

```bash
open -a Obsidian _field-notes/<run_id>/article.md
```

(Per the operator's `open-review-markdown-in-obsidian` preference. Fall back to `$EDITOR` if
Obsidian isn't available.)

The operator replaces the stub between the `<!-- author: ... -->` and `<!-- /author -->` markers
with real prose: why this result is worth acting on, what the decision was, and any caveats. They
may also edit `title`/`summary` and add `hero`/`heroAlt` to the frontmatter. **Do not write this
prose for them** — the package's whole posture is that the human authors the trust claim.

### Step 4 — Emit the website-ready bundle

Once the narrative is authored, assemble the bundle:

```bash
python3 .claude/skills/proof-field-note/scripts/emit_bundle.py _field-notes/<run_id>/article.md
```

The helper **refuses** (non-zero exit, no bundle) while the `<!-- author: replace this section -->`
marker is still present — so an unauthored stub can never ship. It also backstops a secret scan
(Layer A is secret-free by construction; this is defense in depth). On success it writes
`_field-notes/<slug>/bundle/`:

- `article.md` — the authored note, verbatim (SVG figures stay **inline** so they theme with the
  site light/dark; no asset extraction).
- `bundle.json` — provenance manifest: `slug`, `target_collection: "story"`, `run_id`,
  `config_hash`, `recommended`, `source_export`, `hero_convention`.
- `hero/README.md` — where to drop the optional hero image.

### Step 5 — Hand off to the website (operator, manual)

The skill does **not** write into `~/orionfold/website` (parent spec §6: no code in the website
repo from this effort). The operator copies the bundle's `article.md` to
`~/orionfold/website/src/content/story/<slug>.md`, drops any hero per `hero/README.md`, and runs
the website's own build/sync. The `bundle.json` records the provenance for that hand-off.

## Verify the skill itself

`emit_bundle.py` has a focused self-test (run directly, not via pytest — this skill is outside the
package suite):

```bash
python3 .claude/skills/proof-field-note/scripts/test_emit_bundle.py
```

Expect `OK -- emit_bundle.py self-test passed (3 cases)`. It covers: marker-present → refuses;
authored → all three bundle files with correct provenance and inline figures; key-shaped token →
secret backstop trips.

## Invariants — do not regress

- **No package change.** This skill only *consumes* `orionfold field-note`. It edits no `src/`, so
  the mock `config_hash 467ddd96c9a5`, the receipt (`export.py`, `RECEIPT_VERSION`), and every
  freeze/palette guard are untouched by construction.
- **Marker guard is load-bearing.** Emit must refuse while the author stub survives. Never weaken
  it to "trust the operator authored it."
- **No frontmatter rewrite.** Layer A's frontmatter is a valid `story` superset; the helper copies
  it verbatim. If the website ever makes `story` `.strict()`, that's a website-side schema change,
  not a reason to strip keys here.
- **Figures stay inline.** Parent spec §3 chose inline SVG so figures theme with the site —
  extracting them to `.svg` files would defeat that.
- **No cross-repo writes.** Emit only to `_field-notes/` (gitignored, this repo). The operator
  syncs to the website by hand.
- **Secret-free.** The backstop scan + the repo's PreToolUse secrets-guard both apply; a bundle
  never ships key material.
