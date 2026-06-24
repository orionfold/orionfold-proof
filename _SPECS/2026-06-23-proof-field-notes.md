# Spec — Proof Field Notes (the dogfooding-loop artifact)

> **Status:** DRAFT for operator approval. No code until approved (CLAUDE.md release gates +
> ceremony gate). This spec is the self-contained handoff: after approval, `/clear` and implement
> the **first slice** in a fresh session.
> **Date:** 2026-06-23 · **Owner:** operator + Claude Code
> **Backlog home:** B6 (dual-distribution core + dogfooding loop), MERGED BACKLOG #1.
> **Ratifies:** ADR-0004 (core/shells), ADR-0005 (dogfooding loop & artifact taxonomy §2 field-note format).
> **Source study:** ainative.business `articles/`, `fieldkit/`, `.claude/skills/` (sync-field-notes,
> fieldkit-curator, hf-publisher); the peer `~/orionfold/website` (Astro) content collections.

---

## 1. What a Proof field note *is*

A **Proof field note = an operator-authored trust narrative wrapped around a real Proof Receipt**, at
Proof's abstraction (which AI option to trust on your own task — cross-platform, no Spark/GPU framing).
It is the direct analogue of an ainative field-note article, re-grounded from *training* to *trust*.

The ainative pattern (verified from source) splits cleanly into four layers, and Proof mirrors each:

| Layer | ainative | **Proof** | Where it lives |
| --- | --- | --- | --- |
| **Measurement** | fieldkit eval/quant → `QuantReport` | a Proof run → `ProofReport` | **public core** (exists ✅) |
| **Artifact card** | `fieldkit.publish` → ModelCard + manifest YAML | `receipts/export.py` → receipt + a new **field-note manifest** | **public core** (receipt ✅; manifest ❌) |
| **Narrative** | operator-authored `article.md` + SVG figures | operator-authored prose + cockpit-chart figures | **operator, by hand** |
| **Sync → publish** | `sync-field-notes` skill → the website | a **private Proof field-note skill** → `~/orionfold/website` | **private skill, gitignored here** |

**The package never authors a narrative. It emits structured, secret-free evidence.** The private skill
turns that evidence into a published article. This is the load-bearing boundary of the whole feature.

---

## 2. The two-layer design (the core decision)

### Layer A — PUBLIC: a receipt-derived field-note export in the package

A new pure core renderer + a thin CLI shell (ADR-0004 §3). **Ships in `orionfold-proof`. End-user
capability.** Secret-free by construction. **No browser dependency, no strategy, no narrative
automation.** `import orionfold` stays cheap (ADR-0004 §1).

`orionfold field-note <run_id> [--out note.md]` emits a single Markdown document:

1. **YAML frontmatter** — the loop's state-machine spine + the cross-platform feasibility record (§4).
2. **A receipt-derived evidence body** — verdict, leaderboard table, per-candidate cost/latency,
   failure cases, `config_hash`, rerun command. Rendered by reusing `build_receipt()` — *not* a second
   copy of receipt logic.
3. **Data tables** (Markdown, GFM, right-aligned numbers, deltas) — the ainative table convention.
4. **Static inline SVG figures generated from the run data** (operator decision, §3) — a Pareto
   cost-vs-quality scatter and pass-rate bars, emitted as self-contained themeable `<svg>` (the actual
   ainative figure convention). Pure Python, no browser. **Figures ship in the package** — the
   standalone end-user export carries real charts, not just tables.
5. **A narrative stub** — `## Why this can be trusted` placeholder for operator prose, plus
   `<!-- author: replace this section -->` markers. The package does **not** fill it.

**Why this is genuinely useful to end users (not just dev tooling):** a consultant/AI-builder can export
a shareable, evidence-backed write-up of *"why I chose this model for this task"* — repeatable, hashed,
secret-free — straight from a run. It stands alone as a product capability, independent of our website.

### Layer B — PRIVATE: the dev-side authoring + publish skill

A skill (`.claude/skills/proof-field-note/`), **symlinked into the strategy folder and gitignored
here** (the B7 pattern — see §7). **Dev-environment only; never bundled or exposed to end users.** It:

1. Calls the public `orionfold field-note` export to get the full scaffold — **figures already
   included** (Layer A emits them as inline SVG, §3).
2. Opens the note for the operator to author the `## Why this can be trusted` narrative (human prose,
   never LLM-generated — consistent with Proof's no-LLM `decideInsights` posture and ainative's
   "deterministic scripts, not LLM coordination" invariant).
