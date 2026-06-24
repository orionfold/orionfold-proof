# ADR 0006: Distribution & licensing — mirror fieldkit's model

- **Status:** Accepted (operator-approved 2026-06-23; **Apache-2.0 confirmed by operator**)
- **Date:** 2026-06-23
- **Deciders:** Manav Sehgal (operator) + Claude Code
- **Related:** `docs/adr/0004-dual-distribution-core-shells.md`,
  `docs/adr/0005-proof-dogfooding-loop-and-artifacts.md`,
  `_SPECS/2026-06-23-dual-distribution-findings.md` §1, `_IDEAS/backlog.md` #7 (packaging) / §B6.
- **Note:** this ADR records the **distribution + licensing model**; the **applying** work (writing the
  LICENSE, headers, final PyPI metadata, release script) is backlog #7, sequenced **after** the
  ADR-0004 vertical slice.

## Context

The operator directed that Proof adopt fieldkit + Arena's **canonical distribution and licensing model
verbatim where it fits**. Confirmed from the source:

- **License:** fieldkit is **Apache-2.0** (`fieldkit/LICENSE`).
- **Build:** `hatchling`, dynamic version, single `[project.scripts]` entry — **Proof already uses this
  exact stack** (`pyproject.toml`: hatchling, `orionfold = "orionfold.cli:app"`).
- **Channels:** PyPI wheel (`pip install fieldkit`) **plus** a git-tag subdirectory install for the
  bleeding edge (`pip install "git+…@fieldkit/vX.Y.Z#subdirectory=fieldkit"`).
- **Optional/lazy deps:** heavy surfaces behind extras (`[notebook]`, `[harness]`, `[arena]`, `[rl]`) +
  lazy imports, so `import fieldkit` stays cheap.
- **Release ritual:** offline test suite → git tag → PyPI publish → git+PyPI install-verify, logged in
  `_STATUS.json`; a maintained `CHANGELOG.md`.
- **Structural privacy:** `_GUIDES`/`_SPECS`/`_IDEAS` are private gitignored symlinks — "only released
  code is public"; privacy is structural, not a per-push scrub.

**Current Proof state (audited 2026-06-23):** `pyproject.toml` declares
`license = { text = "Proprietary" }`; there is **no LICENSE file**; a `CHANGELOG.md` already exists;
provider/web deps are all in the **core** dependency list (not yet optional).

## Decision

### 1. License: Apache-2.0 — CONFIRMED by operator (2026-06-23)

Proof adopts **Apache-2.0**, flipping from the current `Proprietary`. The operator confirmed this
explicitly. The rationale: it matches the "open-core local engine" thesis in `docs/opportunity.md`, the
sibling fieldkit/Arena precedent, and the engineer/researcher adoption path that motivates the
dual-distribution model. The flip is irreversible for any version published under it — that is accepted.

The applying work (backlog #7, after the ADR-0004 vertical slice): add a top-level `LICENSE` (Apache-2.0,
"Copyright Orionfold LLC"), set `license = "Apache-2.0"` in `pyproject.toml` (replacing
`license = { text = "Proprietary" }`), and follow fieldkit's posture on headers — rely on the top-level
`LICENSE` rather than per-file headers unless a header is later wanted. **Until #7 lands, `pyproject.toml`
still reads `Proprietary`; the decision is recorded here, the file change is sequenced.**

### 2. Distribution channels

- **PyPI:** publish the wheel as **`orionfold-proof`** (the existing dist name); the CLI command stays
  **`orionfold`**. Target UX: `uv tool install orionfold-proof` → `orionfold up`.
- **Git-tag install** for the bleeding edge, mirroring fieldkit. Proof is its own repo root (not a
  monorepo subdirectory), so the install form is the simpler `pip install
  "git+<repo>@v0.X.Y"` (no `#subdirectory=`). Tags are named `v0.X.Y`.
- **Reserved brands:** keep `orionfold` and `orionfold-arena` reserved on PyPI (placeholders), ship only
  `orionfold-proof` (per the identity memo).

### 3. Optional-deps strategy (ties to ADR-0004 §1)

Move the **web/server stack** (`fastapi`, `uvicorn`, `python-multipart`) behind a `[server]` extra and
**provider SDKs** behind provider extras, keeping the **core** dep set minimal (pydantic, httpx, typer,
the pure-Python dataset importers). `import orionfold` must stay cheap; the cockpit is
`orionfold-proof[server]`. Exact extra names finalized at #7 implementation.

### 4. Release-and-verify ritual

Adopt fieldkit's ritual: **offline test suite green → bump `CHANGELOG.md` → git tag `v0.X.Y` → build +
publish wheel → install-verify from both PyPI and the git tag → record in the handoff/worklog.** Keep the
existing `CHANGELOG.md` as the changelog of record (commit subjects remain the fine-grained log per the
solo-direct-to-main norm). While `0.x`, minor versions may break; `1.0` marks API stability (ADR-0004 §7).

### 5. Structural public/private docs

Proof already separates `docs/` (public-facing) from `_IDEAS/` and `_SPECS/` (working/strategy). Reaffirm
the fieldkit posture: **only released code + public `docs/` ship; strategy/backlog stay private.** No
secret material in any published artifact (reinforced by the secrets-guard hook and ADR-0005 §4).

### 6. PyPI-facing metadata

Mirror fieldkit's `[project]` metadata shape — description, keywords, classifiers (Development Status,
Intended Audience, License, Python versions), project URLs (homepage, source, changelog), authors. The
**exact field values are finalized at #7 implementation** against fieldkit's `pyproject.toml` as the
template (the licensing sub-study's verbatim extraction feeds this); this ADR fixes the *model*, not the
final string values.

## Consequences

- **Positive:** Proof ships on the same proven rails as fieldkit; the build stack already matches (minimal
  churn); a researcher gets a clean `pip install orionfold-proof` lib+CLI with a light core; the release
  ritual is auditable and repeatable.
- **Negative / trade-offs:** the Apache-2.0 flip is irreversible and must be a deliberate operator
  decision (flagged §1); splitting deps into extras adds an install-matrix to test; per-file headers are
  intentionally skipped (a future auditor may want them).
- **Follow-ups (= backlog #7, after the ADR-0004 slice):** write `LICENSE` once Apache-2.0 is confirmed;
  set `license` in `pyproject.toml`; define the extras; finalize PyPI metadata against the fieldkit
  template; script the release-verify; then (backlog #8) git remote + push — still **LAST**, after
  packaging.

## Alternatives considered

- **Keep `Proprietary`.** Contradicts the "open-core" thesis in `docs/opportunity.md` and the fieldkit/
  Arena precedent the operator asked to mirror; closes the engineer/researcher adoption path that
  motivates the whole dual-distribution model. **Rejected — operator confirmed Apache-2.0 (§1).**
- **A copyleft license (GPL/AGPL).** Stronger share-back, but Apache-2.0 matches the sibling products and
  is friendlier to the "plug Proof into your own product" researcher audience. Apache-2.0 preferred.
- **Defer all licensing to #7 with no ADR.** Rejected — the license choice is load-bearing for the
  dual-distribution model and deserves a recorded, separately-supersedable decision now.
