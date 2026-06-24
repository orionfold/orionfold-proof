# ADR 0004: Dual-distribution — a reusable core behind web, CLI, and programmatic shells

- **Status:** Accepted (operator-approved 2026-06-23)
- **Date:** 2026-06-23
- **Deciders:** Manav Sehgal (operator) + Claude Code
- **Related:** `docs/adr/0001-local-first-proof-receipt-architecture.md`,
  `docs/adr/0003-streaming-run-progress.md` (already reserved the batch endpoint "for the CLI,
  programmatic callers"), `docs/adr/0005-proof-dogfooding-loop-and-artifacts.md`,
  `docs/adr/0006-distribution-and-licensing.md`, `_SPECS/2026-06-23-dual-distribution-findings.md`
  (the supporting study), `_IDEAS/backlog.md` §B6 (origin) / §B4 (unblocked by this).

## Context

Proof's chosen distribution is a **CLI + Python package** (`uv tool install orionfold-proof` →
`orionfold up`; PyPI `orionfold-proof`). That creates **two audiences**:

- **Non-technical users** (AI builders, consultants, small teams) → the **web cockpit**.
- **Engineers & researchers** (early adopters) → the **CLI and the package/API**, plugging Proof
  *into their own products and experiments*.

The second audience is **first-class**, not an afterthought. The trigger for this ADR: while
brainstorming a cross-run leaderboard (B4), the reflex was a **frontend-only** rollup. That is wrong
for this product — logic the CLI and programmatic API also need must live in the **reusable core**, not
in React. The web app is **one consumer of a reusable core; the core is the product.**

A code-level audit (`_SPECS/2026-06-23-dual-distribution-findings.md` §3) found Proof is **~80% a clean
library already**: `run_proof()`, `run_matrix()`, `iter_matrix()`, `build_leaderboard()`, and
`receipts/export.py` are pure, server-free callables; FastAPI routes are a thin stitching layer. The
gaps are (a) **no headless workflow CLI** (only `up`/`dev`), (b) **no deliberately curated public API
surface**, and (c) one genuine cross-shell dual-maintenance hot-spot: `DEFAULT_THRESHOLDS`, mirrored in
`scoring/rubric.py` ⇄ `web/.../scoring.ts` and feeding `config_hash`.

The precedent studied is ainative.business's **fieldkit** package: a curated core with a thin Typer CLI,
optional-deps extras, and an API-graduation rule. fieldkit's `eval`/`publish`/`lineage` map almost 1:1
onto Proof's `proof`+`scoring` / `receipts` / `storage`.

## Decision

### 1. One package, optional-deps extras (fieldkit's model)