3. **Emits a website-ready bundle** matching the Astro content contract (§6) and hands off to
   `~/orionfold/website` for publishing at `orionfold.com/proof/field-notes` (outside this repo's scope).

Because figures are now pure-Python SVG in Layer A, Layer B carries **no browser dependency** — it is
purely the editorial/sync wrapper. (The earlier screenshot approach would have forced figures into
Layer B; the SVG decision keeps Layer B thin.)

---

## 3. Figure strategy (operator decision: static SVG from run data)

Operator chose **static inline SVG generated from the `ProofReport`** (reconsidered from an initial
screenshot idea). Rationale: it is the cleaner architecture *and* the better native look on the Astro
site.

- **Cleaner architecture:** pure Python, **no browser dependency** → figures live in the **public
  package** (Layer A). `import orionfold` stays cheap (ADR-0004 §1). Deterministic: same report →
  byte-identical SVG, forever (testable by string-diff, like the codegen guard).
- **Better look-and-feel on the site:** ainative's own field notes use hand-authored inline SVG
  (`<figure class="fn-diagram">`, gradients, `var(--color-*)` theming, `<figcaption>`, `role="img"` +
  `aria-label`). Inline SVG themes with the site (light/dark), reflows, and reads native — a screenshot
  raster cannot. We match that convention.
- **Trade-off accepted:** we re-implement the chart as a Python SVG string-builder rather than reuse the
  React `FrontierScatter`. The **`paretoFrontier` math already exists** (TS in the cockpit; port the
  kernel, lower-cost-better orientation) — only the SVG *emission* is new.

**Two figures, scoped to the proof story:**
1. **Pareto cost-vs-quality scatter** — cost (x, lower better) × pass-rate (y); frontier path connects
   non-dominated candidates; **recommended candidate is the only accent** (DS accent/status split).
2. **Pass-rate bars** — per-candidate pass-rate, `--color-ok` for the bars (status), neutral ink labels.

Both are emitted as self-contained `<figure><svg>…</svg><figcaption>…</figcaption></figure>` blocks with
CSS-var theming + accessibility attributes, matching the ainative `fn-diagram` shape. **No `<!-- figure
-->` placeholders** — Layer A renders the real figures inline.

*(Quick/unscored runs and no-winner runs degrade gracefully: pass-rate bars omitted when scores are
`None`; the scatter shows dots with no frontier when nothing dominates — honest, never a fake chart.)*

---

## 4. Frontmatter schema (the state-machine spine)

All fields **derived from the `ProofReport`** — none invented. Mirrors ADR-0005 §2 + the cross-platform
feasibility axis (§3 there). Designed to also satisfy the website Astro collection (§6).

```yaml
---
artifact: proof-field-note
title: <operator-set; defaults to the decision question>
date: <run.created_at, date only>
summary: <one-line verdict; operator-editable>
# --- proof provenance (the spine) ---
run_id: <run.id>
config_hash: <run.config_hash>
decision_question: <run.brief.decision_question>
dataset: { id: <run.dataset_id>, name: <run.dataset_name> }
rubric: { kind: <run.rubric.kind>, threshold: <run.rubric.threshold> }
recommended: <winning label, or "no clear winner">
fmt_check: <true iff rubric.kind in {exact, contains}>   # ADR-0005 §4: format check, not correctness
# --- cross-platform feasibility record (ADR-0005 §3) ---
candidates:
  - { label: ..., provider_id: ..., privacy: local|cloud, model: ... }
cost_usd: <report.cost_summary.total_cost_usd>
tags: [proof, <rubric.kind>, ...]   # operator-extendable
---
```

**`fmt_check`** is the one ADR-0005 §4 honesty flag landed here (cheap, in-scope for the field note's
spine). Retrofitting `·fmt` across the live leaderboard/track-record/receipt renders stays a SEPARATE
slice (logged, not built).

---

## 5. Public core surface (Layer A detail)

- **New module:** `src/orionfold/receipts/field_note.py` — `build_field_note(report) -> str`. No DB,
  no HTTP, no browser. Reuses `build_receipt()` for the evidence body.
- **New module:** `src/orionfold/receipts/figures.py` — pure SVG string-builders
  `pareto_svg(report) -> str` and `pass_rate_svg(report) -> str` (the `paretoFrontier` kernel ported
  from the cockpit TS, lower-cost-better). Deterministic; no float-format drift (round/format like the
  codegen renderer so the string-diff test is stable). `build_field_note` composes these.
- **Graduates to `receipts.__all__`** (currently empty) once the CLI consumes it (ADR-0004 §7: a
  second consuming use; here the CLI is that use — graduates immediately on landing).
- **New CLI shell** (~20–30 lines, mirrors `runs show`): `@app.command("field-note")` →
  `get_report` → 404-guard → `build_field_note` → stdout or `--out`. Reuses `_with_conn()`.
- **One `docs/api/receipts.md` card** documenting the public surface.

---

## 6. Website content contract (informational — building it is out of scope)

The peer `~/orionfold/website` (Astro) will publish at `orionfold.com/proof/field-notes`. Its existing
conventions the Layer-B bundle must target:

- Content collections live in `src/content/`; the `story` collection is the closest genre — minimal
  frontmatter (`title`/`date`/`summary`/`tags` + optional `hero`), Markdown body, hero image by
  convention at `src/assets/<collection>/<slug>/hero.png`.
- The `productDetail` schema **already lists `'field-notes'` as a known `sources` type** — the route is
  anticipated. A future `proofFieldNotes` collection will define the strict Zod schema; our frontmatter
  (§4) is a superset that should map cleanly (extra proof-provenance keys are fine).
- The website has its own sync skill pattern (`sync-field-notes`); our Layer-B skill produces the
  bundle, the website consumes it. **No code in the website repo from this effort.**

---

## 7. Privacy / structural invariants

- **Layer B skill is gitignored here** and symlinked into the strategy folder — same as the website
  repo's `_IDEAS -> .../strategy/orionfold-website/_IDEAS` symlink. **Depends on B7** (this repo's
  `_IDEAS`/`_SPECS` are still real dirs, not symlinks). The skill can be authored privately before B7
  lands, but the symlink-into-strategy step is gated on B7.
