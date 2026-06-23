# 2026-06-23 — WS-D2: Run-level cost ledger panel (Task 8)

## Summary
Added a per-candidate **Run cost** panel beneath the cost-vs-quality scatter on a
populated full run. It surfaces what the leaderboard's "Est. cost" column can't: per-candidate
**judge $**, **token volume** (in / out), each candidate's **share of run spend**, and a
**reconciled run total**. The total equals the verdict banner's existing "Run cost: candidate
$X · judge $Y · total $Z" line — by construction, because both roll up the same `report.results`.

**FE-only**: no backend, no Pydantic model, no migration, no `config_hash` path. The canonical
mock matrix hash `467ddd96c9a5` is untouched (no scoring/hash code touched).

## What changed
- **New pure module** `web/src/features/proof/costLedgerMath.ts` — `buildCostLedger(leaderboard, results)`
  rolls `ResultRow`s up per `candidate_id` (Σ `estimated_cost_usd` → candidate $, Σ `judge_cost_usd`
  → judge $, Σ tokens), computes each candidate's share of the grand total (divide-by-zero-safe on
  a free run), and preserves **leaderboard order** (recommended-first), not result-row order.
  Carries `privacy` through so the view never guesses it.
- **New component** `web/src/features/proof/CostLedger.tsx` — a `Run cost` section (table + reconciled
  `tfoot` total). DS-clean: cost is neither a verdict nor a PASS signal, so the panel uses **only
  neutral ink / panel tokens** — never `--color-accent` (recommended/interactive) or `--color-ok`
  (PASS). Share bar is `--color-ink-muted`; `$`/token figures are `tabular-nums`. `$` to 4 dp to
  match the verdict line; judge "—" when no judge ran; "Free" + a "No spend — local or mock
  providers only" note on a zero-cost run.
- **Mount** `ProofCockpit.tsx` — `<CostLedger report={report} />` in the **full-run** branch only
  (after `<FrontierScatter>`); the quick branch renders `QuickCompare` and does not include it.
- **Playwright** `e2e/playwright/proof.spec.ts` — asserts the panel mounts and a keyless mock run's
  `run-cost-total` reads "Free" (the same zero the verdict line reports).

## File-naming note
Pure module is `costLedgerMath.ts` (NOT `costLedger.ts`) to avoid a macOS case-insensitive
filesystem collision with the component `CostLedger.tsx` — mirroring the existing
`paretoFrontier.ts` / `FrontierScatter.tsx` split.

## Verification
- **Backend:** `uv run pytest` → **298 passed** (unchanged — backend untouched).
- **Frontend:** `pnpm test` → **189 passed** (+11: 6 math + 5 component). `pnpm build`
  (tsc --noEmit + vite) clean.
- **Playwright:** `pnpm exec playwright test` → **11/11 passed** (re-embedded the fresh build into
  the gitignored `src/orionfold/server/static/` for the served app).
- **Real-model browser verification** (live source, real keys, Sandbox OFF, no mocks):
  - 2 Anthropic tiers (Haiku 4.5 + Opus 4.8) on the investment-memo dataset, Auto→Similarity@0.55,
    config `04ffcde784fc`.
  - Panel: Haiku 404/1,237 tok · $0.0066 · 11% share; Opus 554/1,963 tok · $0.0518 · 89% share;
    **Run total 958/3,200 tok · candidate $0.0584 · judge — · total $0.0584**.
  - **Reconciliation gate PASSED:** the verdict line read *"Scored by Similarity · Run cost:
    candidate $0.0584 · judge $0.0000 · total $0.0584"* — matches the panel to the penny.
  - Shares 11% + 89% = 100%; candidate $ rows sum to the total. Judge "—" everywhere (no LLM judge ran).
  - Graded **light + dark** — both readable, correct contrast, no accent/ok misuse, secret-free.
- **Fresh-context diff-reviewer:** CLEAN — sum-reconciliation holds by construction, no DS
  violations, FE-only, full-run-only mount correct, privacy not guessed, tests assert real
  (non-tautological) invariants. No edits required.

## Product impact
The operator can now see **where the money went** on a run, not just the total — which tier drove
the spend (Opus = 89% here), how many tokens each consumed, and whether a judge added cost. The
reconciled total ties the breakdown back to the protected receipt's headline figure, so the cost
story is trustworthy and repeatable.

## Risks / deferrals
- Out of scope per spec (WS-D): historical cross-run cost charts, budget alerts, a standalone
  Costs route. None added.
- `free` uses exact `=== 0` — safe given the only zero-total source is mock/local rows that are
  literally 0; a paid run never coincidentally hits exactly 0.0.

## Next recommended step
**Task 9 — WS-E1 (Candidates inline add-key / start-host affordance, MED).** List known providers
with a quiet "Add key in Settings →" for unconfigured cloud and "Start Ollama / LM Studio" for
local; reuse the selection panel's gated entries. _ref:_ §WS-E1 · feature #4.
