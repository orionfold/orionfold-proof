# Worklog — 2026-06-23 · WS-D1 Pareto cost-vs-quality scatter (Task 6)

## Summary
Added a cost-vs-quality scatter beneath the leaderboard in the Decide step, so the central
"which candidate is the best trade-off?" decision reads at a glance. X = estimated cost
($, lower is better), Y = pass rate (%). The Pareto frontier connects the non-dominated
candidates; the **recommended** candidate is the only accent.

**Approach decisions (operator-approved):**
- **Standardized on Recharts** for cockpit viz. CLAUDE.md listed Recharts in the intended
  stack but it was never actually installed (the only chart-like UI was the leaderboard's
  CSS-`div` pass-rate bars). Operator chose Recharts over hand-rolled SVG / Nivo / visx,
  weighing the recurring viz pipeline (WS-D2 micro-viz is next) over bundle weight (a
  non-issue for a local-first app). `recharts ^3.9.0` installed; React 19 needed no
  `react-is` override.
- **Reused only the `paretoFrontier()` kernel** from the Arena `FrontierScatter.jsx`, not the
  component — the Arena one is preact + uPlot with GGUF-specific treatment, and its skyline
  assumes *higher-x-is-better* (throughput). Ours is **reoriented** for *lower-cost-is-better*:
  a point is Pareto-optimal iff no other has cost ≤ AND quality ≥ (one strict). Reusing the
  Arena math verbatim would have been silently wrong.
- Y-axis = **pass rate** (the leaderboard's headline metric and what "recommended" is gated on).

**FE-only:** no backend, no migration, no `RECEIPT_VERSION` bump, no `config_hash` touch — pure
display of existing `LeaderboardEntry` data. Mock `config_hash 467ddd96c9a5` untouched by
construction.

### New / changed files
- `web/src/features/proof/paretoFrontier.ts` (new) — pure `paretoFrontier(pts)` (reoriented
  skyline, cost-ascending tier sweep) + `buildScatterPoints(entries)`.
- `web/src/features/proof/FrontierScatter.tsx` (new) — Recharts `<ScatterChart>`; per-point
  color via the v3 `shape` prop (`<CandidateDot>`, NOT deprecated `<Cell>`); recommended =
  only `--color-accent`, others status-toned (`var(--color-x)` everywhere → automatic theming);
  frontier as a dotless `<Scatter>` polyline through cost-sorted frontier points; calm
  empty-state guard under 2 scored candidates.
- `web/src/features/proof/ProofCockpit.tsx` — mounted `<FrontierScatter>` between `<Leaderboard>`
  and `<FailureCases>`.
- `web/src/features/proof/{paretoFrontier,FrontierScatter}.test.*` (new) — 13 tests.
- `e2e/playwright/proof.spec.ts` — added a scatter-mount assertion on the populated run; ALSO
  fixed two **pre-existing WS-C breakages** (last session didn't re-run e2e): proof-loop now
  types the decision question after dataset select (WS-C clears an untouched question on
  dataset change); quick-compare now matches the receipt card by the prompt-derived headline
  (WS-C derives the Quick headline from the prompt, not a carried Models-mode question).

## Verification
- **BE:** `uv run pytest` → 298 passed (unchanged → confirms FE-only).
- **FE:** `pnpm test` → 163 passed (+13). `tsc --noEmit` + `vite build` clean (bundle 785KB /
  231KB gzip — chunk-size warning expected for a charting lib in a local-first app; informational).
- **Playwright:** 11/11 (incl. the new scatter-mount assertion + the two WS-C e2e fixes), against
  the embedded build.
- **Real-browser visual** (Sandbox ON mock run, embedded build): scatter renders beneath the
  leaderboard; recommended point (mock_good, $0 / 100%) is the only accent with a ring;
  failing candidate (mock_bad, 0%) uses status-danger; axes/ink correct; **light + dark both
  themed correctly via semantic tokens, no hardcoded hex**; no secrets on screen.
- **Fresh-context `diff-reviewer`:** correct and faithful, no correctness gaps, FE-only invariant
  holds, DS accent/status split enforced, both e2e fixes verified against the actual WS-C code as
  the documented contract (not papering over a regression). Removed an inert `ZAxis` per its note.

## Product impact
The consultant now sees the cost/quality trade-off as a picture, not just a table — the recommended
candidate sits visibly on the frontier, making "what's worth trusting at what price" immediate.

## Risks
- Recharts adds ~290KB to the bundle (785KB total). Acceptable for a local-first desktop-style
  tool; revisit with code-splitting only if startup feel degrades. Logged as a non-blocking note.
- All-free (mock) runs cluster on the X-axis left edge with an empty cost range — faithful (mocks
  are free); a real-model run spreads across X.

## Next recommended step
**Task 7 — WS-D2 (run-level cost ledger / spend panel, MED).** Reuse ainative
`src/lib/usage/ledger.ts` + `components/costs/cost-dashboard.tsx` + micro-viz
(`sparkline/mini-bar/donut-ring`) — now buildable on the Recharts foundation laid here. Data source:
`RunCostSummary` already on the report. Verify the panel's sums match the verdict banner's "Run cost"
line. _ref:_ spec §WS-D2 · feature #3.
