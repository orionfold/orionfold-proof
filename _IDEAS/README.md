# _IDEAS — Findings from ICP-persona end-to-end visual verification

> A running, evidence-linked backlog produced by walking **Orionfold Proof** through the
> browser as its **Ideal Customer Profile** (AI consultant + small product team), using
> **real models** (no mocks). Findings are grouped into three files. Each is **logged, not
> fixed** in this pass.

## Session

- **Date:** 2026-06-22
- **Build:** orionfold-proof v0.1.0 (live source, `pnpm --dir web dev` → `:5174`; API `:8790`)
- **Mode:** REAL models, **Sandbox OFF** (verified in Settings). No mock providers used.
- **Models (cross-vendor economy trio):** Claude Haiku 4.5 (Anthropic) · GPT-5.4 nano
  (OpenAI) · Llama 3.1 8B Instruct (OpenRouter).
- **Personas:** Pass 1 = AI consultant producing a client-shareable proof (scored arc);
  Pass 2 = small product team running a quick prompt A/B.
- **Design reference compared against:**
  `orionfold-design-system/mocks/design-reference/2026-06-20/{candidate-1,components}.html`.

## Files

| File | Holds |
| --- | --- |
| [issues.md](issues.md) | Bugs, broken states, UX breaks, confusing behavior |
| [feature-opportunities.md](feature-opportunities.md) | Desirability features; each cites a peer-project reuse path + quick-win\|deeper |
| [design-system.md](design-system.md) | Gaps between live UI and the design-system reference / token kit |
| [backlog.md](backlog.md) | Someday / low-priority long-tail items — deferred, not fixed; promote only when prioritized |

## What was verified (works end-to-end on real models)

- Dataset **import → preview → freeze** with real user-pasted JSONL (5 examples, "Exact
  match" hint, source/created metadata persisted).
- Two **real scored matrix runs** (3 cloud candidates × 5 examples = 15 live API calls each)
  across **Anthropic / OpenAI / OpenRouter** — streaming progress, per-candidate bars,
  decision banner, leaderboard, **failure-case browser with real model outputs**.
- A real **Quick ⚡ A/B** (Haiku 4.5 vs GPT-5.4 nano on a release-notes prompt) — objective
  bars (neutral ink), human **pick**, **Save as Proof Receipt**, promote CTA.
- **Receipt export** in **Markdown / HTML / JSON** for scored + quick runs; in-app receipt
  detail view renders faithfully; light + dark themes both clean.
- **Secret hygiene: PASS.** Programmatic scan of MD/HTML/JSON for every exported receipt
  found **no API keys / bearer tokens** despite three real keys in use. The receipt is
  "secret-free" as promised.
- **Provider boundary** (Cloud/Local/Mock) labeled throughout; mocks correctly hidden from the
  run picker with Sandbox OFF.

## Findings index (16)

**Issues (6)** — `med` unless noted
1. (med) Decision question persists stale across a dataset change.
2. (med) Stale decision question is FROZEN into a saved Quick receipt (artifact-level).
3. (med) Dataset "check hint" does not drive the run's Scoring method (taxonomy mismatch).
4. **(high)** REAL-RUN: a classification task scores 0/5 on every model → misleading "NO CLEAR
   WINNER" (no per-task instruction / system prompt).
5. **(high)** REAL-RUN: the flagship demo dataset also reads "NO CLEAR WINNER" with real models
   (default Similarity threshold 0.80 too strict).
6. **(high)** LLM-judge unavailable to a cloud-only user (judge picker excludes cloud
   providers; defaults to Mock even with Sandbox OFF).

**Feature opportunities (5)**
1. **(high, quick-win)** Per-task **instruction / prompt template** — `system_prompt` plumbing
   already exists end-to-end; UI-only add. Unblocks classification/extraction proofs.
2. (med, deeper) **Pareto cost-vs-quality frontier** on the leaderboard — reuse Arena
   `FrontierScatter.jsx`.
3. (med, quick-win) **Run-level cost summary / spend ledger** — reuse ainative
   `lib/usage/*` + `cost-dashboard.tsx` + micro-viz.
4. (med, quick-win) Candidates page **inline "add key / start host"** affordance.
5. (med, deeper) **First-run quick-start / guided first proof** to cut time-to-first-proof.

**Design-system (5)**
1. (low, quick-win) Dataset metadata line inconsistent between bundled and user-created sets.
2. (med, quick-win) Leaderboard headers not sortable (reference `.tbl` defines the pattern).
3. (low, quick-win) Leaderboard column headers use sans `font-medium`, not reference mono
   micro-caps.
4. (low, quick-win) Provider-boundary "Mock" badge styles identically to Local/Cloud.
5. (low, quick-win) Settings & list pages leave the inspector column empty.

## Highest-leverage theme

The three **high** issues compound into one story: **a cloud ICP's first real proof is
steered toward a discouraging "NO CLEAR WINNER."** Classification fails for lack of a task
instruction (#4), free-form summarization fails the too-strict 0.80 Similarity default (#5),
and the one path that would grade fairly — an LLM judge — isn't available to a cloud-only user
(#6). The good news: the **`system_prompt` plumbing already exists** (feature #1 is UI-only),
and the fixes are well-scoped. Landing #1 + a threshold/judge default recalibration would turn
the out-of-box real-model experience from "no winner" into "clear, trustworthy proof."

## Evidence convention

Each entry cites browser screenshot IDs (e.g. `ss_07963zcfs`) captured live during the walk,
plus durable anchors that survive the session: **run IDs** (re-exportable receipts persisted
in `~/.orionfold/proof.db`), **config hashes**, and **source `file:line`** references. Secret
scans were run programmatically against the live `/api/runs/{id}/receipt.{md,html,json}`
endpoints.

## Legend

- **Severity:** `low` · `med` · `high` (impact on the ICP's ability to decide what to trust).
- **Effort:** `quick-win` (drop-in / light-adapt) · `deeper` (multi-day build).
- **Route / State:** which view · which of empty·loading·error·populated · light·dark.
- **Evidence:** screenshot path under the session scratchpad.
- **Reuse source:** concrete peer-project file path when a feature can be adapted.

## Peer-project reuse map (for feature entries)

- **Orionfold Arena** — `/Users/manavsehgal/Developer/ainative-business.github.io/arena-app/`
  (Astro/Preact/uPlot): `FrontierScatter.jsx` (Pareto cost-vs-quality), `LiveLeaderboard.jsx`
  + `sidecar.mjs` (live SSE leaderboard + static snapshot), `lib/arena/leaderboard-format.mjs`
  (formatters), `styles/premium-narrative.css` (share-friendly receipt polish).
- **Orionfold AI Native Platform** — `/Users/manavsehgal/orionfold/ainative/` (Next.js):
  `components/charts/{sparkline,mini-bar,donut-ring}.tsx` (pure-SVG micro-viz),
  `lib/usage/{ledger.ts,pricing-registry.ts}` + `components/costs/cost-dashboard.tsx`
  (multi-provider cost breakdown), `lib/workflows/` (blueprint templates),
  `lib/agents/learned-context.ts` (operator-approved recommendation loop).
