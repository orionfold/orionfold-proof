# SPEC — Trustworthy First Proof + Comprehensive Polish

> **Status:** ✅ APPROVED by operator 2026-06-22 — proceeding to Stage 3 (work breakdown).
> **Date:** 2026-06-22 · **Author:** Claude Code (founding-engineer mode)
> **Scope decision (operator, 2026-06-22):** cover **all 16 `_IDEAS/` findings** comprehensively,
> prioritized **HIGH → MED → LOW**, grouped into related workstreams. Planning ceremony: **lightweight —
> this spec doc IS the plan** (no brainstorming/writing-plans skill).
>
> **Source of truth:** `_IDEAS/{README,issues,feature-opportunities,design-system}.md`. Every workstream
> cites the originating `_IDEAS` entry and **verified** `file:line` anchors (re-confirmed by read-only
> investigation 2026-06-22 — several `_IDEAS` claims were imprecise; corrections are flagged inline as
> **⚠ CORRECTION**).

---

## 0. How to read this spec

Six workstreams (**A–F**), ordered by lead severity. Each is independently shippable and maps to one
or more session-sized point-tasks in Stage 3. A workstream collapses *related* findings (shared
surface or shared root cause) into one story rather than tracking 16 flat entries.

| WS | Lead sev | Findings folded in | Theme |
|----|----------|--------------------|-------|
| **A** | HIGH | issue #4, #5, #6 · feature #1 | **Trustworthy first proof** — the "NO CLEAR WINNER" story |
| **B** | MED | issue #3 | **Scoring taxonomy** — unify check-hint ↔ scoring method (couples to A) |
| **C** | MED | issue #1, #2 | **Decision-question integrity** — stale at config + frozen into Quick receipt |
| **D** | MED | feature #2, #3 | **Cost & frontier** — Pareto scatter + run-level cost ledger |
| **E** | MED | feature #4, #5 | **Activation & onboarding** — inline add-key + guided first-run |
| **F** | LOW | DS #1–#5 | **Design-system application-consistency** |

**Global out-of-scope (fenced for the whole spec):** no new providers; no document ingestion / RAG;
no multi-user / auth / cloud DB; no agent orchestration; no receipt schema redesign beyond additive
fields. `RECEIPT_VERSION` only bumps if a workstream changes receipt *content* (called out per-WS).
All migrations remain append-only (next index **6**).

**Global invariants that MUST survive every workstream** (from `HANDOFF.md` "Key invariants"):
mock `config_hash 467ddd96c9a5` unchanged for the scored mock matrix; `system_prompt` added to
`config_hash` **only when set** (`engine.py:37-39`); Quick-Compare `mode`/`chosen_winner` on
`ProofRun` only and EXCLUDED from `config_hash`; `{kind:"none"}` → `score=None`/`passed=None` and
`build_leaderboard` stays `None`-safe; full-receipt HTML byte-identical (palette-count test);
accent/status split (cyan = interactive only, green = PASS only).

---

## WS-A — Trustworthy first proof (HIGH)

**The story.** A cloud-only ICP's *first real proof* is steered toward a discouraging "NO CLEAR
WINNER" three different ways. Fix them together so the out-of-box real-model experience reads as a
clear, trustworthy proof. Folds: issues #4, #5, #6 + feature #1.

### A1 — Per-task instruction field (Models mode) — _IDEAS feature #1, issue #4

**Goal.** Add an optional **Task instruction** field to the Proof Run Configure step (Models mode)
that sets `system_prompt` on every selected candidate, so classification/extraction tasks can be
proven (the models classify instead of "helping the user").

**⚠ CORRECTION to _IDEAS "UI-only".** `system_prompt` is plumbed through *providers / engine /
receipt*, but **Models-mode `RunRequest` does not carry it yet** — `build_candidates()` resolves bare
IDs with no override (`src/orionfold/providers/registry.py:133-173`). So this is **UI + a thin
backend seam**, not zero backend. Prompts mode already sets `system_prompt` per variant via
`expand_prompt_variants()` (`registry.py:182-208`, sets at `:204-206`).

