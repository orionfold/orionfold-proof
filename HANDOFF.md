# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-23 · **Stage 3 in progress — Task 1 (WS-A1) DONE + committed (`593d346`).**
Shipped the Models-mode **Task-instruction** field: optional textarea in Configure (Models mode) that
sets `RunRequest.system_prompt` on every selected candidate via `_resolve_candidates`. Verified
end-to-end on REAL models — a support-triage classify run scores **0/5 without** the instruction
(helpful prose) and **4/5 with** it (bare labels, clear winner), two distinct config_hashes; mock
matrix `467ddd96c9a5` unchanged. 281 backend + 121 frontend tests green, build clean, browser-confirmed
(field renders below Candidates in Models mode, hidden in Prompts mode). **Execute task 2 (A2) next
session** — but resolve the settings-persistence open question FIRST (see below). `main` local-only;
git remote/push stay queued LAST until packaging (operator directive)._

## ▶️ START HERE NEXT SESSION — execute task 2 (A2) from the NEXT TASKS queue

**Stage 3 is underway: one point-task per session.** Task 1 (A1) is checked off below. Read the
spec workstream before coding (`_SPECS/2026-06-22-trustworthy-proof-and-polish.md` — names exact
files/interfaces, fences out-of-scope, ends with a verify). Build smallest slice → verify (tests +
browser per CLAUDE.md) → check the box → re-handoff.

**Next up: Task 2 — WS-A2 (Per-method default thresholds + Settings sliders).** ⚠ **Resolve the
"Open question" (settings persistence surface) BEFORE coding** — Orionfold has no app-settings store
yet; default to a new `app_settings` SQLite table + `/api/settings` GET/PUT unless one is found. See
spec §WS-A2.

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
- [ ] **2 · A2 — Per-method default thresholds + Settings sliders** (HIGH). Per-kind default map
  (Similarity ~0.55, Keypoint/Judge 0.8) **+ user-configurable sliders in Settings** that override the
  defaults (persisted). Similarity card calibration note. _files:_ `domain/models.py:42` (map fallback) ·
  `ScoringMethod.tsx:38-40` (UI defaults from map) · **Settings view + a persisted settings store/endpoint**
  for the slider values · `SettingsView` component. _verify:_ bundled demo → clear winner with new
  defaults; changing a slider in Settings changes the prefilled threshold on the next run; backend test
  on the default map. _ref:_ spec §WS-A2 · _IDEAS issue #5. **(see Open question below — settings
  persistence surface needs a quick scoping decision.)**
- [ ] **3 · A3 — Cloud LLM judge + sane Sandbox-OFF default** (HIGH). Emit key-gated cloud providers as
  judge-eligible in the selection panel; with Sandbox OFF + a cloud key, default Run-on→Hosted + a real
  judge (never silently Mock); disable LLM judge with a hint when no real judge exists. _files:_
  `providers/selection.py` `selection_panel()` · `scoring.ts:41-93/84-85` · `JudgeFilter.tsx:50-59`.
  _verify:_ real cloud judge listed + selected by default; no-keys → disabled w/ hint; `scoring.test.ts`
  asserts no mock/unavailable default when a real judge exists. _ref:_ spec §WS-A3 · _IDEAS issue #6.
- [ ] **4 · B — check-hint → scoring-method mapping + selectable Exact card** (MED). Auto consults
  `check_hint` (exact→Exact, substring→Contains, numeric→exact-number, eyeball→judge); add a selectable
  "Exact" card; surface the resolution in the Auto card. _files:_ `scoring/rubric.py:64-68`
  `default_rubric_for` · `scoring.ts:4-8` `resolveAutoKind` · `ScoringMethod.tsx` (Exact card + Auto
  copy). _verify:_ Exact-hint dataset → Auto resolves Exact (visible); label run scores clean pass/fail;
  re-verify the A1 triage proof now scores correctly; mock `config_hash` unchanged. _ref:_ §WS-B · issue #3.
- [ ] **5 · C — Decision-question integrity (config + Quick)** (MED). Clear-unless-touched decision
  question on dataset change (add `decisionQuestionTouched` symmetric to `taskNameTouched`); on entering
  Quick mode clear the carried question + derive the Quick receipt headline from the Quick prompt.
  _files:_ `ProofCockpit.tsx:84-93/243-246` · `QuickCompare.tsx:33`. _verify:_ dataset switch → no stale
  headline; saved Quick receipt headline matches its prompt (check exported MD). _ref:_ §WS-C · issues #1/#2.
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

### Open question to resolve at the start of Task 2 (A2)
Operator added: **default thresholds should be user-configurable sliders in Settings.** Before coding
A2, confirm the **persistence surface** — Orionfold has no app-settings store yet (Settings today holds
provider keys + data-management + Sandbox toggle). Options: (a) a new `app_settings` SQLite table +
`/api/settings` GET/PUT (durable, matches local-first), or (b) reuse the existing settings mechanism if
one exists. Quick scoping check first; default to (a) if none exists. The per-method map stays the
*fallback*; slider values *override* per kind.

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
- **Proof Run setup:** shared `WorkflowStep`; `compareBy` is now `"models" | "prompts" | "quick"`;
  decision recipes render only in the Models branch (recipes.json loads at backend startup — restart
  to see edits).

## Paste prompt for the next session
```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001/0002/0003,
latest worklog 2026-06-22-icp-e2e-visual-verification).

PIPELINE (operator-chosen): _IDEAS/ → _SPECS/ → session point-tasks. Do stage 1 first, get sign-off,
then proceed. The shipped Datasets→Leaderboard→Quick-Compare arc is COMPLETE and was E2E-verified on
REAL models last session (no verification debt). NO code changed last session.

STAGE 1 — REVIEW _IDEAS/ : read _IDEAS/README.md (16-finding index + "highest-leverage theme") then
issues.md / feature-opportunities.md / design-system.md. Use AskUserQuestion to confirm scope+priority.
Strong default: the 3 HIGH issues are ONE story (cloud ICP's first real proof → "NO CLEAR WINNER"):
#4 no per-task instruction, #5 too-strict 0.80 Similarity default, #6 LLM-judge unavailable to
cloud-only — spec together with feature #1 (per-task instruction UI; system_prompt plumbing ALREADY
exists end-to-end, UI-only).

STAGE 2 — WRITE _SPECS/ : create top-level _SPECS/ and author a self-contained spec for the agreed
scope (CLAUDE.md "spec depth = blast radius × uncertainty": name files/interfaces, fence out-of-scope,
sequence a vertical slice, end with an e2e check). Cite the _IDEAS entries + their file:line anchors.
⏸ STOP for operator approval of the spec.

STAGE 3 — WORK BREAKDOWN : decompose the approved spec into point-sized, session-by-session tasks
(each = one focused vertical session, test + browser-verifiable). Write them as the "NEXT TASKS"
checklist in HANDOFF.md (goal · files · verify · _SPECS/_IDEAS ref), then execute ONE task per session,
checking off and re-handing-off each time. BRAINSTORM scope FIRST for anything non-trivial.

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
models|prompts|quick).
```
