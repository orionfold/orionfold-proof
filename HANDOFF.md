# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-23 · **BACKLOG MERGED + PRIORITIZED (docs-only, no code).** The old HANDOFF
list (#1–8) and `_IDEAS` (B1–B8) were reconciled against repo state into one ranked `## MERGED BACKLOG`
table below — **B6 (dual-distribution) is now #1, NOT #7 packaging** (the prior "natural next" was stale).
Full B1–B8 reasoning frozen in `_IDEAS/backlog-archive-2026-06-23.md`; `_IDEAS/backlog.md` reset to an
empty intake stub for fresh findings. Last shipped code = **B4 Track Record web screen (`33339d5`)** ↓._

_**B4 (prior commit):** Exposed the pure core fn `track_record()` over a thin `GET /api/track-record` (`?dataset_id=`) route and
rendered it as a new cockpit view — **which candidate has earned trust across repeated runs**, grouped by
comparable slice (dataset × rubric kind), ranked by **pooled** pass-rate (Σpasses/Σexamples), dataset
dropdown filter. **Additive only** (core fn reads existing fields, re-runs no scoring → no migration, mock
`467ddd96c9a5` untouched by construction). DS accent/status split held (pass bars `--color-ok`, zero
`--color-accent` in the view); privacy carried via `ProviderTag`. **344 BE (+2) / 234 FE (+4)**, ruff+pyright
0, tsc+vite build clean, **14/14 Playwright** (+1 nav smoke); real-browser graded light+dark (11 groups
across every rubric class, pooled bars correct, AAA primary text, secret-free, filter + 2 empty states
verified); fresh-context diff-reviewer **PASS — ship it**. Minor filter↔history-id seam logged as
`_IDEAS/backlog.md` **B8** (non-blocking). See ▶️ START HERE below. (worklog
`docs/worklog/2026-06-23-b4-track-record-web-screen.md`.)_

<!-- prior status (two slices: pyright hygiene + DEFAULT_THRESHOLDS single-source) below — superseded -->
<!-- _**Two slices DONE.** (1) **Pyright hygiene** (`39b432b`): cleared the 9 pre-existing
`export.py`/`resolution.py` errors with behavior-identical narrowing fixes — tree is now **genuinely
pyright-clean (0 errors)**. (2) **`DEFAULT_THRESHOLDS` single-source** (the deferred §6 slice, `814c120`):
Python is now the single source of truth; the FE consumes a **codegen'd** `web/.../thresholds.generated.ts`
(written by `orionfold codegen`) instead of a hand-mirrored literal. A backend staleness guard
(`tests/unit/test_codegen.py`) fails CI on drift. **342 BE (+2) / 230 FE**, ruff+pyright 0, tsc+vite build
clean, `467ddd96c9a5` 8/8 freeze tests pass (keypoint stayed 0.8), diff-reviewer clean, negative-tested.
(worklog `docs/worklog/2026-06-23-default-thresholds-single-source.md`.)_ -->

<!-- prior status (B3 real-world demo datasets, af8203d) below — superseded -->
<!-- _BACKLOG B3 (real-world demo datasets) is DONE + committed (`af8203d`). The
approved spec `_SPECS/2026-06-23-real-world-demo-datasets.md` shipped: **3 new bundled synthetic datasets**
(`support-ticket-triage`→exact, `contract-field-extraction`→contains, `buyer-need-solution-match`→similarity
/LLM-judge) so a fresh install spans **four rubric classes** (keypoint·exact·contains·judge). All additive —
**no migration** (index stays 6); mock `467ddd96c9a5` untouched by construction (brand-new ids, no shared hash
path; no new `check_hint` maps to keypoint). `sample_data.py` refactored single-seed → a `SampleSpec` list;
`seed_sample_data` returns **`(4,4)`** and scores each seeded receipt by the same rubric a real run resolves
(the investment-memo sample stays keypoint — its `check_hint="eyeball"` ∉ `_HINT_KIND`). `SettingsView` seed/
remove copy pluralized to match the new count. Verified: **309 BE (+11) / 230 FE**, ruff + pyright clean on
changed files, **13/13 Playwright** (re-embedded build). **Real-model browser pass** (Sandbox OFF, real keys,
cost OK'd; Haiku 4.5 + GPT-5.4-nano): triage→**Exact 100%** clear winner; extraction→Auto reads "Contains text
→ Contains", **Contains** clear winner; buyer-match→demo-judge-default auto-picked **LLM judge · claude-haiku-
4-5**, verdict "claude-haiku-4-5 is the clear pick" (20% vs nano 0%); all 3 receipts record the right "Scored
by:" line + **secret-free** (md/html/json: 0 matches). **Operator decisions:** (a) browser-verify all 3; (b)
loosen buyer-match reference pitches; (c) the loosening only marginally moved pass rate (judge@0.8 is strict on
open-ended generation — a Settings knob, out of B3 scope) → **ship the loosened data as-is** (honest, repeatable
clear winner). Fresh-context diff-reviewer: **PASS** (confirmed mock-hash safety, no migration, metadata DB-only,
investment-memo→keypoint preserved, empty-hint→None test, justified SettingsView pluralization). ⚠️ **Pre-existing
pyright (9): `receipts/export.py` + `recipes/resolution.py` errors exist on the CLEAN pre-B3 tree (stash-confirmed)
— NOT from B3; prior "pyright clean" claims were inaccurate. Worth a separate cleanup.** (worklog
`docs/worklog/2026-06-23-b3-real-world-demo-datasets.md`.) **Next: back to deferred BACKLOG (operator picks) —
natural next is #7 packaging·licensing·distribution (BRAINSTORM FIRST); #8 git remote+push stays LAST.** `main`
local-only; git remote/push stay queued LAST until packaging (operator directive)._ -->

<!-- prior status (Stage 3 COMPLETE, Task 11 WS-F, 9820b5c) below — superseded -->
<!-- _Stage 3 COMPLETE — Task 11 (WS-F DS application-consistency pass) is DONE +
committed (`9820b5c`). The Stage-3 point queue is now EMPTY.** WS-F shipped all five DS items in one session
(token foundation already matched — these were application-consistency fixes, NOT color drift): **F1** the
seeded sample dataset now writes display metadata (`insert_sample_dataset` + `seed_sample_data` pass
`created_at`=`2026-06-19T12:00:00Z` / `source`="Bundled with Orionfold" / `check_hint`="eyeball") so its card
reads `5 examples · created … · Bundled with Orionfold` + an "Eyeball / judgment" chip, matching user sets —
**no migration** (cols exist at index 5; display-only, engine never reads `check_hint`); **F2/F3** the
`Leaderboard.tsx` headers are now mono micro-caps (reference `.tbl` voice) **and sortable** (client-side,
`aria-sort`, cyan accent + `↕/↑/↓` arrow on the active column) — the server ranking is the **default on load**
(`column:null`, podium medals meaningful) and **medals are suppressed once sorted** (explore mode), the
recommended highlight stays tied to `entry.recommended` not index; pure sort logic in new
`leaderboardSort.ts` (null `$/quality` always sinks, stable w/ server-order tiebreak); **F4** the Mock
`ProviderTag` is now **warn-tinted** (`border/bg/text --color-warn`, reference `.badge.warn`) so simulated ≠
real reads at a glance — Cloud/Local unchanged neutral, base span no longer hardcodes border/bg (per-kind
`cls` owns it, no Tailwind conflict); **F5** `ViewShell` width-caps inspector-less routes (`max-w-5xl`,
left-anchored) so they don't read full-bleed vs the cockpit's main+22rem grid (widen-main-only — operator
decision; `ProofCockpit` doesn't use `ViewShell` so the cockpit is untouched). **FE + a backend seed fix; no
migration/`config_hash` change** — mock `467ddd96c9a5` intact (double-safeguard: `"eyeball"` not in
`_HINT_KIND`, AND `seed_sample_data` doesn't pass `check_hint=` to scoring). Verified: **230 FE (+18) / 298 BE
(unchanged)**, tsc exit 0 + build clean, ruff+pyright clean, **13/13 Playwright** (re-embedded build into the
gitignored static dir). **Real-browser light + dark** (`browser-visual-verification`): F1 sample card metadata
+ chip (after a re-seed of the stale pre-fix row); F2 click reorders + accent + `aria-sort` + medals→ranks; F3
mono micro-caps both themes; F4 amber Mock badge distinct from neutral Cloud, AA both themes; F5 balanced;
secret-free; restored Sandbox OFF + dark after. Full-receipt HTML **byte-identical** (palette guard green;
`receipts/export.py` untouched). Fresh-context diff-reviewer: **PASS — ship-ready, no correctness/invariant
issues** (independently confirmed the `config_hash` double-safeguard + null-sort + accent/status split +
ViewShell scope). (worklog `docs/worklog/2026-06-23-ws-f-ds-application-consistency.md`.) **Next: the point
queue is EMPTY — only deferred backlog remains (packaging·licensing·distribution, BRAINSTORM first → git
remote+push LAST).** `main` local-only; git remote/push stay queued LAST until packaging (operator directive)._ -->

<!-- prior status (Task 9.5 demo-scorer-default, 50155bb) below — superseded -->
<!-- _Stage 3 in progress — the demo-scorer-default fix (Task 10's blocker) is
DONE + committed (`50155bb`).** The bundled **"Sample · investment memo summarization"** demo (the
seeded `is_sample` dataset) now **defaults its run's scoring method to the LLM judge** instead of
Auto/Keypoint. Lexical Similarity/Keypoint scores free-form paraphrase ~0 ("NO CLEAR WINNER") at any
threshold (re-runs read 0.06–0.15 even at the shipped 0.55 default), so the honest fix is the scorer,
not the threshold. **FE-only, reuses the A3 judge gate:** new pure `prefersSampleJudge(dataset,
judgeCell)` in `web/.../scoring.ts` (true iff `is_sample` AND a resolved **non-`mock_judge`** cell — the
tri-state `undefined`/`null`/`mock_judge` all return false, so a keyless user stays on Auto and Sandbox
keeps its keyless clear-winner demo, **never a silent Mock**) + a **`useRef`-latched `useEffect`** in
`ScoringMethod.tsx` that fires `selectMethod("judge")` **once per sample-dataset arrival** while
`value===null`, routed through the existing `if (judgeCell)` commit gate so it can only emit a **real**
judge (A3 invariant preserved). No backend/migration/`config_hash` change — mock `467ddd96c9a5` intact
by construction. **Operator decisions:** (a) fix the scorer first (demo-critical) over the unblocked
Task 11; (b) put the default in the **frontend** (the keyless backend scoring core can't resolve a
concrete judge model — that lives in `defaultJudgeCell`). Verified: **204 FE (+12) / 298 BE
(unchanged)**, tsc+build clean, **12/12 Playwright** (re-embedded build into the gitignored static dir;
the Sandbox e2e still asserts the *catalog* demo → **Keypoint**, since it's `is_sample:false`).
**Real-browser, REAL models** (Sandbox OFF; Anthropic+OpenAI keys; cost OK'd): seeded the sample, selected
it → Scoring **auto-selected LLM judge** (Claude Haiku 4.5 · Anthropic, Hosted/Cheapest) → ran a real
proof (config `4193ef79ba57`) → **clear winner: RECOMMENDED claude-haiku-4-5, passed 3/5 (60%), avg 0.71
> nano 0.68, total $0.0135**; receipt records **"Scored by: LLM judge · claude-haiku-4-5"**; all 3 exports
**secret-free**. Negative cases verified live: fresh load on the catalog (non-sample) → **Auto**; Sandbox
ON + sample → stays Auto (no mock-judge auto-select). Fresh-context diff-reviewer: **faithful, no
regressions/invariant violations/scope creep**. (worklog `docs/worklog/2026-06-23-demo-judge-default.md`;
`_IDEAS/issues.md` "REAL-RUN: flagship … NO CLEAR WINNER" marked ✅ RESOLVED.) **Next: Task 10 (WS-E2
guided first-run CTA) is now UNBLOCKED — build the one-click "run the demo on real models" CTA.** `main`
local-only; git remote/push stay queued LAST until packaging (operator directive)._ -->

## ▶️ START HERE NEXT SESSION — B4 Track Record web screen DONE (operator picks the next slice).

**This session (2026-06-23):** shipped **BACKLOG B4 — the Track Record web screen** (`33339d5`). The pure
core fn `track_record()` (built in the CLI-widen slice `b2bf9d3`) is now exposed over a thin
`GET /api/track-record` (`?dataset_id=`) route and rendered as a new cockpit nav view (after Receipts,
`TrendingUp` icon). It answers **which candidate has earned trust across repeated runs** — groups by
comparable slice (dataset × rubric kind), ranks by **pooled** pass-rate (Σpasses/Σexamples so a larger run
weighs more), `won N×` markers, dataset dropdown filter. FE display + one read-only route over existing
data → **no migration, no scoring/hash change**, mock `467ddd96c9a5` untouched by construction. This is the
first screen to render a dual-distribution core fn the CLI already exposes (`orionfold track-record`) —
same data, two surfaces. Verified end-to-end (344 BE / 234 FE / 14 Playwright / real-browser light+dark /
diff-reviewer PASS). **Remaining deferred backlog below — operator picks; do NOT auto-start.** B4 is no
longer a candidate (done).

**Earlier this session:** pyright hygiene (`39b432b` — 9 baseline errors cleared, tree now 0 errors) + the
`DEFAULT_THRESHOLDS` single-source codegen slice (`814c120`). Both still hold.

<!-- prior START HERE (CLI-widen slice 2) below — superseded by the two slices above -->
## (superseded) Dual-distribution: CLI widened.

**Major pivot 2026-06-23: from B4 (cross-run leaderboard) to the strategic DUAL-DISTRIBUTION MODEL.**
The FE-only rollup reflex was at odds with Proof's CLI/package distribution. Deep-studied
ainative.business's fieldkit→arena→field-notes loop, wrote **ADRs 0004/0005/0006** + origin spec
(operator-approved; **Apache-2.0 confirmed**). Shipped **slice 1** (`134e9e5`): headless `orionfold run`
through a shared core (`execute_run`/`execute_resolved` in `proof/runner.py`) the route + CLI both call.

**Slice 2 — CLI WIDENED (DONE + committed `b2bf9d3`).** ADR-0004 §8 next slice. (a) NEW CORE FN
**`track_record(reports, *, dataset_id=None)`** in `proof/leaderboard.py` — the B4 cross-run rollup as a
**pure core function** (ADR-0004 §5), grouping by **`(dataset_id, rubric.kind)`** (the comparability
rule), **pooled** pass-rate (Σpasses/Σexamples, NOT a mean of per-run rates), quick runs excluded
(`mode=="quick"`/`rubric.kind=="none"`), reads only existing `LeaderboardEntry`/`ProofRun` fields → can't
touch `config_hash`. New `TrackRecordGroup`/`TrackRecordEntry` models; exported from `proof.__all__`
(+`build_leaderboard` formalized). (b) NEW CLI verbs as **thin shells** (ADR-0004 §3) over a shared
`_with_conn()` helper (extracted from `run`'s old inline connect/migrate/close — `run` reuses it,
behavior unchanged): **`dataset import|list`**, **`runs list|show`**, **`track-record`**. `runs show
--format` reuses `run`'s `_FORMAT_RENDERERS` map → **byte-identical receipt, now locked by a test**.
**`DEFAULT_THRESHOLDS` single-source (§6) DEFERRED** to its own slice (operator decision) — slice 2 is
**BE/CLI-only, FE untouched**. Verified: **340 BE (+21: 8 track_record + 13 CLI workflow)**, ruff clean,
pyright 0 errors on changed files (pre-existing 9 in export.py/resolution.py untouched), the 8
`467ddd96c9a5` freeze-tests pass, headless e2e (import→list→2 runs→runs list→track-record) secret-free.
Fresh-context diff-reviewer: **clean** (no bugs / invariant violations / scope creep). (worklog
`docs/worklog/2026-06-23-cli-widen-dataset-runs-track-record.md`.)

**Next (operator picks — see the prioritized `## MERGED BACKLOG` table below):** the full backlog
was merged + re-ranked 2026-06-23. **Top of the list is now B6** (dual-distribution core — ADRs
already written, brainstorm+slice remain), **NOT #7 packaging** (the old "natural next" line was
stale; B6's same-day directive demoted packaging to *downstream of B6*). B7 (private-strategy symlink)
is HIGH and **blocks the final git remote+push**. Do NOT auto-start anything — surface a row only when
the operator asks. `main` local-only, all work committed, clean worktree, shippable state.

**✅ Pyright baseline cleared (`39b432b`):** the 9 pre-existing `export.py`/`resolution.py` errors are
fixed — `uv run pyright` now reports **0 errors** on the full `src` tree. A "pyright clean" claim can now
be taken at face value (run full `uv run pyright`, expect 0).

_B3 real-world demo datasets = `af8203d` (worklog `docs/worklog/2026-06-23-b3-real-world-demo-datasets.md`;
spec `_SPECS/2026-06-23-real-world-demo-datasets.md`). Task 11 (WS-F DS pass) = `9820b5c`.
Task 10 (WS-E2 guided first-run CTA) = `5cc8ca0` (worklog
`docs/worklog/2026-06-23-ws-e2-guided-first-run-cta.md`). Demo-scorer-default fix = `50155bb` (worklog
`docs/worklog/2026-06-23-demo-judge-default.md`). Task 9 (WS-E1 add-key affordance) = `f65e686` (worklog
`docs/worklog/2026-06-23-ws-e1-candidates-add-key-affordance.md`). Task 8 (WS-D2 cost ledger) = `055bd50`
(worklog `docs/worklog/2026-06-23-ws-d2-run-cost-ledger.md`). Task 7 (Decide insight layer) = `30e5cf5`
(worklog `docs/worklog/2026-06-23-decide-insight-layer.md`). WS-D1 = `0f83f9e`
(worklog `docs/worklog/2026-06-23-ws-d1-pareto-cost-quality-scatter.md`). WS-C = `1864b35`;
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
- [x] **8 · D2 — Run-level cost ledger panel** (MED) ✅ DONE 2026-06-23 (`055bd50`). A **Run cost** panel
  beneath the scatter on a populated full run: per-candidate tokens in/out · candidate $ · judge $ ·
  **share of run spend** · a **reconciled run total**. New pure `costLedgerMath.ts`
  `buildCostLedger(leaderboard, results)` rolls `ResultRow`s up per `candidate_id` (Σ `estimated_cost_usd`,
  Σ `judge_cost_usd`, Σ tokens) — sums **equal `report.cost_summary` / the verdict's "Run cost" line by
  construction** (both roll up the same rows); share divide-by-zero-safe; **leaderboard order preserved**;
  privacy **carried not guessed**. `CostLedger.tsx` is DS-clean (**neutral ink only — NEVER
  `--color-accent`/`--color-ok`**; `tabular-nums`; judge "—" when none; "Free" on zero-cost). Mounted
  **full-run branch only**. ⚠️ pure module is `costLedgerMath.ts` NOT `costLedger.ts` (macOS
  case-insensitive collision w/ `CostLedger.tsx` — mirrors `paretoFrontier`/`FrontierScatter`). **FE-only —
  no backend/migration/config_hash**; mock `467ddd96c9a5` intact. 298 BE (unchanged) / 189 FE (+11),
  tsc+build clean, 11/11 Playwright. Real-model (Sandbox OFF, Haiku+Opus, config `04ffcde784fc`): panel
  total **$0.0584** reconciles to the verdict line exactly; light+dark graded, secret-free. Fresh-context
  diff-reviewer: clean. _new files:_ `costLedgerMath.ts` + `CostLedger.tsx` (+tests). _files touched:_
  `ProofCockpit.tsx` · `proof.spec.ts`. _ref:_ §WS-D2 · feature #3.
- [x] **9 · E1 — Candidates inline add-key / start-host affordance** (MED) ✅ DONE 2026-06-23
  (`f65e686`). `CandidatesView` now renders from **`/api/selection`** (every catalog provider +
  `available` flag) instead of the available-only `/api/candidates`, so unconfigured providers are
  shown, not silently omitted. Unconfigured cloud → "Not configured" + a reason naming the exact env
  var + the existing inline **`<KeyEntry>`** (writes `.env.local` server-side, invalidates
  `["selection"]` so the card flips live); unconfigured local → "Start the local server" hint;
  available → models listed. **Operator chose inline KeyEntry over a Settings deep-link** (SettingsView
  has no key field; KeyEntry is the already-built secrets-guard-safe path). Reuses `KeyEntry` /
  `CLOUD_KEY_NAMES` / `ProviderTag` / `ProviderLogo` / the panel's `available` gate — no new gating,
  no key-entry rebuild. Removed orphaned `getCandidates()` client. **FE-only — no
  backend/migration/config_hash**; mock `467ddd96c9a5` intact. 192 FE (+3) / 298 BE (unchanged),
  tsc+build clean, **12/12 Playwright** (+1 smoke; re-embedded build into the gitignored static dir).
  Real-browser verified against a **keyless** API instance (`ORIONFOLD_ENV_FILE` override; real
  `.env.local` untouched): 4 cloud providers show the add-key affordance + reason, 2 local list models,
  light + dark graded, secret-free. Fresh-context diff-reviewer: ship-ready. _new file:_
  `CandidatesView.test.tsx`. _files touched:_ `CandidatesView.tsx` · `lib/api.ts` · `proof.spec.ts`.
  _ref:_ §WS-E1 · feature #4. (worklog `docs/worklog/2026-06-23-ws-e1-candidates-add-key-affordance.md`)
- [x] **9.5 · Demo-scorer-default fix (Task 10's blocker)** ✅ DONE 2026-06-23 (`50155bb`). The bundled
  `is_sample` summarization demo now **defaults to the LLM judge** (FE-only): pure
  `prefersSampleJudge(dataset, judgeCell)` in `scoring.ts` (true iff `is_sample` AND a resolved
  non-`mock_judge` cell) + a `useRef`-latched effect in `ScoringMethod.tsx` that auto-selects the judge
  once per sample-dataset arrival (value===null), through the existing `if (judgeCell)` commit gate.
  Sandbox keeps its keyless demo; keyless user stays on Auto (never silent Mock); non-sample unaffected.
  No backend/migration/`config_hash` change — mock `467ddd96c9a5` intact. 204 FE (+12) / 298 BE, tsc+build,
  12/12 Playwright. Real-model browser (Sandbox OFF): sample → auto LLM judge (Claude Haiku 4.5) → clear
  winner (RECOMMENDED claude-haiku-4-5, 60%, avg 0.71), receipt "Scored by: LLM judge", secret-free.
  Fresh-context diff-reviewer: faithful. _files:_ `scoring.ts`(+test) · `ScoringMethod.tsx`(+test). _ref:_
  `_IDEAS/issues.md` "REAL-RUN: flagship … NO CLEAR WINNER" (✅ RESOLVED) · worklog
  `docs/worklog/2026-06-23-demo-judge-default.md`.
- [x] **10 · E2 — Guided first-run CTA** (MED) ✅ DONE 2026-06-23 (`5cc8ca0`). One-click "Run the demo
  proof on real models" on the **empty** Proof Run state: seeds the bundled `is_sample` sample (if absent),
  selects it, preselects **2 cheap cloud candidates**, lets `ScoringMethod` auto-apply the LLM judge
  (`50155bb` default), and **auto-runs** → clear-winner receipt in ~30s. **FE-only:** new pure
  `cheapCloudCandidates(panel)` in `scoring.ts` (cheapest available cloud first; 2 distinct ids);
  `ProofCockpit.tsx` gains `canRunDemo = cheapCloud.length===2` (**CTA shown only when ≥2 cheap cloud** —
  honest promise; operator decision), a seed mutation, `startGuidedDemo()` (preselect + arm, **no rubric
  reset** — the judge latch is once-per-dataset), an arm effect (holds sample selected through seed→refetch),
  and an **auto-run effect firing only once `rubric.kind==="judge"`** (backend keypoint fallback unreachable;
  one-shot; disarms-no-spin if a non-judge method was pre-picked). **Operator decisions (AskUserQuestion):**
  CTA = preselect + auto-run when ready (judge default is async); no-key fallback = hide the CTA. No
  backend/migration/`config_hash` change; mock `467ddd96c9a5` intact. **212 FE (+8) / 298 BE (unchanged)**,
  tsc exit 0 + build clean, **13/13 Playwright** (+1 CTA smoke). Real-browser, REAL models (Sandbox OFF):
  one click → sample + LLM judge (Claude Haiku 4.5) + 2 cheap cloud → **clear winner RECOMMENDED gpt-5.4-nano,
  80% (4/5), avg 0.73, total $0.0130** (`run_593bbe577f05`, `rubric.kind:judge`); receipt "Scored by: LLM
  judge", 3 exports secret-free. Fresh-context diff-reviewer: PASS (hardened one liveness edge). _new files:_
  none. _files touched:_ `scoring.ts`(+test) · `ProofCockpit.tsx`(+test) · `proof.spec.ts`. _ref:_ §WS-E2 ·
  feature #5. (worklog `docs/worklog/2026-06-23-ws-e2-guided-first-run-cta.md`)
- [x] **11 · F1–F5 — DS application-consistency pass** (LOW) ✅ DONE 2026-06-23 (`9820b5c`). All five in
  one session. **F1** `insert_sample_dataset`+`seed_sample_data` write the sample's display metadata
  (`created_at`/`source`="Bundled with Orionfold"/`check_hint`="eyeball") — card now matches user sets; **no
  migration** (cols at index 5; display-only). **F2/F3** `Leaderboard.tsx` mono micro-caps headers + sortable
  (client-side, `aria-sort`, accent+arrow on active col); server ranking = default-on-load (medals
  meaningful), medals suppressed once sorted; pure `leaderboardSort.ts` (null `$/quality` sinks, stable). **F4**
  Mock `ProviderTag` warn-tinted (`--color-warn`, ref `.badge.warn`); Cloud/Local unchanged; base span no
  longer hardcodes border/bg. **F5** `ViewShell` `max-w-5xl` left-anchored (inspector-less only; cockpit
  doesn't use ViewShell). FE + backend seed fix; no migration/`config_hash` change — mock `467ddd96c9a5`
  intact (`"eyeball"`∉`_HINT_KIND` AND seed doesn't pass `check_hint=` to scoring). 230 FE (+18) / 298 BE,
  tsc 0 + build + ruff/pyright clean, 13/13 Playwright; real-browser light+dark graded, secret-free; receipt
  HTML byte-identical. Fresh-context diff-reviewer: PASS (ship-ready). _new files:_ `leaderboardSort.ts`(+test).
  _files touched:_ `sample_data.py` · `repository.py` · `Leaderboard.tsx`(+test) · `badges.tsx`(+test) ·
  `ViewShell.tsx` · `test_settings_and_samples.py`. _ref:_ §WS-F · DS #1–#5. (worklog
  `docs/worklog/2026-06-23-ws-f-ds-application-consistency.md`)

_**Stage 3 point queue is now EMPTY** — every HIGH/MED/LOW task above is shipped. Only deferred BACKLOG
remains (below); operator picks. git remote+push stays queued LAST behind packaging (operator directive)._

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

## MERGED BACKLOG — prioritized (operator picks; do NOT auto-start)

> **Single source of truth for "what's next."** Merged 2026-06-23 from the old HANDOFF list
> (#1–8) + `_IDEAS` (B1–B8), reconciled against actual repo state. Per-item detail (Arena
> reuse notes, migration steps, invariant forks) is frozen in
> `_IDEAS/backlog-archive-2026-06-23.md`; `_IDEAS/backlog.md` is now an empty intake stub for
> NEW findings. When a new item earns a slot, fold it into this table and re-rank.
>
> ⚠️ Reconciliation: HANDOFF's old "natural next = #7 packaging" was **stale** — the same-day
> operator directive (archive B6) demoted #7 to *downstream of B6*. This table reflects that.

| # | Item | Priority | State / gate |
| --- | --- | --- | --- |
| 1 | **B6 — Dual-distribution core + dogfooding loop** | **NOW / HIGHEST** | ADRs 0004/0005/0006 + `_SPECS/2026-06-23-dual-distribution-findings.md` **already written**. Remaining: brainstorm w/ operator → vertical slice moving canonical logic into the Python core. *Supersedes #7 framing; blocks B4.* |
| 2 | **B7 — Private-strategy symlink + relay** | **HIGH** | **Blocks #14.** `_IDEAS`/`_SPECS` confirmed still **real dirs (not symlinks)**. Own git-history-touching session. Independent of B6 → can run parallel. |
| 3 | **#7 — Packaging · licensing · distribution** | MED–HIGH | **Downstream of B6** (B6 defines the boundary #7 packages). Apache-2.0 flip, PyPI metadata (dist `orionfold-proof`/CLI `orionfold`; reserve `orionfold`+`orionfold-arena`), `uv tool install … → orionfold up`, release ritual. Scope FIRST. |
| 4 | **B4 — Reimagine Candidates → cross-run board** | MED–HIGH | ⏸ **PAUSED, blocked on B6.** Web screen already shipped (`33339d5`); the Arena-leaderboard reimagining is the paused part. |
| 5 | **B5 — Make Quick Compare more whole** | MED–HIGH | Brainstorm FIRST. Overlaps B2 (#8) + B4. Mine Arena `CompareDuel.jsx`. |
| 6 | **Cross-product models × prompts** | MED | N models × M prompts in one run. Brainstorm FIRST. |
| 7 | **Catalog price/source accuracy pass** | MED | Verify list prices + context windows (`current-docs-check`). |
| 8 | **B2 — Quick→Promote carries the prompt** | LOW–MED | UX seam (promote drops the ad-hoc prompt by design). May be superseded by B5#4 (inline scoring). |
| 9 | **DS-skin polish** | LOW–MED | Shared token-driven badge/chip/bar kit (DS findings in `_IDEAS/design-system.md`); receipt proof-seal stamp. |
| 10 | **B8 — Track Record filter ↔ run-id drift** | LOW | Minor seam from the B4 build; honest empty states. Anchors in `TrackRecordView.tsx`. |
| 11 | **B1 — Exact rubric shows `≥ 0.8` in receipt** | LOW | Cosmetic; harmless (binary check grades identically at any threshold in (0,1]). |
| 12 | **Stored "Recommended on 0/5" backfill** | LOW | Optional one-off; 2026-06-21 pre-gate runs only. New runs correct. |
| 13 | **Richer sample data** | LOW | Extend `sample_data.py` if onboarding wants it. |
| 14 | **git remote + push** | **LAST** | **Gated on BOTH B6→#7 AND B7.** Do NOT surface until those land (operator directive). No remote; `main` holds all work unpushed (incl. strategy content — why B7 precedes this). |

_✅ Shipped, dropped from active: **B3** real-world demo datasets (`af8203d`)._

_Standing notes: several ad-hoc real runs (incl. "no winner") sit in `~/.orionfold/proof.db` —
clear via Settings → data management for a pristine demo state if wanted. `_IDEAS/issues.md`,
`feature-opportunities.md`, `design-system.md` still hold the unpromoted finding detail._

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
- **Track Record web screen (B4, SHIPPED `33339d5`):** `GET /api/track-record` (`?dataset_id=`) is a
  **thin route** over the pure core fn `track_record(list_runs(conn), dataset_id=...)` in
  `proof/leaderboard.py` — all rollup logic lives in the core fn; the route adds **zero business logic**
  (ADR-0004 §3). The core fn reads only existing `LeaderboardEntry`/`ProofRun` fields and re-runs no
  scoring → **can't touch `config_hash`**; mock `467ddd96c9a5` untouched. **Pooled** pass-rate =
  Σpasses/Σexamples (NOT a mean of per-run rates); groups by `(dataset_id, rubric.kind)` (the
  comparability rule — same dataset scored the same way); quick/`kind=="none"` runs excluded by the core
  fn. **FE:** `TrackRecordView.tsx` renders from `getTrackRecord(datasetId?)` with queryKey
  `["track-record", datasetId || null]`; the Zod `trackRecord{Entry,Group}Schema` in `api.ts` are a
  **field-by-field mirror** of the Pydantic models (`domain/models.py` `TrackRecordEntry`/
  `TrackRecordGroup`) — keep them in sync; `rubric_kind` uses the extracted `rubricKindSchema` (full
  `RubricKind` union). DS: pass-rate bars use **`--color-ok`** (status), the view introduces **no
  `--color-accent`**; `privacy` is **carried** from the entry into `ProviderTag`, never guessed.
  Registered in `App.tsx` (View union / NAV `TrendingUp` after Receipts / conditional render). The e2e
  nav smoke scopes to the **visible `<main>`** (the hidden mounted cockpit's text would otherwise satisfy
  a global `getByText`). ⚠️ Known non-blocking seam (`_IDEAS` B8): the filter dropdown lists *current*
  datasets while groups reflect *historical* run ids — "All datasets" can show groups the dropdown can't
  isolate, and a selectable dataset may have no runs (correct empty state). FE display + one read-only
  route over existing data — no backend/hash/migration.
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
- **Threshold codegen (single-source, `814c120`):** `DEFAULT_THRESHOLDS` is **canonical in
  `scoring/rubric.py`**. The FE no longer hand-mirrors it — `orionfold codegen` (pure
  `render_thresholds_ts()` in `src/orionfold/codegen.py`) writes `web/src/features/proof/
  thresholds.generated.ts`, and `scoring.ts` **imports + re-exports** `DEFAULT_THRESHOLDS`/`TunableKind`
  from it (every consumer imports via `./scoring`, unchanged). The generated file is **committed, NOT
  gitignored** (FE builds with no prebuild step). `tests/unit/test_codegen.py` byte-diffs the committed
  file against a fresh render → **editing `rubric.py` without `orionfold codegen` fails CI**. The renderer
  is deterministic (`json.dumps` keeps `0.8` as `0.8`; TS union type derived from map keys). **keypoint
  MUST stay 0.8** (mock `467ddd96c9a5`). To change a threshold: edit `rubric.py`, run `orionfold codegen`,
  commit both. The BE `test_scoring.py` + FE `scoring.test.ts` freeze-tests stay as the value locks.
- **Threshold defaults (A2):** per-kind map `DEFAULT_THRESHOLDS {similarity:0.55, keypoint:0.8,
  judge:0.8}` is canonical in `scoring/rubric.py`; the FE consumes the codegen'd copy (see the codegen
  invariant above). A test on each side freezes the values. Settings sliders persist `threshold_<kind>` keys in the
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
- **Decide insight layer (Task 7, SHIPPED `30e5cf5` — `_SPECS/2026-06-23-decide-insight-layer.md`):**
  the scatter Y-toggle (`metric: "pass_rate" | "avg_score"` state in `FrontierScatter.tsx`, default
  Pass rate) keeps **recommended accent tied to `entry.recommended`**, NEVER to whichever point leads the
  *current* metric (a point can top Avg-score yet not be recommended — that disagreement is the insight;
  frozen by the `recommended dot draws the accent ring; a non-recommended metric leader does not` test).
  `buildScatterPoints(entries, metric)` reads `e.avg_score` when `metric==="avg_score"` and recomputes
  the frontier per metric; `recommended` always passes through unchanged. The explainer is **deterministic
  rule-based** `deriveDecideInsight(entries)` in `decideInsights.ts`, NEVER an LLM call (free + reproducible
  — the receipt repeatability promise); 5 ordered rules (all-errored / all-fail-but-real-scores→names the
  **avg-score** leader / clear-winner / tight-cluster / fallback); constants `REAL_SCORE_FLOOR=0.03`,
  `CLEAR_WINNER_GAP=0.2`. Explainer is **metric-agnostic** — it reasons about the run, so its text does NOT
  change when the toggle flips (frozen by a `textContent`-before/after test). Tones map `ok→--color-ok`,
  `warn→--color-warn`, `info→--color-ink-muted` — NEVER the cyan accent (the toggle's *active* state
  legitimately uses `--color-accent-strong` as an interactive-control affordance, distinct from the
  recommended-point accent). FE-only display of existing `LeaderboardEntry` fields — touches no
  backend/hash. NOTE: non-recommended dot tone still comes from `passRateTone(p.quality)` where `quality`
  is the *toggled* metric value — cosmetic and consistent with the displayed Y (diff-reviewer OK'd), not
  an accent violation.
- **Run-level cost ledger (Task 8, SHIPPED `055bd50`):** pure `costLedgerMath.ts`
  `buildCostLedger(leaderboard, results)` rolls `report.results` up per `candidate_id` — Σ
  `estimated_cost_usd` → candidate $, Σ `judge_cost_usd` → judge $, Σ `input/output_tokens`. Because the
  engine's `build_cost_summary` rolls up **the same rows**, the panel's per-candidate totals **sum back to
  `report.cost_summary` (= the DecisionSummary "Run cost" line) by construction** — frozen by a test that
  recomputes the expected sums from the raw rows. Share = `total/grandTotal` with a `grandTotal>0` guard
  (free run → 0, never NaN). **Leaderboard order is preserved** (recommended-first), NOT result-row order.
  `privacy` is **carried through `CandidateCost`** (from `LeaderboardEntry.privacy`) so the view's
  `ProviderTag` never guesses it. `CostLedger.tsx` is mounted in the **full-run branch ONLY** (the quick
  branch renders `QuickCompare`); it shows nothing on an empty leaderboard. DS: cost is neither verdict
  nor PASS → **neutral ink tokens ONLY, NEVER `--color-accent` or `--color-ok`**; share bar is
  `--color-ink-muted`; all `$`/token figures `tabular-nums`; judge column shows "—" when no judge ran;
  zero-total run shows "Free" + a "No spend — local or mock providers only" note. ⚠️ **The pure module is
  `costLedgerMath.ts`, NOT `costLedger.ts`** — a lowercase `costLedger.ts` would collide with
  `CostLedger.tsx` on macOS's case-insensitive FS (same reason `paretoFrontier.ts`/`FrontierScatter.tsx`
  differ by more than case). FE-only display of existing report fields — touches no backend/hash; mock
  `467ddd96c9a5` untouched.
- **Candidates add-key affordance (Task 9, SHIPPED `f65e686`):** `CandidatesView` renders from
  **`getSelection()` with `queryKey: ["selection"]`** (every catalog provider + `available` flag,
  sandbox-aware server-side) — NOT the available-only `getCandidates()` (now removed). The `["selection"]`
  key is **load-bearing**: `KeyEntry.onSuccess` invalidates `["selection"]`, so a saved key flips the card
  to available **live** — don't change the key. Three states keyed on `CLOUD_KEY_NAMES`: unconfigured
  **cloud** (`!available && CLOUD_KEY_NAMES[id]`) → reason + inline `<KeyEntry>`; unconfigured **local**
  (`!available`, no key) → start-host hint, **NO KeyEntry**; **available** → models listed. Reuses
  `KeyEntry` / `CLOUD_KEY_NAMES` / `ProviderTag` / `ProviderLogo` — do NOT rebuild gating or key entry.
  DS: the view itself introduces **NO `--color-accent`/`--color-ok`**; explanation text is
  `--color-ink-faint`/`--color-ink-muted`; identity `ProviderTag` stays neutral; the only accent is
  KeyEntry's **pre-existing** Save button (an interactive control, legitimately accent). FE-only display of
  the selection panel — touches no backend/hash; mock `467ddd96c9a5` untouched. ⚠️ The e2e smoke's
  `getByRole("main")` is safe ONLY because the hidden ProofCockpit `<main>` uses Tailwind `hidden`
  (`display:none`, excluded from the a11y tree) — if that view ever switches to `visibility`/`opacity`,
  the locator becomes strict-mode ambiguous (two `<main>`s).
- **Demo judge default (`50155bb`):** the bundled `is_sample` summarization demo defaults its scoring to
  the LLM judge via pure `prefersSampleJudge(dataset, judgeCell)` in `scoring.ts` — `true` **iff**
  `dataset.is_sample === true` AND `judgeCell` is a resolved **non-`mock_judge`** cell. The tri-state is
  load-bearing: `undefined` (default not resolved yet), `null` (no real judge, Sandbox OFF), and
  `mock_judge` (Sandbox keyless) **all return false** — so Sandbox keeps its keyless clear-winner demo and
  a keyless user stays on Auto, **never a silent Mock**. The consumer is a **`useRef`-latched `useEffect`**
  in `ScoringMethod.tsx` (`autoDefaultedFor`, keyed on `dataset.id`, set **before** `selectMethod` to
  prevent re-fire) that fires `selectMethod("judge")` once per sample-dataset arrival **only while
  `value === null`** — so it never clobbers a deliberate later switch back to Auto. It routes through the
  existing `if (judgeCell)` commit gate (A3), so it can only ever emit a real judge. The default is
  **FRONTEND-only** (operator's chosen layer): the keyless backend `default_rubric_for` is unchanged and
  still resolves the sample to **keypoint** — so anything that builds a `RunRequest` with `rubric:null`
  (incl. a future CTA that bypasses the component) gets keypoint, NOT judge. The catalog
  `investment-memo-summarization` (`is_sample:false`) is unaffected (stays Auto→Keypoint — frozen by the
  Sandbox e2e). FE-only display/selection logic — touches no backend/hash; mock `467ddd96c9a5` untouched.
- **Guided first-run CTA (Task 10, SHIPPED `5cc8ca0`):** the empty-state "Run the demo proof on real
  models" CTA **does NOT build a `RunRequest` directly** — it drives `ScoringMethod`'s state so the demo
  judge default (above) applies, then auto-runs. Pure `cheapCloudCandidates(panel, count=2)` in `scoring.ts`
  scans **available cloud** providers cheapest-first (cost_class `free<$<$$<$$$`, then recommended→latest;
  first N distinct candidate ids); **cloud-only** (Local/Mock are the Sandbox path). `ProofCockpit.tsx`:
  the CTA shows **only when `cheapCloud.length === 2`** (operator decision — the "real models" promise must
  be deliverable; keyless/Sandbox-only users keep the existing empty-state copy). `startGuidedDemo()`
  preselects sample + cheap cloud and arms — **it must NOT reset `rubric`** (the once-per-dataset judge
  latch is already spent on the sample's arrival; clearing the rubric would strand it null forever). The
  **auto-run effect fires `runMutation.mutate` only once `rubric.kind === "judge"`**, passing that exact
  non-null judge rubric — so the backend `default_rubric_for` = keypoint fallback is **unreachable** (this
  is the WS-E2-specific guard against the demo-judge-default warning). One-shot via `setDemoArmed(false)`
  before mutate (the `!demoArmed` early-return blocks any re-fire). It **disarms (no infinite spin)** if the
  rubric is non-null-non-judge (user pre-picked another method → judge can't arrive); safety holds — it
  never fires with the wrong rubric. Sample detected by `is_sample` (`datasets.data.find(d => d.is_sample)`),
  never a hardcoded id. The CTA button is interactive → legitimately `--color-accent-strong` (no `--color-ok`
  misuse). FE-only — touches no backend/hash; mock `467ddd96c9a5` untouched. The e2e CTA smoke asserts
  presence **matches** the live `/api/selection` cloud count (passes with or without keys) and **never
  clicks** a paid run — the click path is covered by unit tests + the live-browser run.

## Paste prompt for the next session
```text
Stage 3 is COMPLETE — the point queue is EMPTY. Tasks 1 (A1, 593d346), 2 (A2, f2b7e91), 3 (A3, 9e413d5),
4 (B, 5307ae5), 5 (C, 1864b35), 6 (D1, 0f83f9e), 7 (Decide insight layer, 30e5cf5), 8 (D2 cost ledger,
055bd50), 9 (E1 add-key affordance, f65e686), the demo-scorer-default fix (50155bb), 10 (E2 guided
first-run CTA, 5cc8ca0) AND 11 (WS-F DS application-consistency pass, 9820b5c) are ALL checked off. WS-A
+ WS-B + WS-C + WS-D + WS-E + WS-F + Task 7 done. There is NO next point-task.

▶️ ONLY DEFERRED BACKLOG REMAINS (operator picks). Do NOT auto-start anything — surface a row only when the
operator asks. The backlog is now a single prioritized table (## MERGED BACKLOG above). The top item is
**B6 — dual-distribution core + dogfooding loop** (NOW/HIGHEST; ADRs 0004/0005/0006 + the findings spec are
already written — brainstorm w/ operator + a vertical slice moving canonical logic into the Python core
remain). **B7 — private-strategy symlink migration** is HIGH and BLOCKS the final git remote+push. Packaging
(#7) is MED–HIGH and DOWNSTREAM of B6 (the prior "natural next = packaging" line was stale). git remote+push
is LAST, gated on BOTH B6→#7 AND B7 (operator directive). Brainstorm/scope FIRST on B6/#7/B5 (gate the
planning ceremony via AskUserQuestion per CLAUDE.md). main is local-only with all work committed; clean
shippable state. Per-item detail: _IDEAS/backlog-archive-2026-06-23.md (frozen); _IDEAS/backlog.md is now
an empty intake stub.

App up (REAL keys in .env.local, Sandbox OFF, no mocks; cost OK'd): API
`uv run orionfold dev --port 8790`; UI `VITE_DEV_PORT=5174 VITE_API_PROXY=http://127.0.0.1:8790
pnpm --dir web dev` (:5174, may land :5175 — open http://localhost:5174 NOT 127.0.0.1). Ours' health =
{"status":"ok",...}; an unrelated :8787 app is {"ok":true}.

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
display touching no backend/hash; Task 7 Decide insight layer = Pass-rate⇄Avg-score Y-toggle (default
Pass rate), buildScatterPoints(entries,metric) reads e.avg_score on "avg_score" + recomputes frontier,
RECOMMENDED ACCENT TIED TO entry.recommended NEVER the metric leader, decideInsights.ts
deriveDecideInsight = deterministic 5-rule explainer NEVER an LLM call, metric-agnostic so its text
doesn't change on toggle, tones ok/warn/ink-muted NEVER the cyan accent, FE-only; Task 8 cost ledger =
pure costLedgerMath.ts buildCostLedger(leaderboard,results) rolls report.results up per candidate_id so
per-candidate totals SUM BACK TO report.cost_summary / the verdict "Run cost" line BY CONSTRUCTION,
share has grandTotal>0 guard (free→0 not NaN), leaderboard order preserved + privacy carried not guessed,
CostLedger.tsx mounted FULL-RUN branch only, neutral ink ONLY never --color-accent/--color-ok, module is
costLedgerMath.ts NOT costLedger.ts (macOS case collision w/ CostLedger.tsx), FE-only no backend/hash;
Task 9 WS-E1 add-key affordance = CandidatesView renders from getSelection() with queryKey ["selection"]
(NOT the removed getCandidates) so a saved key invalidating ["selection"] flips the card live — don't
change the key; 3 states keyed on CLOUD_KEY_NAMES (unconfigured cloud → reason + inline KeyEntry;
unconfigured local → start-host hint NO KeyEntry; available → models listed), reuses
KeyEntry/CLOUD_KEY_NAMES/ProviderTag/ProviderLogo don't rebuild gating, the view introduces NO
--color-accent/--color-ok (only KeyEntry's pre-existing Save button is accent), FE-only no backend/hash,
e2e getByRole("main") safe only because hidden ProofCockpit uses display:none Tailwind `hidden`;
demo judge default (50155bb) = pure prefersSampleJudge(dataset,judgeCell) in scoring.ts true IFF
is_sample AND a resolved NON-mock_judge cell (undefined/null/mock_judge ALL false → Sandbox keeps its
keyless demo, keyless user stays Auto, NEVER silent Mock), consumed by a useRef-latched effect in
ScoringMethod.tsx (autoDefaultedFor keyed on dataset.id, set BEFORE selectMethod) firing
selectMethod("judge") once per sample arrival ONLY while value===null (never clobbers a later switch to
Auto), routed through the existing if(judgeCell) commit gate (A3) so it can only emit a real judge,
FRONTEND-ONLY (operator's layer) — backend default_rubric_for unchanged still resolves sample→keypoint so
a rubric:null RunRequest gets keypoint NOT judge, catalog investment-memo-summarization is_sample:false
unaffected, FE-only no backend/hash mock 467ddd96c9a5 untouched); Task 10 WS-E2 guided first-run CTA
(5cc8ca0) = empty-state "Run the demo proof on real models" DRIVES ScoringMethod's state (does NOT build a
RunRequest directly) so the demo judge default applies then auto-runs; pure cheapCloudCandidates(panel,2)
in scoring.ts scans AVAILABLE CLOUD cheapest-first (free<$<$$<$$$ then recommended→latest, 2 distinct ids,
cloud-only); CTA shown ONLY when cheapCloud.length===2 (honest "real models" promise; keyless/Sandbox-only
keep existing empty-state copy); startGuidedDemo() preselects+arms and must NOT reset rubric (judge latch is
once-per-dataset — clearing strands it null); auto-run effect fires mutate ONLY once rubric.kind==="judge"
passing that non-null judge rubric so backend keypoint fallback is UNREACHABLE, one-shot via
setDemoArmed(false) before mutate, DISARMS-no-spin if rubric non-null-non-judge (user pre-picked another
method); sample detected by is_sample never a hardcoded id; CTA button interactive → legit
--color-accent-strong no --color-ok misuse; e2e smoke asserts presence MATCHES live /api/selection cloud
count + NEVER clicks a paid run; FE-only no backend/hash mock 467ddd96c9a5 untouched.
```