**Files / interfaces to touch:**
- **Frontend state + payload:** `web/src/features/proof/ProofCockpit.tsx` — add `modelInstruction`
  state; include `system_prompt: modelInstruction || undefined` in the Models-mode `RunRequest`
  (built at `ProofCockpit.tsx:218-223`).
- **Frontend UI:** `web/src/features/proof/RunSetup.tsx` — add a `<textarea>` "Task instruction"
  below the Candidates picker (~`RunSetup.tsx:174`). **Mirror** the existing prompt textarea styling
  from `PromptVariants.tsx:76-83` (`inputCls` in `formStyles.ts`). Helper text + `{input}`/`{ticket}`
  guidance optional; placeholder e.g. *"Classify the ticket into exactly one of: billing, bug,
  how-to, feature-request, account-access. Reply with only the label."*
- **API schema:** `web/src/lib/api.ts` `RunRequest` — add optional `system_prompt: z.string().optional()`.
- **Backend request model:** the `RunRequest` Pydantic model used by `src/orionfold/server/routes.py`
  — add optional `system_prompt: str | None = None`.
- **Backend candidate resolution:** `routes.py:359-381` `_resolve_candidates` — when **no**
  `prompt_variants` **and** `body.system_prompt` set, loop `base` and set `c.system_prompt` on each.
  (When `prompt_variants` present, that path wins — instruction field is Models-mode only.)

**Reproducibility.** Because `engine.py:37-39` adds `system_prompt` to `config_hash` only when set,
a Models run *with* an instruction is a *different* proof (desired); a run *without* keeps
byte-identical hashes → mock `config_hash 467ddd96c9a5` invariant preserved.