Keep a **single `orionfold-proof` package**. The **core always installs**: `domain`, `proof`, `scoring`,
`providers`, `receipts`, plus a new `lineage` surface (run/cross-run provenance) and `track_record`
(below). The **web/server stack** (FastAPI, uvicorn, the SQLite-backed cockpit) moves behind a
`[server]` extra; **provider SDKs** move behind extras so `import orionfold` stays cheap. `pip install
orionfold-proof` yields the **library + CLI**; `pip install "orionfold-proof[server]"` adds the cockpit.
No package split in v1 (revisit only if a researcher's "no web deps" need becomes acute).

### 2. A curated public API surface

The root `orionfold/__init__.py` exports only `__version__`. Each public submodule declares its own
`__all__`; consumers import explicitly (`from orionfold.proof import run_proof`,
`from orionfold.receipts import export`). What is **not** in an `__all__` is internal and may change
without notice. The public surface is documented in `docs/api/` cards (one per module), mirroring
fieldkit's `docs/api/*.md`.

### 3. Three shells over one core

The **web cockpit (FastAPI)**, the **Typer CLI**, and the **programmatic Python API** all call the
**same public core functions**. No shell re-implements core logic. Per fieldkit's rule, **each CLI
command is a thin wrapper (~20–30 lines)** over the public API the library already exposes.

### 4. The full headless workflow CLI

The CLI graduates from operational-only (`up`/`dev`) to **workflow-capable**:

- `orionfold run` — dataset + candidates + rubric → run the matrix → emit a `ProofReport` / receipt.
- `orionfold dataset import|list` — import (JSONL/CSV/Markdown/paste) and list datasets headlessly.
- `orionfold receipt export` — render a stored run's receipt to MD/HTML/JSON to stdout/disk.
- `orionfold runs list|show` — inspect run history.
- `orionfold track-record` — the **cross-run rollup** (see §5).

`up`/`dev` remain. The stitching the FastAPI routes already do becomes shared core helpers the CLI and
routes both call (no duplication).

### 5. The B4 cross-run rollup is a CORE function, not a frontend module

The cross-run "Track Record" rollup is implemented as a **pure core function** —
`track_record(reports) -> ...` grouping per `(dataset_id, rubric.kind)` (the comparability rule locked in
the B4 brainstorm) — consumed by **both** `orionfold track-record` (CLI) **and** the web board. This is
the corrected resolution of the B4 pause: the rollup lives where every shell can reach it. The web
"Track Record" screen renders what the core computes; it does not own the computation.

### 6. Single-source the cross-shell constants

`DEFAULT_THRESHOLDS` stops being hand-mirrored. The **Python map is canonical**; the TypeScript map is
**generated from it** (build-time codegen) or the FE **reads a shipped JSON** emitted from the Python
source. Either kills the dual-maintenance hot-spot while preserving the invariant that keypoint stays
`0.8` (so the mock matrix `config_hash 467ddd96c9a5` is untouched). The existing freeze-tests on both
sides remain as guards.

### 7. API-graduation governance

Adopt fieldkit's rule: a primitive graduates to the **public** `__all__` only after a **second consuming
use** (a second CLI command, experiment, or shell). Deferred surfaces ship as **`NotImplementedError`
stubs that lock the name**, not hidden code. While Proof is `0.x`, minor versions may break; `1.0` marks
API stability.

### 8. Build sequence: vertical slice first

After approval, build **one end-to-end CLI path first** — `orionfold run … → receipt` calling the
curated public core — verified headlessly with tests, **then widen** to dataset/runs/track-record, the
threshold single-source, the field-note scaffold (ADR-0005), and packaging (ADR-0006 / backlog #7).

## Consequences

- **Positive:** researchers can drive Proof headlessly and import it as a library; the cockpit, CLI, and
  API never diverge (one core); the threshold dual-maintenance burden is eliminated; the B4 rollup
  becomes reusable everywhere; the architecture matches the proven fieldkit precedent.
- **Positive (safety preserved):** the FE-only invariants that protected `config_hash 467ddd96c9a5`
  still hold — moving the *rollup* to the core touches no scoring/hash path (it reads existing
  `LeaderboardEntry` fields); the threshold single-source keeps keypoint@0.8.
- **Negative / trade-offs:** the CLI is a real new surface needing its own tests + docs; optional-deps
  extras add install-matrix complexity (mitigated by keeping the core dep set small); a curated `__all__`
  imposes discipline on future additions (that's the point).
- **Follow-ups:** the publish/safe-slice **sharing** surface is **deferred** (ADR-0005); packaging +
  licensing land in ADR-0006 / backlog #7, sequenced after the vertical slice; `track_record()` unblocks
  B4's web screen once the core function exists.

## Alternatives considered

- **Split into `orionfold-core` + `orionfold-server`.** Cleanest separation, but two release cadences,
  two changelogs, and cross-package version pinning — too heavy for a solo founder, and fieldkit proves
  one-package-plus-extras is sufficient. Rejected for v1.
- **Defer packaging topology; just add the CLI inside today's package.** Lower risk, but leaves the
  optional-deps boundary undefined and `import orionfold` heavy. We chose to fix the boundary now since
  it's small and shapes everything else.
- **Keep the B4 rollup in the frontend (the original reflex).** The trigger for this whole ADR — it
  strands the cross-run view from the CLI/API audience. Explicitly rejected.
