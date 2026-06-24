# Findings Memo — Dual-Distribution Model & the fieldkit-style Dogfooding Loop

> **Status:** STUDY / DISCUSSION DOCUMENT — its decisions are now ratified in ADRs 0004/0005/0006
> (operator-approved 2026-06-23; Apache-2.0 confirmed). This memo is retained as the supporting study
> behind those ADRs. **No Proof code until the implementation plan (writing-plans) is approved.**
> **Date:** 2026-06-23 · **Source of study:** `/Users/manavsehgal/Developer/ainative-business.github.io`
> (the ainative.business monorepo: fieldkit package, arena-app, articles, papers, dataset-cards,
> products) + a code-level audit of Proof's own `src/orionfold/` and `web/src/`.
> **Backlog home:** `_IDEAS/backlog.md` §B6 (blocks §B4; sequences before packaging #7).

---

## 0. Why this memo exists (the pivot)

While brainstorming B4 (a cross-run models leaderboard), the recommendation was a **frontend-only**
rollup — consistent with Proof's recent FE-only tasks. The operator paused the workstream: that reflex
is **at odds with Proof's chosen distribution**. Proof ships as a **CLI + Python package**
(`uv tool install orionfold-proof` → `orionfold up`; PyPI `orionfold-proof`). Two audiences follow:

- **Non-technical users** (AI builders, consultants, small teams) → the **web cockpit** (one consumer).
- **Engineers & researchers** (early adopters) → the **CLI + package/API**, plugging Proof *into their
  own products and experiments* (a first-class consumer, not an afterthought).

**Implication:** logic reflexively placed in React may belong in the **reusable core** so the CLI and
programmatic API can reach it too. The web app is *one* consumer of a reusable core — **the core is the
product.** The operator points to ainative.business's **fieldkit → arena → field-notes** self-propagating
dogfooding loop as the precedent to adapt, and sees Proof evolving the same way.

---

## 1. How the ainative loop actually works (verified from the public source)

The loop, in the operators' own words (`fieldkit/README.md:3-8`):

> "Every essay in `ai-field-notes` ends with `evidence/` — a folder of working code that produced the
> article's numbers. After 30+ articles the same patterns kept reappearing… `fieldkit` is what those
> `evidence/` folders look like once the boilerplate is lifted into a real package. The blog stays the
> long-form rationale. `fieldkit` is the `pip install`-able surface so you can reproduce — and extend."

**The cycle (4 stages + a triage input):**

```
   papers/ (Frontier Scout)         [INPUT TRIAGE — arxiv → eval.md verdict → promoted_to: article]
        │
        ▼
   articles/<slug>/article.md  +  evidence/   [EXPERIMENT — prose + working code that made the numbers]
        │                                       (frontmatter: stage, series, fieldkit_modules, signature)
        ▼
   pattern recurs across ≥2 articles  ──►  lifted into  fieldkit/src/fieldkit/<module>   [EXTRACT — public API]
        │                                                 (CLI command added for discoverability)
        ▼
   products/<name>/product.md   [PRODUCT — composes ≥1 fieldkit module + a cockpit surface;
        │                        machine-readable build:/features: frontmatter; ships WITH a fieldkit release]
        ▼
   dataset-cards/, models (HF), the book   [SIDE-PRODUCT ARTIFACTS — versioned, licensed, published]
```

**Four governance rules that make it work (all portable):**

1. **API graduation rule.** A primitive graduates to public API only after **"a second consuming article
   before its public API locks"** (`fieldkit/README.md`, `CHANGELOG.md`, `docs/api/training.md`). Deferred
   modules ship as `NotImplementedError` **stubs that lock the surface**, not hidden code.
2. **CLI is a thin wrapper.** Every `fieldkit` CLI command is ~20–30 lines over the *same public API* the
   library exposes — never a second copy of the logic (`fieldkit/src/fieldkit/cli/`).
3. **Optional/lazy deps.** Heavy surfaces live behind extras (`[notebook]`, `[harness]`, `[arena]`,
   `[rl]`) + lazy imports, so `import fieldkit` stays cheap (`pyproject.toml:33-119`).
4. **Privacy is structural, governance is metadata + deterministic scripts.** `_GUIDES`/`_SPECS`/`_IDEAS`
   are private gitignored symlinks ("only released code is public"); the loop's *state machine* is
   frontmatter fields + skills whose `scripts/` do only mechanical transforms — **no LLM coordination**
   (repo `CLAUDE.md`/`AGENTS.md` invariants).

**Distribution + licensing (to adopt verbatim where it fits — satisfies the study half of backlog #7):**
Apache-2.0; `hatchling` build; dynamic version; single `[project.scripts]` entry; PyPI wheel
(`pip install fieldkit`) **plus** git-tag subdirectory install for bleeding edge
(`pip install "git+…@fieldkit/vX.Y.Z#subdirectory=fieldkit"`); maintained `CHANGELOG.md`; a release ritual
(offline test suite → git tag → PyPI → git+PyPI install-verify, logged in `_STATUS.json`).
*(Full pyproject classifiers/metadata extraction pending the package agent's §8 addendum — fold into the
packaging ADR.)*

---

## 2. fieldkit's architecture maps almost 1:1 onto Proof's existing core

| fieldkit module | Purpose | Proof's analog (today) |
| --- | --- | --- |
| `fieldkit.eval` (Bench, Judge, Trajectory, AssertionGrader, PassAtK, rubrics, `is_refusal`) | scoring backbone | `src/orionfold/proof/engine.py` + `scoring/{rubric,judge}.py` — **already present** |
| `fieldkit.publish` (ModelCard, ArtifactManifest, HFHubAdapter, `publish_quant`) | emit publishable artifacts | **MISSING** — `receipts/export.py` is the seed (pure MD/HTML/JSON), but no manifest/card/publish surface |
| `fieldkit.lineage` (append-only Trial TSV, LineageStore, provenance) | run/experiment provenance | `storage/` holds run history as SQLite blobs — **present but not a curated provenance API** |
| `fieldkit.cli` (Typer; thin wrappers over the public API) | headless discoverability | `src/orionfold/cli.py` — **only `up`/`dev` (start servers); NO workflow commands** |
| root `__init__.py` exports only `__version__`; submodules own their `__all__` | curated public surface | **NOT yet curated** — no deliberate public/internal boundary declared |

**Read:** fieldkit has the *same logic shape* Proof already has, plus the **packaged public contract** Proof
lacks (curated `__all__`, thin workflow CLI, optional-deps extras, API-graduation governance, a
publish/lineage surface).

---

## 3. Proof readiness audit — the good news is it's ~80% a clean library already

From a code-level audit of `src/orionfold/` and `web/src/`:

- ✅ **Core is already server-free.** `run_proof()`, `run_matrix()`, `iter_matrix()`, `build_leaderboard()`
  are pure callables taking/returning domain objects (`proof/engine.py`, `proof/leaderboard.py`). FastAPI
  routes are a thin stitching layer (resolve → call core → persist → export), **not** where logic lives.
- ✅ **Receipt export is pure core.** `receipts/export.py` `build_receipt()/to_json()/to_markdown()/to_html()`
  take a `ProofReport`, no DB/HTTP. A researcher can already emit receipts headlessly *in Python*.
- ✅ **Domain models are the single source of truth** (`domain/models.py`: Example, Dataset, Candidate,
  Rubric, ResultRow, LeaderboardEntry, ProofBrief, ProofRun, ProofReport, RunCostSummary).
- ❌ **The CLI is the real gap.** Only `up`/`dev` exist. No `orionfold run` / `dataset import` /
  `receipt export` / `runs list`. A researcher *can* call the library in Python but **cannot drive Proof
  headlessly from the shell** — and the stitching the routes already do is ~80 lines of Typer wrapping.
- ⚠️ **Almost nothing is "trapped" in the frontend.** Every TS pure-logic module
  (`leaderboardSort`, `paretoFrontier`, `costLedgerMath`, `decideInsights`, `briefHelpers`,
  `quickCompareFormat`, picker metadata) is correctly a **cockpit aide**, *not* proof provenance — a
  headless user doesn't need them. **The one genuine dual-maintenance hot-spot is `DEFAULT_THRESHOLDS`**,
  mirrored BE↔FE and test-frozen — and it feeds `config_hash`, so it's the canonical "single-source this"
  case. (`scoring/rubric.py:23-27` ⇄ `web/.../scoring.ts:30-34`.)

**Conclusion:** B6 is **less a rebuild, more a surfacing.** Expose the already-clean core through (a) a real
workflow CLI and (b) a deliberately curated public Python API, then resolve the threshold single-source.
The web cockpit keeps calling the same core the CLI/API call.

---

## 4. What "papers, products, artifacts" mean AT PROOF'S ABSTRACTION (the operator's refinement)

Arena + fieldkit sit at the **model training/inference** level; their artifacts are byproducts of *that*
pipeline (trained/quantized models, GGUF publishing, training receipts, GPU-sizing papers) and are
**DGX-Spark-only**. Proof is a **higher, general abstraction**: *prove which AI option to trust on your own
task* — **cross-device / cross-platform, no GPU/Spark assumption.** So Proof's artifacts derive from
**Proof's own loop**, not Arena's training outputs. The loop *shape* ports; the *substrate* does not.

| Loop element | Arena/fieldkit (training level, Spark-only) | **Proof (trust level, cross-platform)** |
| --- | --- | --- |
| **Experiment** | train/quantize/serve a model on the Spark | **run a proof** — compare models/prompts on the user's own task |
| **Evidence** | `evidence/` runs: rollouts, checkpoints, bench logs | **the proof run's results + the Proof Receipt** (the receipt *is* the evidence — repeatable, hashed) |
| **Field note / paper** | prose + Spark memory-budget eval + GGUF numbers | **a curated receipt + narrative**: the decision, the frozen dataset, per-candidate evidence, the verdict — a *trust* write-up, not a *training* write-up |
| **Extracted primitive** | `fieldkit.{nim,rag,eval,training,quant}` | **Proof core**: run engine, scoring, providers, receipts, cross-run rollup (the same logic, exposed as a clean lib) |
| **Product** | an appliance (model lane + fieldkit + Arena cockpit), Spark-resident | **Proof itself** (package + CLI + cockpit) and **published cross-run track-records** |
| **Side-product artifacts** | datasets (HF), GGUF models, the book | **datasets distilled from real tasks** (B3-style, with cards), **receipts**, **leaderboards / track-records**, **integrity conventions** (`·fmt`) |
| **Feasibility axis** | "fits the 128 GB Spark envelope" / "spark-feasible" | **"runs on the providers/devices you actually have"** — any provider, any device, no GPU/Spark framing |
| **Triage input** | papers/ Frontier Scout (arxiv → spark-feasible) | **real tasks worth proving** (not arxiv) — what decision is a builder actually facing? |

**Overlap with Arena (port the discipline):** comparison + leaderboards; the **`·fmt` "format check — not
correctness"** integrity qualifier (Proof's `exact`/`contains` rubrics are exactly format checks — extends
the scorer-honesty line: demo-scorer-default, B1); the **publishable safe-slice** (export scores, never
prompts/replies — the sentinel leak-test); per-row provenance badges (Local/Cloud/Mock ⇄ Spark/OpenRouter).

**Where Proof generalizes beyond Arena:** provider-agnostic + device-agnostic; the artifact is a **trust
decision**, not a model; no training loop, no GPU envelope, no single-resident-lane constraint; the
"feasibility" question is economic/availability across *the user's* providers, not memory math on one box.

---

## 5. Gap analysis — ambition vs. ainative workflow vs. Proof readiness

| Capability the loop needs | ainative has it | Proof today | Gap / lift |
| --- | --- | --- | --- |
| Reusable core library, server-free | ✅ fieldkit | ✅ core is server-free | **Small** — curate public `__all__`, declare the boundary |
| Headless workflow CLI (thin over the lib) | ✅ `fieldkit run/bench/...` | ❌ only `up`/`dev` | **Medium** — add `run`/`dataset`/`receipt`/`runs` commands (~80–120 LOC) |
| Programmatic Python API (documented, stable) | ✅ `docs/api/*.md` + `__all__` | ⚠️ callable but undocumented/uncurated | **Medium** — public API surface + `docs/api/` cards |
| Optional/lazy heavy deps | ✅ extras + lazy imports | ⚠️ provider SDKs not yet optional | **Small–Medium** — extras for providers; keep `import orionfold` cheap |
| Single-sourced cross-shell constants | ⚠️ (fieldkit is Python-only) | ❌ `DEFAULT_THRESHOLDS` mirrored BE↔FE | **Small** — generate the TS map from the Python source (or ship a JSON the FE reads) |
| Publishable artifact surface (cards/manifests) | ✅ `fieldkit.publish` | ⚠️ `receipts/export.py` is the seed | **Medium** — a Proof `publish`/artifact module (receipt → shareable safe-slice + dataset cards) |
| Provenance/lineage API | ✅ `fieldkit.lineage` | ⚠️ SQLite blobs, no curated API | **Medium** — a `lineage`/history surface (also unblocks B4 cross-run rollup *in the core*) |
| Field-note / paper authoring discipline | ✅ articles + evidence + frontmatter state machine | ❌ none yet | **Larger / cultural** — define Proof's field-note format (curated receipt + narrative) + a deterministic authoring path |
| Safe-slice publish (scores-only, leak-tested) | ✅ `arena/mirror.py` + sentinel test | ❌ none | **Medium** — port the discipline if/when Proof publishes track-records (B4 deferred export) |
| Licensing + release ritual | ✅ Apache-2.0 + PyPI + tag + verify | ⚠️ not yet packaged (backlog #7) | **Medium** — packaging #7, now downstream of this model |

**Net:** the **core is ready**; the lift is **surfacing (CLI + public API + publish/lineage)** and a
**cultural** addition (the field-note authoring discipline). Nothing here demands rewriting the proof
engine — it demands *exposing* it and *publishing* from it.

---

## 6. Open questions for the brainstorm (to be resolved → ADRs)

1. **Core/shell boundary.** Where exactly is the line? Candidate: a `orionfold` core (domain, proof,
   scoring, providers, receipts, lineage, publish) with three shells — FastAPI web, Typer CLI, programmatic
   API — all importing the same public surface. Do we *split the package* (`orionfold-core` vs
   `orionfold-server`) or keep one package with optional `[server]`/`[web]` extras? (fieldkit keeps one
   package + extras — likely the right call for v1.)
2. **CLI surface.** Minimal first cut: `orionfold run`, `dataset import|list`, `receipt export`,
   `runs list|show`. What's the stable contract? Does cross-run rollup (B4) land as a **core function**
   `track_record(reports)` consumed by *both* the CLI (`orionfold track-record`) and the web board? (This
   is the concrete resolution of the B4 "where does the rollup live" question — **the core, not the FE.**)
3. **The threshold single-source.** Generate `scoring.ts`'s map from `scoring/rubric.py` at build time, or
   ship a JSON constant the FE reads at runtime? (Either kills the dual-maintenance hot-spot.)
4. **Proof's field-note / paper format.** Is a "field note" a curated Proof Receipt + narrative
   (decision + frozen dataset + per-candidate evidence + verdict)? What's the deterministic authoring path
   (a CLI command that scaffolds a field-note from a run id)? What's machine-readable frontmatter for it?
5. **The publish/artifact surface.** Does Proof grow a `publish` module (receipt → shareable safe-slice +
   dataset card), reusing Arena's scores-only + sentinel-leak discipline? Sequence vs. B4's deferred export.
6. **API-graduation governance for Proof.** Adopt the "second consuming use before the API locks" rule +
   `NotImplementedError` stubs? What's Proof's equivalent of "a second article" — a second consuming
   command/experiment?
7. **Packaging + licensing (#7, now downstream).** Apply fieldkit's model verbatim: Apache-2.0, PyPI
   `orionfold-proof` + git-tag install, optional-deps, CHANGELOG + release-verify ritual, structural
   public/private docs. Confirm dist name / CLI name / reserved brands (`orionfold`, `orionfold-arena`).
8. **Sequencing.** B6 (this) → ADRs approved → minimal CLI + public API + threshold single-source →
   packaging #7 → *then* B4 cross-run rollup as a core function surfaced in both shells. Does the operator
   want a thin **CLI-first vertical slice** (one `orionfold run` end-to-end) before the broader surface?

---

## 7. Recommendation (for discussion, not decided)

Treat B6 as a **surfacing + publishing** effort, not a rewrite:

- **ADR-A — Dual-distribution architecture:** one `orionfold` package, a curated public core
  (`__all__`-declared), three shells (web/CLI/API) over the same surface, optional-deps extras, the
  threshold single-source, API-graduation governance. The **B4 rollup becomes a core `track_record()`
  function** consumed by both the CLI and the web board (this is the corrected answer to the pause).
- **ADR-B — The Proof dogfooding loop & artifact taxonomy:** define field-note (curated receipt +
  narrative), dataset-card, product, and the cross-platform feasibility axis; port the integrity
  disciplines (`·fmt`, safe-slice) from Arena while dropping the Spark substrate.
- **ADR-C (or fold into #7) — Distribution & licensing:** Apache-2.0 + PyPI + tag + CHANGELOG +
  release-verify ritual + structural public/private split, mirrored from fieldkit.
- **First vertical slice after approval:** a thin `orionfold run … → receipt` CLI path end-to-end (proves
  the core drives headlessly), then widen.

**Keep extending `_IDEAS/backlog.md` as gaps surface** between this ambition, the ainative workflows, and
Proof's readiness (operator directive).
