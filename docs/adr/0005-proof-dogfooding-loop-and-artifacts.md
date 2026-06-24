# ADR 0005: The Proof dogfooding loop & artifact taxonomy (at the trust abstraction)

- **Status:** Accepted (operator-approved 2026-06-23)
- **Date:** 2026-06-23
- **Deciders:** Manav Sehgal (operator) + Claude Code
- **Related:** `docs/adr/0004-dual-distribution-core-shells.md`,
  `docs/adr/0006-distribution-and-licensing.md`,
  `_SPECS/2026-06-23-dual-distribution-findings.md` (§1, §4, §5),
  `docs/release-charter.md`, `_IDEAS/backlog.md` §B6.

## Context

ainative.business runs a **self-propagating dogfooding loop**: a field-note article ends with an
`evidence/` folder of working code → recurring patterns are **lifted into the `fieldkit` package** →
**products** compose those modules → **datasets/models/a book** fall out as side-products; a `papers/`
"Frontier Scout" triages arxiv as the input. The loop's *state machine* is **frontmatter metadata +
deterministic scripts — no LLM coordination**.

The operator sees Proof evolving the same way **but at a different abstraction**. Arena + fieldkit sit at
the **model training/inference** level; their artifacts are byproducts of *that* pipeline (trained/
quantized models, GGUF publishing, training receipts, GPU-sizing papers) and are **DGX-Spark-only** —
every paper eval carries a hardcoded "128 GB envelope" memory budget and a "spark-feasible" verdict.

Proof is a **higher, general abstraction**: *prove which AI option to trust on your own task* —
**cross-device / cross-platform, no GPU/Spark assumption.** So Proof's artifacts must derive from
**Proof's own loop**, not be copied from Arena's training outputs. The loop's *shape* ports; the
*substrate* does not.

## Decision

### 1. Adopt the loop's shape, drop the substrate

Proof runs the same `experiment → evidence → extracted primitive → product → side-product artifact`
cycle, re-grounded at the trust level:

| Loop stage | Arena/fieldkit (training, Spark-only) | **Proof (trust, cross-platform)** |
| --- | --- | --- |
| Experiment | train/quantize/serve a model on the Spark | **run a proof** — compare models/prompts on the user's own task |
| Evidence | `evidence/` rollouts, checkpoints, bench logs | **the proof run + its Proof Receipt** — the receipt *is* the evidence (repeatable, hashed) |
| Extracted primitive | `fieldkit.{nim,rag,eval,training,quant}` | **Proof core** (engine, scoring, providers, receipts, lineage, `track_record`) exposed as a clean lib |
| Product | a Spark-resident appliance | **Proof itself** (package + CLI + cockpit) and published **track-records** |
| Side-product artifacts | datasets (HF), GGUF models, the book | **datasets distilled from real tasks**, **receipts**, **leaderboards / track-records**, **integrity conventions** |
| Feasibility axis | "fits the 128 GB Spark envelope" | **"runs on the providers/devices you actually have"** |
| Triage input | `papers/` Frontier Scout (arxiv → spark-feasible) | **real tasks worth proving** (what decision is a builder actually facing) |

### 2. A Proof "field note / paper" = a curated Proof Receipt + narrative

A field note is **an existing Proof Receipt wrapped in an authored narrative** — the decision, the frozen
dataset, the per-candidate evidence, the verdict, and the `config_hash` — explaining *what was decided
and why it can be trusted*. The **receipt is the evidence** (already Proof's protected, repeatable,
hashed artifact); the narrative is the long-form rationale (the blog half of the loop). This is a *trust*
write-up, not a *training* write-up.

A field note carries **machine-readable frontmatter** (the loop's state-machine spine), e.g. the decision
question, dataset id + hash, rubric kind + threshold, candidate ids, the recommended winner, `run_id`,
`config_hash`, and the providers/devices used (the cross-platform feasibility record). A **CLI command
scaffolds a field note from a `run_id`** — deterministic transform, no LLM (consistent with Proof's
no-LLM `decideInsights` posture and ainative's "deterministic scripts, not LLM coordination" invariant).
The narrative prose is authored by the operator, not generated.

*(This ADR defines the field-note **format**. Building the scaffold command is sequenced after the
ADR-0004 vertical slice.)*

### 3. The cross-platform feasibility axis replaces the memory envelope

Where Arena asks "does this fit the Spark's 128 GB?", Proof asks **"does this run on the providers and
devices the user actually has?"** — provider-agnostic and device-agnostic. Local (Ollama/LM Studio),
cloud (Anthropic/OpenAI/Gemini/OpenRouter), and Mock are equal first-class lanes. No GPU math, no single
resident-lane constraint, no training-pipeline assumption enters Proof's artifacts.

### 4. Port the integrity disciplines from Arena (not the substrate)

Two honesty conventions port directly and extend Proof's existing scorer-honesty line
(demo-scorer-default, B1):

- **The `·fmt` "format check — not correctness" qualifier.** Proof's `exact`/`contains` rubrics are
  format checks (substring/exact-match), exactly like Arena's regex/substring rubrics that earn a `·fmt`
  flag "so a wrong-but-well-formatted answer can't read as 100% quality." Proof flags scores from
  `exact`/`contains` accordingly on leaderboards, track-records, and receipts; `keypoint`/`judge`/
  `similarity` (content-assessing) are not flagged. The mapping reuses the existing `_HINT_KIND`
  taxonomy.
- **Receipts never embed secrets.** The existing secrets-guard posture is reaffirmed as a loop-level
  invariant: any published artifact is secret-free by construction.

### 5. The publish / safe-slice SHARING surface is deferred

Arena's `mirror.py` exports a **scores-only safe-slice** (never prompts/replies), guarded by a sentinel
leak-test. Proof will adopt that **discipline** when it grows a sharing surface, but a `publish` module is
**out of scope for this effort** (no user has asked to share a board yet; local receipt export already
exists). This is a follow-up ADR/effort. The integrity conventions in §4 are landed now so that future
publishing is safe by default.

## Consequences

- **Positive:** Proof gets a coherent artifact taxonomy at its own abstraction; the field-note format
  reuses the already-built receipt (no new artifact engine); the `·fmt` qualifier is a cheap, high-value
  honesty win that strengthens the product's core "numbers that can't flatter themselves" thesis; the
  cross-platform framing is stated as a durable invariant so future features don't drift into Spark/GPU
  assumptions.
- **Negative / trade-offs:** the field-note authoring discipline is partly **cultural** (it needs the
  operator to actually write narratives) — the scaffold command lowers the barrier but can't create the
  habit; defining "what's worth a field note" is judgment, not automation.
- **Follow-ups:** build the field-note scaffold command after the ADR-0004 vertical slice; the safe-slice
  publish surface is a separate future effort; the `·fmt` qualifier lands wherever Proof renders a
  score verdict (leaderboard, track-record, receipt) — coordinate with B4's Track Record screen.

## Alternatives considered

- **Field note = receipt + cross-run track-record + narrative.** Richer, but couples field-note authoring
  to B4's rollup and to having run history. We chose the simpler single-receipt form; a track-record can
  be referenced when relevant without being required.
- **Defer the artifact taxonomy entirely to a later ADR.** Would keep this effort pure plumbing, but the
  operator's refinement (what papers/products/artifacts mean at Proof's abstraction) is the *reason* for
  the pivot — defining it now anchors the cross-platform invariant before features accrete.
- **Copy Arena's artifact types (models, GGUF, training papers).** Rejected — those are training-pipeline
  byproducts on a Spark; Proof sits above training and is cross-platform. Copying them would import the
  exact substrate assumption we must drop.