- **No strategy, skills, or narrative automation in the public package.** Layer A is pure receipt
  derivation.
- **Secret-free by construction** (`.claude/rules/receipts.md`): Layer A reads only a stored
  `ProofReport`; the secrets-guard hook backstops Write/commit.
- **Receipt untouched** — `export.py` is NOT edited; `build_receipt`/`to_markdown` output stays
  byte-identical (palette/HTML guards green). Field note is a *sibling* module, no `RECEIPT_VERSION`
  bump.
- **No scoring/hash path** — read-only over a stored report → mock `config_hash 467ddd96c9a5` untouched
  by construction. No migration, no FE change.

---

## 8. Build sequence (slices — one per session)

Slice 1 is sizeable (SVG renderer + composer + CLI). It MAY be split into 1a/1b if the SVG work runs
long; decide at implementation time.

1. **SLICE 1 (this effort's first build): Layer A public export, figures included.**
   - `figures.py` — `pareto_svg` + `pass_rate_svg` (port `paretoFrontier` kernel; deterministic SVG).
   - `field_note.py` — `build_field_note()` composing frontmatter (§4) + receipt evidence body + data
     tables + the two SVG figures + narrative stub.
   - `orionfold field-note` CLI + `docs/api/receipts.md`.
   - **Tests:** BE unit — frontmatter parses as valid YAML; required keys match the report; `fmt_check`
     true for exact/contains, false otherwise; evidence body present; **both SVGs present + well-formed
     (parse as XML), accent only on recommended, `--color-ok` bars**; deterministic string-diff guard on
     a fixed report (codegen-style); graceful degrade on quick/no-winner; **secret-free assertion** +
     headless e2e (`run → field-note <id>` → frontmatter + body + `<svg`; unknown id → exit 1).
2. **SLICE 2: Layer B authoring skill** (private) — scaffold-from-run (figures already in the scaffold),
   operator-narrative open, website-bundle emit. **No browser dependency** (figures are SVG in Layer A).
   Gated on B7 for the symlink-into-strategy step.
3. **Downstream (not this effort):** the website `proofFieldNotes` Astro collection + route
   (`~/orionfold/website`, operator's other repo).

**Out of scope (logged, not built):** retrofitting `·fmt` across leaderboard/track-record/receipt
renders; the safe-slice publish surface (ADR-0005 §5, deferred); operator narrative prose itself.

---

## 9. Verify (each slice)

ruff + pyright clean · full pytest green · headless e2e · the 8 `467ddd96c9a5` freeze-tests pass ·
receipt HTML byte-identical (palette guard) · fresh-context diff-reviewer. Layer B additionally:
a website-bundle render check against the Astro collection (§6).

---

## 10. Open questions resolved in the interview (2026-06-23)

- **Which B6 strand:** field-note scaffold (operator pick).
- **Ceremony:** spec-first, then `/clear` + implement (operator pick — bigger blast radius than a
  one-file slice).
- **Figures:** static SVG from run data (reconsidered from screenshots) → figures live in Layer A
  (the public package), Layer B stays browser-free (§3).
- **Public/private split:** package emits structured secret-free evidence (end-user capability); the
  authoring/sync/publish skill stays private + gitignored (operator directive).
