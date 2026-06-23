# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-23 · **Stage 3 in progress — Task 5 (WS-C) DONE + committed (`1864b35`).**
The Proof Brief's **decision question** (which headlines the receipt) can no longer silently contradict
what's under test, on either surface. **Config:** new `decisionQuestionTouched` (symmetric to
`taskNameTouched`) — an *untouched* question **clears** on dataset change (no dataset→question mapping
to re-derive, so clearing → placeholder is the honest default); a typed/recipe-selected question is
touched and survives. `onSelectRecipe` marks touched. **Quick:** saved Quick receipt headline now
**derives from the Quick prompt** (`quickDecisionHeadline()` — whitespace-collapsed, trimmed, 120-cap;
blank → empty → QuickCompare falls back to task_name), never the stale Models-mode question. Pure logic
in new `briefHelpers.ts`. **FE-only — no backend, no migration, no RECEIPT_VERSION bump**
(`decision_question` is content, never in `config_hash`; mock `467ddd96c9a5` untouched by construction).
Verified: **298 BE / 150 FE** (+9 FE), tsc + build clean. Browser (real keys, Sandbox OFF): fresh
dataset → empty question; recipe question survives dataset switch; Quick run (Haiku 4.5 vs Gemini
3.1 Flash-Lite) → QuickCompare headline + persisted `brief` + **exported MD `**Decision:**` line** all
= the Quick prompt; receipt secret-free. Fresh-context `diff-reviewer` confirmed faithful + no regressions.
**Execute Task 6 (WS-D1) next session.** `main` local-only; git remote/push stay queued LAST until
packaging (operator directive)._

## ▶️ START HERE NEXT SESSION — execute task 6 (WS-D1) from the NEXT TASKS queue

**Stage 3 is underway: one point-task per session.** Tasks 1–5 are checked off below. Read the
spec workstream before coding (`_SPECS/2026-06-22-trustworthy-proof-and-polish.md` — names exact
files/interfaces, fences out-of-scope, ends with a verify). Build smallest slice → verify (tests +
browser per CLAUDE.md) → check the box → re-handoff.

**Next up: Task 6 — WS-D1 (Pareto cost-vs-quality scatter, MED).** Reuse Arena `FrontierScatter.jsx`
(confirmed exists at `…/ainative-business.github.io/arena-app/src/components/arena/FrontierScatter.jsx`)
beneath the leaderboard; accent **only** on the recommended point. See spec §WS-D1. _verify:_ Vitest on
`paretoFrontier()` + Playwright mount on a populated run. _ref:_ §WS-D1 · feature #2. _Recharts is
already a frontend dep (see CLAUDE.md stack) — confirm before reusing the Arena component as-is (it may
be plain SVG/JSX); port to TS + the cockpit's semantic tokens._

_WS-C committed to `main` as `1864b35` (worklog `docs/worklog/2026-06-23-ws-c-decision-question-integrity.md`).
WS-B = `5307ae5`; an unrelated CLAUDE.md self-improvement pass = `1dc3eb1`. WS-A3 = `9e413d5`,
WS-A2 = `f2b7e91`, WS-A1 = `593d346`._

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
- [ ] **6 · D1 — Pareto cost-vs-quality scatter** (MED). Reuse Arena `FrontierScatter.jsx` (confirmed
  exists) beneath the leaderboard; accent only on the recommended point. _verify:_ Vitest on
  `paretoFrontier()` + Playwright mount on a populated run. _ref:_ §WS-D1 · feature #2.
- [ ] **7 · D2 — Run-level cost ledger panel** (MED). Reuse ainative `lib/usage/ledger.ts` +
  `cost-dashboard.tsx` + micro-viz (confirmed exist); per-provider tokens+$ + run total in Inspector.
  _verify:_ sums match the verdict banner's "Run cost" line. _ref:_ §WS-D2 · feature #3.
- [ ] **8 · E1 — Candidates inline add-key / start-host affordance** (MED). List known providers; quiet
  "Add key in Settings →" for unconfigured cloud + "Start Ollama/LM Studio" for local. Reuse the
  selection panel's gated entries. _ref:_ §WS-E1 · feature #4.
- [ ] **9 · E2 — Guided first-run CTA** (MED, depends on A2). One-click "Run the demo proof on real
  models" on the empty state → clear-winner receipt in ~30s. _ref:_ §WS-E2 · feature #5.
- [ ] **10 · F1–F5 — DS application-consistency pass** (LOW; may split). F1 seed sample dataset
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
   ad-hoc prompt (by design). Future: seed the prompt into a one-example set.
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

## Paste prompt for the next session
```text
Stage 3 execution, one point-task per session. The _IDEAS→_SPECS pipeline is DONE; the approved spec
is _SPECS/2026-06-22-trustworthy-proof-and-polish.md. Tasks 1 (A1, 593d346), 2 (A2, f2b7e91), 3
(A3, 9e413d5), 4 (B, 5307ae5) and 5 (C, 1864b35) are checked off in the HANDOFF NEXT TASKS queue.
WS-A + WS-B + WS-C done.

▶️ EXECUTE TASK 6 — WS-D1 (Pareto cost-vs-quality scatter, MED). Read spec §WS-D1 first (names exact
files/interfaces, fences out-of-scope, ends with a verify): reuse Arena FrontierScatter.jsx (at
…/ainative-business.github.io/arena-app/src/components/arena/FrontierScatter.jsx) beneath the
leaderboard; accent ONLY the recommended point; port to TS + the cockpit's semantic tokens (Recharts is
already a FE dep — confirm whether the Arena component is plain SVG/JSX or charted before reusing).
_verify:_ Vitest on paretoFrontier() + Playwright mount on a populated run. Build smallest slice →
verify (uv run pytest + pnpm test + pnpm build + browser per CLAUDE.md) → check the box → re-handoff.
_ref:_ §WS-D1 · feature #2.

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
decision_question is content NEVER in config_hash so mock 467ddd96c9a5 untouched).
```
