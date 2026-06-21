# 2026-06-21 — Meaning-aware scoring (Finding 2: similarity-rubric weakness)

## Summary

Shipped **meaning-aware scoring** — the last of the three live-review findings from the
decision-recipes run. The v0 default rubric was string-similarity @ 0.8 against the expected prose,
so a **correct** summary in a different format failed (live: a factually complete Markdown table
scored 0.12/Fail). Two scoring methods now join similarity:

- **Keypoint coverage** (deterministic, keyless) — scores the fraction of authored required facts an
  output contains; the **new default** when a dataset carries keypoints. The bundled demo dataset
  ships with keypoints (each a normalized substring of its expected text, so `mock_good` stays a 5/5
  winner), so the keyless demo scores by meaning out of the box.
- **LLM judge** (opt-in) — grades meaning vs `expected_text` 0..1 through a small `Judge` seam that
  reuses the provider boundary (`safe_generate`, inheriting cost estimation **and** secret redaction).
  A keyless deterministic `MockJudge` (`judge_provider_id="mock_judge"`) keeps the suite reproducible.

A full **cost rollup** accounts for every dollar: judge cost is captured per-cell
(`ResultRow.judge_cost_usd`) and rolled into a run-level `RunCostSummary` (candidate · judge · total),
kept **out** of the candidate's own cost and the leaderboard ranking so the recommendation stays
undistorted. The receipt gains a calm **"Scored by"** line and a **"Run cost"** summary across all
three formats (**`RECEIPT_VERSION` 4 → 5**). An in-app **Scoring method** picker (Auto · Keypoint ·
Similarity · LLM judge) reuses the candidate-picker's availability + inline-`KeyEntry` machinery; the
server resolves "Auto" via `default_rubric_for(dataset)` (omit the rubric → keypoint-when-present).

Built brainstorm → spec → plan → subagent-driven (12 tasks, fresh implementer + spec-and-quality
review per task; Task 3 and Task 9 each took one fix loop; Opus whole-branch review + a focused
security/receipt review at the end → two robustness fixes). All on `main` (solo convention; not
pushed — no remote).

## Verification

- `uv run pytest -q` → **200 passed, 0 failures**; `uv run ruff check src tests` → clean.
- `pnpm --dir web test` → **55 passed**; `pnpm --dir web build` → clean (tsc --noEmit + vite).
- Playwright e2e (embed rebuilt) → **4/4**, incl. a new keyless assertion that the cockpit shows
  "Scored by Keypoint coverage" (the Finding-2 proof: a reformatted-but-correct output now passes).
- TDD throughout (RED→GREEN per task under `.superpowers/sdd/`). Per-task reviews all Spec✅/Approved.
  Two fix loops: **Task 3** — the plan's `parse_score` had a `>1`-threshold-vs-`"1.4"→1.0` internal
  contradiction; controller-resolved to an intentional, documented, boundary-tested `>2` (overshoot
  clamps; (2,10]→/10; >10→/100). **Task 9** — the brief's test mock used the wrong `SelectionPanel`
  shape, leaving the cloud-judge-group + `KeyEntry` paths untested; corrected mock + two real branch
  tests + dropped an `as unknown` cast.
- **Final whole-branch review** (Opus, `0f0d39e..c57846e`): **Ready to merge** — all 8 binding
  constraints PASS with file:line evidence (judge cost isolated from candidate cost + leaderboard
  ranking; Finding-1 error-vs-fail ordering preserved; keyless determinism; secrets; `RECEIPT_VERSION`
  exactly 5; intended-only `config_hash` change; Auto-rubric stream threading; Tailwind v4 + contract
  strings). All rolled-up Minors triaged defer.
- **Security + receipt review** (`security-reviewer`): **no secret-leak risk, receipt clean** — judge
  routes entirely through `safe_generate`'s redaction; `Rubric` has no key field; a generated
  `mock_judge` receipt showed `scored_by` "LLM judge · mock-judge-v1", `receipt_version` 5, judge cost
  $0.0009 (9 calls — the errored cell correctly skips the judge), `total == candidate + judge`, and a
  secret scan across all three formats returned **zero** hits. Sample receipts clean.
- **Two final-review fixes** (`ffacb4d`): (1) `ProofReport.cost_summary` got a zeroed `default_factory`
  so an old persisted report (pre-`cost_summary`) reads back instead of 500-ing a stale dev DB; (2) an
  unavailable-but-well-formed judge `provider_id` (e.g. `openai` with no key) now returns **422**, not
  an unhandled 500 (both run endpoints pre-validate the judge, catching `ValueError` + `KeyError`).

## Product impact

The product thesis sharpened: the receipt now measures whether an answer is **right**, not whether it
**matches the reference's phrasing**. A consultant comparing summarizers gets a verdict that rewards
correctness across formats; when phrasing-overlap isn't enough, the LLM judge is one click away and its
cost is shown honestly. "Scored by" makes the basis of trust explicit on every receipt.

## Risks / deferred

- All rolled-up Minors deferred (cosmetic/test-hygiene): vestigial `parse_score` docstring; a couple of
  duplicated test briefs/JSX blocks; an e2e `getByText(/Scored by/i)` that would need scoping only if
  per-candidate scoring labels are ever added. None block merge.
- Catalog price/source accuracy remains a roadmap item (a measured receipt cost always outranks a list
  price downstream). Git remote still unconfigured — all `main` commits are local only.

## Next recommended step

- **#6 prompt-variant candidates** — same model, different system prompt (the next candidate axis;
  composes with the picker + recipes; still text-in/text-out, no new provider machinery).
- Then the **catalog price/source accuracy pass**. Workflows/RAG remain post-v0.
