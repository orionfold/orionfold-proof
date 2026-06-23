# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-23 · **Stage 3 in progress — Task 6 (WS-D1) DONE + committed (`0f83f9e`).**
A cost(x, lower better) × pass-rate(y) **scatter** now sits beneath the leaderboard in the Decide step:
the Pareto frontier connects the non-dominated candidates, and the **recommended candidate is the only
accent**. **Standardized cockpit viz on Recharts** (operator-approved — it was in CLAUDE.md's stack but
NEVER installed; only chart-UI before was the leaderboard's CSS-div bars). `recharts ^3.9.0` added,
React 19 needed no `react-is` override. **Reused only the `paretoFrontier()` kernel** from Arena's
`FrontierScatter.jsx`, NOT the component (it's preact+uPlot, GGUF-specific, and its skyline assumes
*higher-x-better*); **reoriented** for lower-cost-better (optimal iff no other has cost ≤ AND quality ≥,
one strict). New pure `paretoFrontier.ts` (+`buildScatterPoints`); `FrontierScatter.tsx` uses the
Recharts v3 `shape` prop (NOT deprecated `<Cell>`), recommended = only `--color-accent`, others
status-toned, all `var(--color-x)` → auto-theming, calm empty-state <2 candidates. **FE-only — no
backend/migration/RECEIPT_VERSION/config_hash**; mock `467ddd96c9a5` untouched by construction. Also
fixed **two pre-existing WS-C e2e breakages** in `proof.spec.ts` (last session didn't re-run e2e):
proof-loop types the decision question after dataset-select (untouched clears on change); quick-compare
matches the receipt by the prompt-derived headline — both faithful to WS-C's contract, verified by
diff-reviewer. Verified: **298 BE / 163 FE** (+13), tsc+build clean, **11/11 Playwright**, real-browser
light+dark graded (recommended = only accent, no secrets), fresh-context diff-reviewer faithful + FE-only
(removed an inert ZAxis per its note). **A real-model run during the demo produced fresh evidence** for
the flagship "no winner" issue (3 Anthropic tiers, still 0% pass under the shipped 0.55 Similarity
default, scores 0.06/0.06/0.15 — Opus 2.5× the others; the scatter faithfully showed 3 failing dots,
no accent). Logged to `_IDEAS/issues.md` + `feature-opportunities.md` (`docs(ideas):…` commit) — the
fix is **scorer choice (LLM judge), not threshold**, and WS-E2 must block on it. **That run also
motivated a NEW approved task: a Decide-step insight layer** (`_SPECS/2026-06-23-decide-insight-layer.md`)
— a Pass-rate⇄Avg-score Y-toggle on the scatter + a deterministic plain-English explainer, so a
mismatched-scorer run STILL yields insight (avg-score ranks the candidates even when pass rate is flat).
**Execute Task 7 (NEW insight layer) next session, ahead of WS-D2.** `main` local-only; git remote/push
stay queued LAST until packaging (operator directive)._

## ▶️ START HERE NEXT SESSION — execute task 7 (Decide insight layer) from the NEXT TASKS queue

**Stage 3 is underway: one point-task per session.** Tasks 1–6 are checked off below. Read the
spec before coding. Build smallest slice → verify (tests + browser per CLAUDE.md) → check the box →
re-handoff.

**Next up: Task 7 — Decide-step insight layer (score toggle + explainer, MED, FE-only).** Read
`_SPECS/2026-06-23-decide-insight-layer.md` first (self-contained: names files/interfaces, fences
out-of-scope, ends with a verify). Add a **Pass rate ⇄ Avg score** Y-axis toggle to the WS-D1
`FrontierScatter.tsx` (default stays Pass rate; `buildScatterPoints(entries, metric)` + frontier
recomputes per metric; recommended accent stays tied to `entry.recommended`, NOT the metric leader),
plus a new pure `decideInsights.ts` → `deriveDecideInsight(entries)` deterministic plain-English
explainer rendered beneath the chart (rule-based, NOT an LLM call — free + reproducible; status/ink
tones, never the accent). FE-only — no backend/migration/version/hash. _verify:_ Vitest on
`decideInsights` rule branches + `buildScatterPoints(…,"avg_score")` + toggle/explainer in
`FrontierScatter.test.tsx` + Playwright toggle-to-Avg-score + browser re-run the 3-tier case
(Avg-score spreads Opus above; explainer reads the "0% pass but scores 0.06–0.15 … try LLM judge" line).
_ref:_ `_SPECS/2026-06-23-decide-insight-layer.md`; motivated by the WS-D1 real-run + `_IDEAS` issue #5.

**Then: Task 8 — WS-D2 (Run-level cost ledger / spend panel, MED).** Per-provider tokens + $ and a
run total in the Inspector or under the leaderboard. Reuse ainative
`…/orionfold/ainative/src/lib/usage/ledger.ts` + `src/components/costs/cost-dashboard.tsx` + micro-viz
(`src/components/charts/{sparkline,mini-bar,donut-ring}.tsx`) — **now buildable on the Recharts
foundation laid in WS-D1** (port the micro-viz to Recharts + cockpit semantic tokens; do NOT pull a
second charting lib — see the `charting-library-recharts` memory). Data source: `RunCostSummary` already
on the report (`domain/models.py`); candidate/judge/total already computed by the engine. See spec
§WS-D2. _verify:_ the panel's sums **match the verdict banner's existing "Run cost" line**. _ref:_
§WS-D2 · feature #3.

_WS-D1 committed to `main` as `0f83f9e` (worklog `docs/worklog/2026-06-23-ws-d1-pareto-cost-quality-scatter.md`).
WS-C = `1864b35`; WS-B = `5307ae5`; an unrelated CLAUDE.md self-improvement pass = `1dc3eb1`.
WS-A3 = `9e413d5`, WS-A2 = `f2b7e91`, WS-A1 = `593d346`._

**Bring the app up** (live source, real keys in `.env.local`): API on a free port —
`uv run orionfold dev --port 8790` (health `{"status":"ok","service":"orionfold-proof"}`); UI —
`VITE_DEV_PORT=5174 VITE_API_PROXY=http://127.0.0.1:8790 pnpm --dir web dev` (`:5174`, may land on
`:5175`). ⚠️ **Vite binds IPv6 only** — open `http://localhost:5174/` in the browser, NOT
`http://127.0.0.1:5174/` (the latter errors; the `/api` proxy to `127.0.0.1:8790` is fine). `:8787`
may be an unrelated app whose health is `{"ok":true,...}` — not ours. **Real runs cost money but the
operator has OK'd it; Sandbox stays OFF (no mocks).**

## NEXT TASKS — point queue (from approved `_SPECS/2026-06-22-trustworthy-proof-and-polish.md`)
> One task per session, strict severity order. Read the spec workstream first; build → verify (tests +
> browser) → check the box → re-handoff. Tasks 1–5 are the demo-critical HIGH/MED thread.

- [x] **1 · A1 — Models-mode Task-instruction field** (HIGH) ✅ DONE 2026-06-23 (`593d346`). Optional
  "Task instruction" textarea in Configure (Models mode) sets `RunRequest.system_prompt` on every
  candidate via `_resolve_candidates` (blank/absent → unchanged hashes; mock `467ddd96c9a5` intact).
  Verified on REAL models: triage classify 0/5 without → 4/5 with. 281 BE + 121 FE tests, build,
  browser all green. _new test:_ `tests/unit/test_resolve_candidates.py`. _files touched:_
  `routes.py` (RunRequest + `_resolve_candidates`) · `api.ts` RunRequest · `ProofCockpit.tsx`
  (`modelInstruction` state + payload) · `RunSetup.tsx` (textarea, Models-only) + test.
- [x] **2 · A2 — Per-method default thresholds + Settings sliders** (HIGH) ✅ DONE 2026-06-23
  (uncommitted). Built-in map `DEFAULT_THRESHOLDS {similarity:0.55, keypoint:0.8, judge:0.8}` in
  `scoring/rubric.py` (mirrored in `scoring.ts`) + persisted, user-tunable Settings sliders. **Reused
  the existing `settings` k/v table** (no migration); `default_rubric_for(ds, overrides)` resolves the
  kind's default via map+override; both Auto run-sites pass persisted overrides. Similarity calibration
  note on the method card. 291 BE / 128 FE tests, build, browser all green; mock `467ddd96c9a5` intact
  (keypoint@0.8). _new tests:_ map/threshold_for/override + mock-hash-safety in `test_scoring.py`;
  store round-trip/clamp/partial in `test_settings_and_samples.py`; GET-shape/partial-PUT/override-drives-Auto
  in `test_proof_api.py`; FE map + slider + client tests. _files touched:_ `scoring/rubric.py` ·
  `storage/settings.py` · `server/routes.py` (`SettingsModel`+`SettingsUpdate`, `_read_settings`) ·
  `lib/api.ts` · `scoring.ts` · `ScoringMethod.tsx` · `SettingsView.tsx` (+`ThresholdSliders`).
- [x] **3 · A3 — Cloud LLM judge + sane Sandbox-OFF default** (HIGH) ✅ DONE 2026-06-23 (`9e413d5`).
  **Frontend-only** (selection_panel() already emits key-gated cloud providers — spec's CORRECTION held;
  no backend/migration). New pure `defaultJudgeCell(panel, sandbox)` in `scoring.ts`: Sandbox ON → keyless
  Mock; Sandbox OFF → first cell whose *options* hold a real (non-mock) judge (cloud first, then local;
  cheapest tier first), preferring recommended→latest→first; no real judge + Sandbox OFF → `null`.
  `ScoringMethod.tsx` seeds the judge rubric from it + disables the card w/ hint when null; `JudgeFilter`
  opens axes on the cell; `MethodCard` gained `disabled`. Stale-Mock bug fixed in review (judge commits
  only once `judgeCell` resolves to a real cell — never a guessed `mock_judge`). 291 BE / 136 FE (+8),
  build, browser (real keys, Sandbox OFF → Claude Haiku 4.5 judge, e2e clear winner) all green. _files
  touched:_ `scoring.ts` (`defaultJudgeCell`) · `ScoringMethod.tsx` · `JudgeFilter.tsx` · `MethodCard.tsx`
  + tests.
- [x] **4 · B — check-hint → scoring-method mapping + selectable Exact card** (MED) ✅ DONE 2026-06-23
  (`5307ae5`; recovered after a CC crash left the edits uncommitted). Backend `_HINT_KIND`
  (exact/numeric→`exact`, substring→`contains`) + `default_rubric_for(..., check_hint=)` — hint wins
  over the keypoint heuristic; eyeball/empty stay on the keyless heuristic. Both Auto run-sites pass the
  hint via existing `get_dataset_meta` — **no new check logic, no migration** (kinds already in v0).
  Frontend `resolveAutoKind` mirrors the map; 5-col grid + selectable **Exact** card; Auto card surfaces
  *"From your dataset hint: Exact match → Exact match."* 298 BE / 141 FE tests (+7/+5), build clean, mock
  `467ddd96c9a5` unchanged. Browser (real, Sandbox OFF): triage exact-hint + classify instruction →
  Auto→Exact → both 100% (5/5), zero failures, clear winner; receipt "Scored by: Exact match",
  secret-free. _files touched:_ `scoring/rubric.py` · `routes.py` · `scoring.ts` · `selectionMeta.ts` ·
  `ScoringMethod.tsx` + BE/FE tests. _ref:_ §WS-B · issue #3.
- [x] **5 · C — Decision-question integrity (config + Quick)** (MED) ✅ DONE 2026-06-23 (`1864b35`).
  New `decisionQuestionTouched` (symmetric to `taskNameTouched`): untouched question **clears** on
  dataset change (no dataset→question mapping → placeholder); typed/recipe-selected survives;
  `onSelectRecipe` marks touched. Quick payload derives headline from the prompt via pure
  `quickDecisionHeadline()` (blank → falls back to task_name). **FE-only — no backend/migration/version
  bump**; `decision_question` never in `config_hash` so mock `467ddd96c9a5` intact by construction.
  298 BE / 150 FE (+9), build clean. Browser (real, Sandbox OFF): fresh dataset → empty question;
  recipe question survives switch; Quick run → QuickCompare + persisted brief + exported MD Decision
  line all = the prompt; secret-free. diff-reviewer confirmed faithful. _new files:_ `briefHelpers.ts`
  + `briefHelpers.test.ts`. _files touched:_ `ProofCockpit.tsx` · `ProofCockpit.test.tsx`. _ref:_
  §WS-C · issues #1/#2.
- [x] **6 · D1 — Pareto cost-vs-quality scatter** (MED) ✅ DONE 2026-06-23 (`0f83f9e`). Cost(x, lower
  better) × pass-rate(y) scatter beneath the leaderboard; Pareto frontier connects non-dominated
  candidates; **recommended = only accent**. Standardized cockpit viz on **Recharts** (was in stack,
  never installed; `recharts ^3.9.0`, no `react-is` override). Reused ONLY the `paretoFrontier()` kernel
  from Arena (preact+uPlot, NOT reusable), **reoriented** lower-cost-better. New pure `paretoFrontier.ts`
  (+`buildScatterPoints`); `FrontierScatter.tsx` uses v3 `shape` prop (not `<Cell>`), all `var(--color-x)`.
  **FE-only — no backend/migration/version/config_hash**; mock `467ddd96c9a5` intact. Also fixed 2
  pre-existing WS-C e2e breakages in `proof.spec.ts`. 298 BE / 163 FE (+13), tsc+build clean, 11/11
  Playwright, real-browser light+dark graded, diff-reviewer faithful. _new files:_ `paretoFrontier.ts`
  + `FrontierScatter.tsx` + tests. _files touched:_ `ProofCockpit.tsx` · `proof.spec.ts` · `package.json`.
  _ref:_ §WS-D1 · feature #2.
- [x] **7 · Decide insight layer — score toggle + plain-English explainer** (MED, FE-only) ✅ DONE
  2026-06-23. Pass-rate ⇄ Avg-score Y-toggle on `FrontierScatter.tsx` (default Pass rate;
  `buildScatterPoints(entries, metric)` gained a `ScatterMetric` param — `avg_score` reads `e.avg_score`;
  frontier recomputes per metric; YAxis + tooltip relabel per metric; **recommended accent stays tied to
  `entry.recommended`, NOT the metric leader**) + new pure `decideInsights.ts` `deriveDecideInsight(entries)`
  — deterministic 5-rule explainer beneath the chart (NOT an LLM call; `--color-ok/warn/ink-muted` tones,
  never the accent). FE-only — no backend/migration/version/hash; mock `467ddd96c9a5` untouched by
  construction (no scoring/hash path). **178 FE (+15) / 298 BE (unchanged), tsc + build clean, 11/11
  Playwright** (added toggle+explainer assertions; re-embedded build into the package static dir).
  **Real-model browser verification** (Sandbox OFF, 3 Anthropic tiers, Similarity@0.55, config
  `7f2bed41f3f4`): reproduced the headline case — all 3 at 0% pass, avg Opus 0.20 / Haiku 0.05 / Sonnet
  0.05; Pass-rate view = 3 flat dots no accent, Avg-score view spreads Opus above with the frontier
  drawing; explainer reads *"0% pass, but the scores still rank the field … claude-opus-4-8 leads … try
  the LLM judge or lower the threshold in Settings"* and stays identical across the toggle; light + dark
  graded, secret-free. Fresh-context diff-reviewer: faithful, invariants intact, no bugs. _new files:_
  `decideInsights.ts` + `decideInsights.test.ts`. _files touched:_ `paretoFrontier.ts` (+test) ·
  `FrontierScatter.tsx` (+test) · `proof.spec.ts`. _ref:_ `_SPECS/2026-06-23-decide-insight-layer.md`.
- [ ] **8 · D2 — Run-level cost ledger panel** (MED). Reuse ainative `lib/usage/ledger.ts` +
  `cost-dashboard.tsx` + micro-viz (confirmed exist); per-provider tokens+$ + run total in Inspector.
  Port micro-viz to **Recharts** (no second charting lib). _verify:_ sums match the verdict banner's
  "Run cost" line. _ref:_ §WS-D2 · feature #3.
- [ ] **9 · E1 — Candidates inline add-key / start-host affordance** (MED). List known providers; quiet
  "Add key in Settings →" for unconfigured cloud + "Start Ollama/LM Studio" for local. Reuse the
  selection panel's gated entries. _ref:_ §WS-E1 · feature #4.
- [ ] **10 · E2 — Guided first-run CTA** (MED; **BLOCKED on the scorer-default fix**, not just A2). One-click
  "Run the demo proof on real models" on the empty state → clear-winner receipt in ~30s. ⚠️ Real-run
  evidence (2026-06-23): the bundled summarization demo STILL reads "no winner" under the shipped 0.55
  Similarity default — a CTA landing users on 3 failing dots is worse than the blank form. **Fix the demo
  scorer default (→ LLM judge) FIRST** (see `_IDEAS/issues.md` "REAL-RUN: flagship … NO CLEAR WINNER").
  _ref:_ §WS-E2 · feature #5.
- [ ] **11 · F1–F5 — DS application-consistency pass** (LOW; may split). F1 seed sample dataset
  metadata (`repository.py:112-119`/`sample_data.py:25-29`); F2/F3 leaderboard sortable + mono-microcaps
  headers (`Leaderboard.tsx:26-36`, ref `.tbl`); F4 distinct Mock badge (`badges.tsx:19-25`); F5
  inspector-less route layout (`ViewShell.tsx:16`). _verify:_ `browser-visual-verification` light+dark;
  full-receipt HTML byte-identical (palette test). _ref:_ §WS-F · DS #1–#5.

## 🔭 `_IDEAS/` AT A GLANCE (full detail in `_IDEAS/`)
- **Issues (6):** 3× HIGH — first real proof → "NO CLEAR WINNER": (#4) no per-task instruction →
  classification answers the user instead of classifying; (#5) default Similarity threshold **0.80**
  too strict for real paraphrased summaries (flagship demo also shows "no winner"); (#6) LLM-judge
  unavailable to a cloud-only user (picker excludes cloud providers, defaults to **Mock** even with
  Sandbox OFF). Plus: stale decision question (config + **frozen into a saved Quick receipt**);
  check-hint↔scoring **taxonomy mismatch** (dataset hint {Exact/Contains/Numeric/Eyeball} ≠ run
  methods {Auto/Keypoint/Similarity/LLM judge}).
- **Features (5):** (1) **per-task instruction / prompt template — HIGH, quick-win** (UI-only;
  `system_prompt` already threaded `engine.py:37-39` / `anthropic.py:44` / `openai_compatible.py:57`
  / `gemini.py:39` / `receipts/export.py`, added to `config_hash` only when set); (2) Pareto
  cost-vs-quality frontier (reuse Arena `arena-app/src/components/arena/FrontierScatter.jsx`); (3)
  run-level cost ledger (reuse ainative `src/lib/usage/{ledger,pricing-registry}.ts` +
  `components/costs/cost-dashboard.tsx` + micro-viz); (4) Candidates inline add-key affordance; (5)
  guided first-run quick-start.
- **Design-system (5):** dataset metadata inconsistency (bundled vs user); leaderboard **not
  sortable** + sans (not mono micro-caps) headers vs reference `.tbl`; **Mock** boundary badge not
  visually distinct from Local/Cloud; inspector column empty on list/Settings pages. Token
  FOUNDATION already matches the latest reference (`#14c8c0` cyan, Geist) — these are
  *application-consistency* gaps, not color drift.
- **Peer-reuse roots:** Arena `…/ainative-business.github.io/arena-app/`; AI Native
  `…/orionfold/ainative/`. Reference mocks: `…/orionfold-design-system/mocks/design-reference/2026-06-20/{candidate-1,components}.html`.

## BACKLOG — non-blocking, deferred behind the `_IDEAS`→`_SPECS` pipeline (operator picks)
1. **Quick-Compare promote carries the prompt** — promote pre-fills the 2 candidates but NOT the
   ad-hoc prompt (by design). Future: seed the prompt into a one-example set. **Full diagnosis +
   forks now in `_IDEAS/backlog.md` §B2** (durable home; this line is the volatile pointer).
2. **Stored "Recommended on 0/5"** — some 2026-06-21 stored runs persisted `recommended:true` on a
   0-pass candidate (pre-gate). New runs correct. Optional one-off backfill.
3. **Catalog price/source accuracy pass** — verify list prices + context windows (`current-docs-check`).
4. **Cross-product models×prompts** — N models × M prompts in one run. **Brainstorm FIRST.**
5. **DS-skin polish** — shared token-driven badge/chip/bar kit (now partly captured as DS findings
   in `_IDEAS/design-system.md`); receipt proof-seal stamp.
6. **Richer sample data** — extend `sample_data.py` if onboarding wants it.
7. **Packaging · licensing · distribution** — LICENSE + source headers, PyPI metadata (dist
   `orionfold-proof`, CLI `orionfold`; reserve `orionfold` + `orionfold-arena`),
   `uv tool install orionfold-proof` → `orionfold up`, release notes / demo script. **Scope FIRST.**
8. **git remote + push** — **LAST item; do NOT surface or start until packaging (#7) is done**
   (operator directive). No remote configured; `main` holds all work unpushed.

_Done since last handoff: ICP E2E real-model verification; 16 findings captured to `_IDEAS/`
(no code changes). Several ad-hoc real runs (incl. "no winner") sit in `~/.orionfold/proof.db` —
clear via Settings → data management for a pristine demo state if wanted._

## Key invariants to NOT regress
- **Quick-Compare (new):** `mode`/`chosen_winner` live on `ProofRun` (JSON report blob) ONLY and are
  **EXCLUDED from `config_hash`** (a quick run's hash is identical before/after a pick). The unscored
  rubric `{kind:"none"}` yields `ResultRow.score=None`/`passed=None`; `build_leaderboard` must stay
  `None`-safe (`r.score or 0.0`). Quick runs use an ephemeral `Dataset(id="quick-compare")` — **no
  dataset row written**. `list_runs` hides quick runs with `chosen_winner is None`. Quick receipts
  use objective columns + neutral-ink bars — **never `--color-accent` (interactive) or `--color-ok`
  (PASS)** for the bars; the pick selection legitimately uses the accent (interactive).
- **Receipts archive list (`ReceiptsView.tsx`):** the per-row summary winner is **mode-specific** —
  full runs read `leaderboard.recommended` ("Winner … % … Scored by"); quick runs read
  `run.chosen_winner` resolved against `run.candidates` ("Picked &lt;label&gt;" / "Tie — no clear
  winner"). Do NOT collapse quick runs onto the `recommended` path — nothing is ever recommended in an
  unscored run, so it would always show the wrong "No clear winner".
- **`RECEIPT_VERSION` is now 8.** The quick receipt is the protected artifact's lightweight variant:
  always labeled "QUICK CHECK · not scored proof" + promote CTA; never claims scored proof.
  `_RECEIPT_STYLE` is shared by full + quick HTML (full output must stay byte-identical — guarded by
  the palette-count test in `test_receipts.py`).
- **Leaderboard `$/quality`:** `cost_per_quality` on `LeaderboardEntry` only; never a ranking key.
  Ranking sort key `(_all_errored, -pass_rate, -avg_score, avg_latency_ms,
  total_estimated_cost_usd)`.
- **Datasets metadata:** `tags`/`created_at`/`source`/`check_hint` on the DB row + API `DatasetRow`
  ONLY — never the domain `Dataset`/`Example`. Migrations append-only; next index **6**.
- **Mocks:** bare ids `mock_good`/`mock_bad`; engine labels `Mock · good`/`Mock · bad`; picker groups
  them only when Sandbox is on. Scored mock matrix `config_hash 467ddd96c9a5` unchanged. **Quick-mode
  signal inside a mock = `example.expected_text == ""`** (the keyless ad-hoc prompt): `mock_good` then
  returns `_condense(input_text)` instead of the (empty) expected; `mock_bad` skips its 1-in-5 error.
  **Do NOT regress the scored path** — with a non-empty expected, `mock_good` still echoes it
  byte-identically and `mock_bad` still errors ~1/5 (the "always a failure case" guarantee).
- **Sample detection:** receipts by `run_sample…` id prefix; datasets by the `is_sample` column.
- **The accent/status split (DS skin):** cyan `--color-accent` = the only interactive colour; green
  `--color-ok` = PASS/verified ONLY; semantic-token layer only; light + dark + AA; dark is `@theme`
  default; categorical value tags neutral/squared.
- **Threshold defaults (A2):** per-kind map `DEFAULT_THRESHOLDS {similarity:0.55, keypoint:0.8,
  judge:0.8}` lives in BOTH `scoring/rubric.py` and `web/.../scoring.ts` and **must stay in sync**
  (a test on each side freezes the values). Settings sliders persist `threshold_<kind>` keys in the
  existing `settings` k/v table (NO `app_settings` table, NO migration); the persisted value
  **overrides** the map per kind, the map is the **fallback**. `default_rubric_for(ds, overrides)`
  resolves the kind's default; the resolved threshold feeds `config_hash` (so a tuned value is part of
  the proof, but only for runs started after the change — saved runs are frozen). **Keypoint default
  MUST stay 0.8** — the canonical mock matrix resolves to keypoint@0.8 → `467ddd96c9a5`; changing
  Similarity can't touch it. `PUT /api/settings` is a **partial** update (`SettingsUpdate`): a body
  with only `sandbox_enabled` or only `thresholds` is valid and leaves the other untouched.
- **Judge default (A3):** the LLM-judge selection is driven by pure `defaultJudgeCell(panel, sandbox)`
  in `scoring.ts` — Sandbox ON → keyless `mock_judge` (Local+Cheapest, its invariant home); Sandbox OFF
  → a **real** judge (cloud first, then local Ollama; never silently Mock); no real judge + Sandbox OFF
  → `null` (judge card disabled w/ hint). The judge method **commits only once `judgeCell` resolves to a
  real cell** (`judgeReady = settings loaded && (sandbox || panel loaded)`) — NEVER a guessed
  `mock_judge` (that diverges from the dropdown and grades silently with Mock). `filterJudgeModels`
  still pins `mock_judge` as the Local+Cheapest *picker* default — `defaultJudgeCell` scans cell
  *options* (not `defaultProviderId`) to find a real judge behind that pin. FE-only; mock `config_hash`
  unaffected.
- **Proof Run setup:** shared `WorkflowStep`; `compareBy` is now `"models" | "prompts" | "quick"`;
  decision recipes render only in the Models branch (recipes.json loads at backend startup — restart
  to see edits).
- **Decision-question integrity (WS-C):** pure logic in `web/.../briefHelpers.ts`. The decision
  question follows the dataset until **touched**, but unlike the task name it has no dataset→question
  mapping — so `effectiveDecisionQuestion(q, touched)` returns `""` when untouched (clears to the
  placeholder on dataset change; never carries a question from another dataset). `decisionQuestionTouched`
  is set on user-typing AND on `onSelectRecipe` (a recipe is a deliberate choice that must survive a
  later dataset switch). `DEFAULT_BRIEF.decision_question` is now effectively dead on first paint (always
  suppressed until touched) — harmless, do not "fix" by initializing touched=true. **Quick mode** has no
  dataset to anchor a title: the Quick run payload overrides `brief.decision_question` with
  `quickDecisionHeadline(quickPrompt)` (whitespace-collapsed, trimmed, 120-cap+ellipsis; blank → `""` so
  `QuickCompare.tsx:33` falls back to `task_name`) — NEVER the carried Models-mode question. `decision_question`
  is a **content** field: never in `config_hash`, so this can't touch mock `467ddd96c9a5`. The verdict/quick
  headline reads `report.run.brief` (the frozen run-time brief), so it always reflects what was sent.
- **Cost-vs-quality scatter (WS-D1):** charting is **Recharts** — do NOT add a second charting lib (see
  the `charting-library-recharts` memory). Frontier math is pure `web/.../paretoFrontier.ts`,
  **reoriented for lower-cost-is-better** (a point is Pareto-optimal iff no other has cost ≤ AND
  quality ≥, one strict) — this is the OPPOSITE of Arena's higher-x-better skyline, so don't "simplify"
  it back. `buildScatterPoints` maps `pass_rate`→quality, `total_estimated_cost_usd`→cost.
  `FrontierScatter.tsx` colors dots via the Recharts **v3 `shape` prop** (NOT `<Cell>` — deprecated,
  removed in v4); **recommended = ONLY `--color-accent`**, every other dot uses status tokens
  (ok/warn/danger via `passRateTone`); ALL colors are `var(--color-x)` strings (auto light/dark theming,
  never hardcoded hex). Renders the calm empty-state when <2 scored candidates. FE-only display of
  existing `LeaderboardEntry` data — touches no backend/hash.
- **Decide insight layer (Task 7, planned — `_SPECS/2026-06-23-decide-insight-layer.md`):** when built,
  the scatter Y-toggle must keep **recommended accent tied to `entry.recommended`**, never to whichever
  point leads the *current* metric (a point can top Avg-score yet not be recommended — that disagreement
  is the insight). The explainer is **deterministic rule-based** (`decideInsights.ts`), NEVER an LLM call
  (free + reproducible — the receipt repeatability promise); explainer tones use status/ink tokens, never
  the cyan accent. Default first paint stays Pass rate (WS-D1 behavior). FE-only.

## Paste prompt for the next session
```text
Stage 3 execution, one point-task per session. Tasks 1 (A1, 593d346), 2 (A2, f2b7e91), 3 (A3, 9e413d5),
4 (B, 5307ae5), 5 (C, 1864b35) and 6 (D1, 0f83f9e) are checked off in the HANDOFF NEXT TASKS queue.
WS-A + WS-B + WS-C + WS-D1 done.

▶️ EXECUTE TASK 7 — Decide insight layer (score toggle + plain-English explainer, MED, FE-only; NEW,
ahead of WS-D2). Read _SPECS/2026-06-23-decide-insight-layer.md first (self-contained: names
files/interfaces, fences out-of-scope, ends with a verify). Motivated by the WS-D1 real-run: 3 Anthropic
tiers on the flagship summarization set returned 0% pass for all (scorer mismatch), yet avg-score
(0.06/0.06/0.15) STILL ranked them — Opus 2.5×. Add a Pass-rate ⇄ Avg-score Y-axis toggle to
FrontierScatter.tsx (default Pass rate; buildScatterPoints(entries, metric) + frontier recomputes per
metric; RECOMMENDED ACCENT STAYS TIED TO entry.recommended, not the metric leader) + a new pure
decideInsights.ts deriveDecideInsight(entries) deterministic rule-based explainer beneath the chart
(NOT an LLM call — free + reproducible; status/ink tones, never the accent). FE-only — no
backend/migration/version/hash; Recharts only (no second charting lib). _verify:_ Vitest on
decideInsights branches + buildScatterPoints(…,"avg_score") + toggle/explainer in FrontierScatter.test +
Playwright toggle-to-Avg-score + browser re-run the 3-tier case (Avg-score spreads Opus above; explainer
reads "0% pass but scores 0.06–0.15 … try LLM judge"). Build smallest slice → verify (uv run pytest +
pnpm test + pnpm build + browser per CLAUDE.md) → check the box → re-handoff. _ref:_
_SPECS/2026-06-23-decide-insight-layer.md.

THEN Task 8 — WS-D2 (run-level cost ledger, MED): per-provider tokens+$ + run total, reuse ainative
ledger.ts + cost-dashboard.tsx + micro-viz ported to RECHARTS; sums must match the verdict banner's
"Run cost" line. _ref:_ §WS-D2 · feature #3.

App up (REAL keys in .env.local, Sandbox OFF, no mocks; cost OK'd): API
`uv run orionfold dev --port 8790`; UI `VITE_DEV_PORT=5174 VITE_API_PROXY=http://127.0.0.1:8790
pnpm --dir web dev` (:5174). Ours' health = {"status":"ok",...}; an unrelated :8787 app is {"ok":true}.

BACKLOG (deferred behind the pipeline): quick-promote carries the prompt; stored recommended-on-0/5
backfill; catalog price pass; cross-product models×prompts (BRAINSTORM); richer sample data;
packaging·licensing·distribution (BRAINSTORM); git remote + push — LAST, do NOT surface until
packaging is done (operator directive).

Do NOT regress invariants in HANDOFF.md (Quick-Compare mode/chosen_winner on ProofRun only + EXCLUDED
from config_hash / {kind:"none"} → None score+passed / build_leaderboard None-safe / ephemeral
quick-compare dataset writes no row / list_runs hides un-picked quick / quick receipt v8 + neutral-ink
bars never accent-or-ok / _RECEIPT_STYLE shared full HTML byte-identical; leaderboard $/quality on
LeaderboardEntry only never a ranking key; datasets metadata DB+API-only; append-only migrations next
index 6; mock bare-ids + config_hash 467ddd96c9a5; DS accent/status split; compareBy now
models|prompts|quick; A2 threshold map {similarity:0.55,keypoint:0.8,judge:0.8} synced BE↔FE +
keypoint MUST stay 0.8 to keep 467ddd96c9a5, sliders persist in the existing settings table,
PUT /api/settings is partial; A3 judge default = pure defaultJudgeCell(panel,sandbox) — Sandbox ON →
keyless mock_judge, Sandbox OFF → real judge never silently Mock, no-judge+Sandbox-OFF → null/disabled,
judge commits ONLY once judgeCell is a real cell, filterJudgeModels still pins mock_judge as the
Local+Cheapest picker default; WS-C decision-question = pure briefHelpers.ts —
effectiveDecisionQuestion(q,touched) returns "" when untouched (clears on dataset change, no
re-derive), decisionQuestionTouched set on typing AND onSelectRecipe, Quick payload overrides
brief.decision_question with quickDecisionHeadline(prompt) (blank → falls back to task_name),
decision_question is content NEVER in config_hash so mock 467ddd96c9a5 untouched; WS-D1 scatter =
Recharts ONLY (no second charting lib), pure paretoFrontier.ts reoriented LOWER-cost-better (opposite
of Arena's higher-x skyline — don't simplify back), FrontierScatter dots via v3 shape prop not <Cell>,
recommended = ONLY --color-accent / others status-toned, all var(--color-x) never hardcoded hex, FE-only
display touching no backend/hash).
```
