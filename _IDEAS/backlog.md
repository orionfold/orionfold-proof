# _IDEAS — Backlog (someday / low-priority)

> Long-tail items deliberately **deferred, not fixed**. Each is non-blocking, has a known
> harmless current behavior, and a clear (if minor) future improvement. Promote into a
> `_SPECS/` workstream only when it earns priority. Sibling files: [issues.md](issues.md),
> [feature-opportunities.md](feature-opportunities.md), [design-system.md](design-system.md).

## B1 · Exact rubric shows `≥ 0.8` threshold in the receipt — cosmetic

- **Priority:** Someday / LOW. Cosmetic only; no behavioral impact.
- **Surfaced:** 2026-06-23, during WS-B verification (check-hint → scoring-method mapping).
- **What happens.** When a dataset's check-hint resolves Auto to **Exact** (or the user picks
  the Exact card), the exported receipt prints `Rubric: exact ≥ 0.8 · Scored by: Exact match`.
  The `0.8` is the `Rubric.threshold` *field default* — `"exact"` is intentionally **not** in
  `DEFAULT_THRESHOLDS` (`src/orionfold/scoring/rubric.py`), so `threshold_for("exact")` falls
  back to that field default.
- **Why it's harmless.** Exact is a **binary** check — the scorer returns exactly `1.0` (match)
  or `0.0` (no match). Any threshold in `(0, 1]` yields the *identical* pass/fail partition, so
  `≥ 0.8` and `≥ 1.0` grade the same. (The selectable Exact card already seeds `threshold: 1`;
  only the Auto-resolved path shows `0.8`.) Verified clean in the WS-B e2e run — both candidates
  100% (5/5), zero failures.
- **Possible future polish (pick at most one, only if it earns priority):**
  - Suppress the `≥ N` threshold display in receipts for binary kinds (`exact`/`contains`) —
    print just `Rubric: exact` / `Scored by: Exact match`.
  - Or normalize the Auto-resolved binary-kind threshold to `1.0` so the displayed value reads
    as "must match exactly."
- **⚠ Guardrail if ever touched.** Threshold/numeric-tolerance redesign was **explicitly fenced
  out of WS-B scope** (spec §WS-B "Out of scope"). Any change here must keep the mock matrix
  `config_hash 467ddd96c9a5` unchanged (the mock dataset carries no hint → still keypoint@0.8,
  untouched) and must not alter pass/fail outcomes for existing receipts.
- **Anchors:** `src/orionfold/scoring/rubric.py` (`threshold_for`, `DEFAULT_THRESHOLDS`,
  `default_rubric_for`) · receipt render in `src/orionfold/receipts/export.py` · spec
  `_SPECS/2026-06-22-trustworthy-proof-and-polish.md` §WS-B.

## B2 · Quick→Promote silently drops the prompt — UX seam

- **Priority:** Someday / LOW–MED. Non-blocking; the destination is by-design, only the journey is rough.
- **Surfaced:** 2026-06-23, operator question during WS-C thread. (Previously a one-liner in the
  volatile HANDOFF backlog; persisted here as the durable home.)
- **What happens.** In Quick mode the user types any free-text prompt with **no dataset**. Clicking
  **"Promote to a full scored run →"** runs `onPromote` (`web/src/features/proof/ProofCockpit.tsx:267-270`):
  it `setCompareBy("models")` + `setSelected(...candidates)` — carrying the **2 candidates** but
  **dropping the prompt**, and landing the user in Models mode (dataset-anchored) at an **empty dataset
  picker**. The prompt they cared about vanishes with no explanation or bridge.
- **Why the destination is correct (feature, not bug).** Promote's purpose is to convert a one-off
  eyeball check (`rubric:{kind:"none"}`, `score=None`) into *repeatable scored proof*, which **requires
  a set of examples to score against** — i.e. a dataset. So Promote *must* land somewhere with a
  dataset. The prompt-drop is intentional (was HANDOFF backlog #1, "by design").
- **Why it still feels like a bug.** The transition is silent and lossy: typed prompt → gone; dropped
  into a blank picker; no scaffolding to turn the ad-hoc prompt *into* the proof. Breaks the "calm
  instrument panel" promise at exactly the conversion moment.
- **Possible future improvement (pick when it earns priority):** seed the prompt into a **one-example
  set** so Promote carries candidates **and** prompt, landing on a runnable scored config (prompt =
  example 1) instead of an empty picker. At minimum, a quick honest bridge: a dismissible notice on
  arrival ("Your Quick prompt isn't carried — pick a dataset to score against").
- **⚠ Forks to resolve in a spec before building (two protected invariants).**
  - **Dataset persistence:** ephemeral staged set (like Quick's `Dataset(id="quick-compare")` which
    writes **no** row) vs a written dataset row (then append-only **migration index 6** +
    `is_sample`/metadata handling — see HANDOFF "Datasets metadata" invariant).
  - **Scoring with no expected:** a promoted prompt has no `expected_text`; Quick used `{kind:"none"}`
    but a *scored* run needs a real rubric — prompt the user for the expected answer / keypoint, or
    pick a default. This is the crux that makes it a real product decision, not a mechanical fix.
- **Anchors:** `web/src/features/proof/ProofCockpit.tsx` (`onPromote`, Quick payload ~`:234`) ·
  `QuickCompare.tsx` (promote CTA) · HANDOFF invariants "Quick-Compare" + "Datasets metadata".