**Out of scope (A1):** starter blueprint gallery (the "Classify into labels / Extract a field /
Summarize to one line" presets) — defer to a P1 follow-up; this task ships the raw field only.

**Verify (A1):** unit — backend test that `_resolve_candidates` sets `system_prompt` on every
candidate when provided and leaves hashes unchanged when absent; the mock matrix `config_hash` test
still passes. Browser — Models run on the triage dataset *with* the classify instruction now produces
non-zero passes (models emit bare labels). Receipt MD/HTML renders the instruction (`receipts/export.py`
already supports it).

### A2 — Realistic default Similarity threshold — _IDEAS issue #5

**Goal.** The flagship "Investment memo summarization" demo must produce a **clear winner** on real
models, not "NO CLEAR WINNER." Real paraphrased summaries score ~0.2–0.5 on lexical similarity, well
below the current **0.80** default.

**⚠ Anchor.** The `0.80` default lives in **two** places that must agree:
- Backend model default: `src/orionfold/domain/models.py:42` — `threshold: float = Field(default=0.8, …)`.
- Frontend hardcodes (per method): `web/src/features/proof/ScoringMethod.tsx:38-40` (keypoint /
  similarity / judge all set `threshold: 0.8`).

**✅ DECIDED (operator 2026-06-22): per-method default thresholds, made user-configurable via Settings
sliders.** Two layers:
1. **Built-in per-kind default map** (the *fallback*): **Similarity ~0.55** (typical for good
   paraphrased summaries), **Keypoint 0.8** (retain), **Judge 0.8** (retain).
2. **User-configurable override (operator add 2026-06-22):** expose these defaults as **sliders in
   Settings**, persisted, so a user can tune the per-method default threshold for their workflow. The
   slider value *overrides* the built-in map for new runs; the map remains the fallback when unset.

**⚠ Scope expansion — needs a persistence surface.** Orionfold has **no app-settings store today**
(Settings holds provider keys, data-management, and the Sandbox toggle — verify current `SettingsView`
+ any settings endpoint before coding). The sliders need durable, local-first storage. **Resolve at the
start of this task:**
- **(a, default if none exists):** new `app_settings` SQLite table (append-only migration, next index 6)
  + `/api/settings` GET/PUT returning a small typed settings blob (`{thresholds: {similarity, keypoint,
  judge}}`). Matches local-first.
- **(b):** reuse an existing settings mechanism if one already persists the Sandbox toggle — prefer this
  if found (avoid a parallel store).

**Files:**
- **Default map (fallback):** backend `src/orionfold/domain/models.py:42` — the `0.8` field default
  becomes the map's fallback; per-kind values resolve at rubric construction. Frontend
  `web/src/features/proof/ScoringMethod.tsx:38-40` — replace the three hardcoded `0.8`s with the
  per-kind map. **Keep backend + frontend maps in sync** (frontend unit asserts the expected map).
- **Settings sliders:** the `SettingsView` component (add a "Default scoring thresholds" section with a
  slider per method, 0–1) + the settings persistence (table/endpoint per (a)/(b)). On run setup,
  `ScoringMethod.tsx` reads the persisted override (falling back to the map) for the prefilled threshold.
- **Calibration note:** Similarity method-card copy in `ScoringMethod.tsx` ("0.80 is strict; ~0.55 is
  typical for good paraphrased summaries").

**Reproducibility note.** The *resolved* threshold is already recorded in the run's `rubric` →
`config_hash`, so a tuned slider value travels in the receipt as part of the proof's identity. The
slider only changes the *prefilled default*; it does not retroactively alter saved runs.

**Out of scope (A2):** per-dataset threshold overrides; auto-tuning from data; a thresholds-history UI.

**Out of scope (A2):** auto-tuning thresholds from data; per-dataset calibration UI.

**Verify (A2):** real-model run on the bundled dataset yields ≥1 candidate above threshold → a
non-"NO CLEAR WINNER" verdict. Backend test asserts the new default. **Receipt content unaffected**
(threshold already recorded in `rubric`); no `RECEIPT_VERSION` bump.

### A3 — Cloud LLM judge available + sane Sandbox-OFF default — _IDEAS issue #6

**Goal.** A cloud-only consultant (no Ollama/LM Studio) can run an **LLM-judge** proof, and with
Sandbox OFF the judge does **not** silently default to **Mock** (which contradicts "real evaluation").

**⚠ CORRECTION to _IDEAS "cloud excluded".** The judge picker is **not** a hardcoded
mock+ollama+lmstudio list. `filterJudgeModels()` (`web/src/features/proof/scoring.ts:41-93`) filters
`panel.providers` by a `(privacy, tier)` cell; the **default cell is Local + Economy, which only
yields the synthesized `mock_judge`** (`scoring.ts:48-60`). Cloud judges appear only when the user
flips "Run on → Hosted". The real defects are: (1) the **default lands a Sandbox-OFF user on Mock**,
and (2) cloud judge candidates may be **absent from the selection panel** the backend emits.

**Files / interfaces:**
- **Backend selection panel:** `src/orionfold/providers/selection.py` (`selection_panel()`) — ensure
  **key-gated cloud providers** (anthropic/openai/openrouter/gemini, built only when key resolves per
  `registry.py:40-100`) are emitted as **judge-eligible** entries so the Hosted cell is populated.
- **Frontend default:** `scoring.ts` (`filterJudgeModels` default-pick at `:84-85`) and/or
  `JudgeFilter.tsx:50-59` (Run-on default) — when **Sandbox is OFF and a cloud key exists**, default
  "Run on" to **Hosted** and pre-select a real configured judge instead of `mock_judge`. When NO real
  judge is available, **disable LLM judge** with a clear "add a provider key or start Ollama" hint
  rather than silently selecting Mock.
- **Reuse:** the candidate registry already key-gates cloud providers
  (`src/orionfold/providers/registry.py`) — reuse the same resolution for judges (no new credential path).

**Out of scope (A3):** judge ensembles / multi-judge; judge cost optimization beyond the existing
Cheapest/Balanced/Best tier toggle.

**Verify (A3):** with Sandbox OFF + a cloud key, the Judge-model dropdown lists a real cloud judge and
does **not** default to Mock; an end-to-end LLM-judge run grades with a real model. With no keys and
Sandbox OFF, LLM judge is disabled with the hint (not silently mocked). Frontend unit
(`scoring.test.ts`) asserts the default never lands on an unavailable/mock judge when a real one exists.

**WS-A end-to-end check.** Fresh DB + real keys + Sandbox OFF: (1) bundled demo → **clear winner**
(A2); (2) triage dataset + classify instruction → non-zero passes (A1); (3) LLM-judge run on a real
cloud judge succeeds (A3). The first real proof reads as trustworthy, not "no winner."

---

## WS-B — Scoring taxonomy unification (MED) — _IDEAS issue #3

**Goal.** A dataset's **check hint** should *drive* the run's resolved scoring method, and the two
vocabularies should reconcile. Today an "Exact match" hint does nothing — Auto resolves to Similarity,
mis-scoring exact labels.

**⚠ Confirmed facts.** `check_hint` is **display-only** today — `web/src/features/proof/tags.ts:13`
comment: *"the engine never reads these."* Allowed hint values: `"" | substring | numeric | exact |
eyeball` (`tags.ts:14-20`). Stored on the DB row + API `DatasetRow` only (`storage/db.py:49`,
`storage/repository.py:27`, `api.ts:66`). **Good news:** `RubricKind` already includes `"exact"` and
`"contains"` (`domain/models.py:15`) and the backend already implements those checks
(`scoring/rubric.py:24-41`) — they're simply not surfaced as UI scoring methods. So we **map**, we
don't build new checks.

**Files / interfaces:**
- **Auto resolution (backend):** `src/orionfold/scoring/rubric.py:64-68` `default_rubric_for` — extend
  to consult the dataset's `check_hint`: `exact → Rubric(kind="exact")`, `substring →
  kind="contains"`, `numeric → exact/normalized-number`, `eyeball → judge` (or leave Similarity),
  else current keypoint/similarity fallback.
- **Auto resolution (frontend mirror):** `web/src/features/proof/scoring.ts:4-8` `resolveAutoKind` —
  mirror the same hint→kind mapping so the Auto card shows the truth.
- **Surface the link:** in the Auto method card (`ScoringMethod.tsx`), show *"from your dataset hint:
  Exact match → Exact"* so the resolution is visible.
- **✅ DECIDED (operator 2026-06-22): expose Exact as a selectable method.** Add an "Exact" card to
  `ScoringMethod.tsx` (the backend `kind="exact"` already exists at `domain/models.py:15` and
  `scoring/rubric.py:24-41`), so the user can explicitly pick exact/normalized-equality scoring — this
  closes the hint↔method vocab gap the ICP noticed, not just the Auto resolution.

**Out of scope (WS-B):** a numeric-tolerance check beyond simple normalized equality; redesigning the
hint vocabulary itself.

**Coupling note.** WS-B makes A1's classification proof score correctly: instruction (A1) makes the
model emit a bare label; exact scoring (B) grades it cleanly. Ship A1 → B → re-verify the triage proof.

**Verify (WS-B):** dataset frozen with "Exact match" hint → Auto resolves to Exact (visible in the
card); a label run scores clean pass/fail, not partial Similarity. Backend test on `default_rubric_for`
for each hint value. Mock matrix `config_hash 467ddd96c9a5` unchanged (mock dataset has no hint, so
Auto still resolves Similarity).

---

## WS-C — Decision-question integrity (MED) — _IDEAS issues #1, #2

**Goal.** The **Decision question** (which "headlines the receipt") must never silently contradict the
task/dataset/prompt — neither at config time (#1) nor frozen into a saved **Quick** receipt (#2). One
fix, two surfaces.

**⚠ Confirmed mechanism.** Task name auto-syncs from the dataset until touched
(`ProofCockpit.tsx:84-88`, `taskNameTouched` at `:66/:90`); the **decision question is never
re-derived or cleared** on dataset change (`ProofCockpit.tsx:89-93`). Quick mode carries the prior
Models-run `brief` unchanged — `QuickCompare.tsx:33` headlines with
`report.run.brief.decision_question`, and the promote/restore path (`ProofCockpit.tsx:243-246`) never
touches `brief`. So a stale question persists into the saved Quick receipt.

**Files / interfaces:**
- **Config-time (#1):** `web/src/features/proof/ProofCockpit.tsx` — on dataset change, either
  **clear** `decision_question` (and show the recipe placeholder) or **re-derive** it like task name.
  Recommended minimal fix: clear on dataset change unless the user has touched it (add a
  `decisionQuestionTouched` flag symmetric to `taskNameTouched`). At minimum, surface a mismatch
  warning before Run.
- **Quick mode (#2):** `ProofCockpit.tsx` — when `compareBy` switches to **"quick"**, clear the
  carried-over `decision_question`; **derive the Quick receipt headline from the Quick prompt** (or
  prompt a short title on Save). Quick mode has no dataset to anchor a title, so derivation-from-prompt
  is the right default.

**Receipt impact.** No schema change — these are *content correctness* fixes (the fields already
exist). No `RECEIPT_VERSION` bump. (Existing already-saved stale receipts are historical; optional
one-off note in BACKLOG, not in scope.)

**Out of scope (WS-C):** a full "rename/retitle a saved receipt" feature; backfilling past receipts.

**Verify (WS-C):** switch dataset → decision question clears/re-derives (no contradiction); enter Quick
mode → no stale question; save a Quick receipt → headline matches the Quick prompt (verified in the
exported MD Decision/Task lines). Frontend unit on the clear/derive logic.

---

## WS-D — Cost & frontier (MED) — _IDEAS features #2, #3

**Goal.** Make the central "which is the best cost/quality trade-off?" decision visible at a glance,
and give the consultant a clear per-provider spend breakdown. Reuse peer-project code (both reuse roots
**confirmed to exist**).

### D1 — Pareto cost-vs-quality frontier scatter — _IDEAS feature #2

**Files / reuse:** new `web/src/features/proof/FrontierScatter.tsx` adapted from
`/Users/manavsehgal/Developer/ainative-business.github.io/arena-app/src/components/arena/FrontierScatter.jsx`
(**exists** — Pareto skyline `paretoFrontier()`, group coloring, flagship marker). Render beneath the
leaderboard in the Decide step. **Axes:** cost (x) × pass-rate or avg-score (y). **DS rule:** reserve
`--color-accent` for the *recommended* point only; status colors for pass/fail only.

### D2 — Run-level cost ledger / spend panel — _IDEAS feature #3

**Files / reuse:** a compact cost panel (per-provider tokens + $, run total, optional project running
total) in the Inspector or under the leaderboard. Adapt from
`/Users/manavsehgal/orionfold/ainative/src/lib/usage/ledger.ts` + `src/components/costs/cost-dashboard.tsx`
(**both exist**); micro-viz from ainative `src/components/charts/{sparkline,mini-bar,donut-ring}.tsx`.
Data source: `RunCostSummary` already on the report (`domain/models.py`), candidate/judge/total already
computed by the engine.

**Out of scope (WS-D):** historical cross-run cost charts beyond a simple running total; budget alerts;
a standalone Costs route.

**Verify (WS-D):** scatter renders the candidates with a correct Pareto frontier; the recommended point
is the only accent. Cost panel sums match the verdict banner's existing "Run cost" line. Vitest on
`paretoFrontier()` adaptation + a Playwright smoke that the scatter mounts on a populated run.

---

## WS-E — Activation & onboarding (MED) — _IDEAS features #4, #5

**Goal.** Turn dead-ends into activation: explain *why* a provider is/isn't available and offer a
one-click first real proof.

### E1 — Candidates inline "add key / start host" — _IDEAS feature #4

**Files / reuse:** `web/src/features/proof/CandidatesView` (catalog) — list **known** providers with a
quiet "Add key in Settings →" (or inline key field) for unconfigured cloud, and a "Start Ollama / LM
Studio" hint for local. Reuse the keyless-default + reveal-on-configure pattern from
`arena-app/src/components/arena/OpenRouterKeySettings.jsx`. The selection panel already knows gated
providers (`selection.py` emits gated entries; `scoring.ts` already surfaces gated judge rows — reuse).

### E2 — Guided first-run / "Run the demo proof on real models" — _IDEAS feature #5

**Files:** a first-run CTA on the empty Proof Run state (bundled dataset + 2 cheap cloud candidates +
a scoring default that *actually passes* — depends on **A2**), producing a real winner receipt in
~30s. Reuse the stepper pattern; pairs with WS-A's recalibration.

**Out of scope (WS-E):** a full blueprint/template gallery; multi-step onboarding wizard; inline key
*entry* if it complicates the secrets-guard surface — prefer "Add key in Settings →" deep-link first.

**Verify (WS-E):** an unconfigured provider shows the add-key affordance and explains its absence;
first-run CTA runs a real demo proof end-to-end to a clear-winner receipt (depends on A2). Playwright
smoke on the empty-state CTA.

---

## WS-F — Design-system application-consistency (LOW) — _IDEAS DS #1–#5

**Goal.** Close gaps between the live UI and the reference component kit
(`/Users/manavsehgal/orionfold-design-system/mocks/design-reference/2026-06-20/{candidate-1,components}.html`).
The token *foundation* already matches (`#14c8c0` cyan, Geist) — these are **application-consistency**
fixes, not color drift.

| # | Finding | Verified anchor | Fix |
|---|---------|-----------------|-----|
| F1 | Bundled dataset metadata line thin ("5 examples" only) | **⚠ root cause:** `insert_sample_dataset()` doesn't set `created_at/source/check_hint` (`src/orionfold/storage/repository.py:112-119`; seed `sample_data.py:25-29`). Card renders correctly (`DatasetsView.tsx:80-98`) — it just has no data. | **Backend seed fix:** populate `created_at/source/check_hint` on the seeded sample so its card matches user sets. Append-only migration if needed (next index 6). |
| F2 | Leaderboard headers not sortable | `Leaderboard.tsx:26-36` plain `<th font-medium>`, no sort; reference `.tbl th.sortable` + `aria-sort` + `.sort-ar` (`components.html:399-405`). | Adopt the reference sortable pattern: client-side sort, `aria-sort` a11y, accent on active column. **Keep** the documented default ranking sort key as initial state. |
| F3 | Headers sans `font-medium`, not mono micro-caps | same `Leaderboard.tsx:26-36`; reference `.tbl thead th { font-family:var(--mono); font-size:10px; uppercase; letter-spacing:0.06em; … }`. | Apply mono micro-caps to leaderboard (and other data-table) headers for the "receipt voice." |
| F4 | Mock badge styles like Cloud | **⚠ correction:** code already keeps the accent/status split; the real gap is Mock + Cloud both use `text-(--color-ink-muted)` (`badges.tsx:19-25`). | Give Mock a distinct token treatment (muted/warn-leaning per reference `.badge.warn` `components.html:382-388`) so simulated ≠ real at a glance. |
| F5 | Inspector column empty on Settings/Datasets/Candidates | **⚠ architectural:** those routes use `ViewShell` (no inspector pane; `ViewShell.tsx:16`), cockpit uses a 2-col grid (`ProofCockpit.tsx:154`). | Either widen `ViewShell`'s main column, or add an optional right-rail slot for lightweight context (e.g. Datasets: selected-dataset summary; Settings: "everything stays on this machine" note). |

**Out of scope (WS-F):** a shared token-driven badge/chip/bar component kit refactor (BACKLOG #5 "DS-skin
polish") beyond the five targeted fixes above; receipt proof-seal stamp.

**Verify (WS-F):** bundled dataset card matches user-dataset metadata line + hint chip; leaderboard
sorts by any column with `aria-sort` and accent on active, default ranking preserved on load; headers
render mono micro-caps; Mock badge visually distinct from Cloud/Local; inspector-less routes no longer
read as unbalanced. Visual check in both light + dark via `browser-visual-verification`. **Full-receipt
HTML byte-identical** (F-changes are app UI, not receipt HTML — palette-count test must still pass).

---

## Decisions (resolved by operator 2026-06-22)

1. **A2 threshold strategy:** ✅ **per-method default thresholds** (Similarity ~0.55, Keypoint/Judge 0.8)
   via a per-kind default map + Similarity calibration note, **made user-configurable as persisted
   Settings sliders** (operator add 2026-06-22; needs an app-settings persistence surface — see A2). *(see A2)*
2. **WS-B Exact method exposure:** ✅ **add the selectable "Exact" card** (backend kind already exists). *(see WS-B)*
3. **C decision-question fix:** ✅ **clear-unless-touched** (symmetric to task name); re-derivation needs
   a dataset→question heuristic we don't have. *(see WS-C)*
4. **Sequencing:** ✅ **strict severity order** WS-A→B→C→D→E→F; the HIGH story is the demo-blocking thread. *(see breakdown below)*

---

## Suggested Stage-3 work breakdown (point-sized sessions)

Each = one focused, vertical, test-+-browser-verifiable session. Operator approves the spec first;
these become the `HANDOFF.md` "NEXT TASKS" checklist.

1. **A1** — Models-mode Task-instruction field (UI + `RunRequest`/`_resolve_candidates` seam). *verify:*
   backend hash test + browser classify run shows passes.
2. **A2** — Per-method default thresholds (map) **+ user-configurable Settings sliders** (persisted;
   needs an app-settings store — scope (a)/(b) first). *verify:* bundled demo → clear winner; slider
   change alters the next run's prefilled threshold.
3. **A3** — Cloud judge in selection panel + sane Sandbox-OFF default. *verify:* real cloud judge run; no Mock default.
4. **B** — check-hint → scoring-method mapping (+ optional Exact card); re-verify the A1 triage proof scores clean.
5. **C** — Decision-question integrity at config + Quick (clear/derive). *verify:* no stale headline in saved Quick receipt.
6. **D1** — Pareto frontier scatter (reuse Arena). 7. **D2** — Cost ledger panel (reuse ainative).
8. **E1** — Candidates inline add-key affordance. 9. **E2** — Guided first-run CTA (depends on A2).
10. **F1–F5** — DS consistency pass (may split: F1 seed; F2/F3 leaderboard table; F4 badge; F5 layout).

> Tasks 1–5 are the demo-critical HIGH/MED thread; 6–10 are value-add MED/LOW. One task per session,
> check off + re-handoff each time.

---

## End-to-end acceptance for the whole spec

Fresh `~/.orionfold/proof.db`, real keys in `.env.local`, **Sandbox OFF**:
1. Guided first-run CTA → bundled demo → **clear winner** receipt (~30s). *(A2, E2)*
2. Import a label dataset with "Exact match" hint → Auto resolves Exact → classify-instruction run →
   **clean pass/fail** leaderboard. *(A1, B)*
3. LLM-judge run on a real cloud judge succeeds; never silently Mock. *(A3)*
4. Leaderboard sorts by any column; Pareto scatter shows the trade-off; cost panel matches the banner. *(D, F2/F3)*
5. Quick A/B → saved receipt headline matches its own prompt. *(C)*
6. Every exported receipt (MD/HTML/JSON) is **secret-free**; full-receipt HTML byte-identical (palette test). *(invariants)*
7. `uv run pytest`, `pnpm test`, `pnpm build`, Playwright happy-path all green.
