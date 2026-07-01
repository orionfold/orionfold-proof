---
paths:
  - "src/orionfold/**"
  - "web/**"
---
# Key invariants to NOT regress

> Project-lifetime contracts that must survive every change. Relocated 2026-06-30 from
> HANDOFF.md (it had grown to 325 lines; these are standing law, not session continuity).
> Path-scoped so they auto-load when editing `src/orionfold/**` or `web/**`.

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
- **Proof field note (B6 Layer A, SHIPPED `112776e`):** `orionfold field-note <run_id> [--out]` is a
  **thin CLI shell** over the pure core fn `build_field_note(report)` in `receipts/field_note.py`
  (graduated to `receipts.__all__`; the CLI is its second consuming use, ADR-0004 §7). It reads **only a
  stored `ProofReport`** → no scoring/hash path, no migration, no FE; **mock `467ddd96c9a5` untouched by
  construction**. **The receipt is NOT touched** — `export.py` is unedited, `RECEIPT_VERSION` stays 8, the
  byte-identical palette guard stays green; the field note is a **sibling** module that *reuses*
  `export.to_markdown` for the evidence body (H1 `# Proof Receipt`→`## Evidence` via a single `.replace`,
  guarded by `test_field_note_has_a_single_h1…`) — **never a second copy** of receipt logic. **Frontmatter
  is hand-rendered** (NOT `yaml.dump`) so output is byte-deterministic and `import orionfold` carries no YAML
  dep; every value is **derived** from the report (nothing invented). `recommended` reads the leaderboard's
  own `recommended` flag (single source of truth — never re-derives the verdict); `fmt_check` is true iff
  `rubric.kind ∈ {exact, contains}` (ADR-0005 §4 format-vs-correctness). **Figures** (`receipts/figures.py`,
  `pareto_svg`/`pass_rate_svg`, NOT in `__all__`) are **pure-Python inline SVG** (no browser, no charting
  lib): the Pareto kernel `_pareto_frontier` is a **faithful port of `web/.../paretoFrontier.ts`**
  (lower-cost-better, tier-resolved equal-cost ties — do NOT "simplify" the dominance rule). **DS accent/
  status split held**: recommended = the ONLY `--color-accent`; pass-rate bars `--color-ok`; other dots
  status-toned (ok/warn/danger via `_pass_rate_tone`); all colours are `var(--color-*)`. **Determinism**:
  every emitted number routes through `_num()` (fixed 2-dp, trailing-zeros-trimmed) — do not interpolate raw
  data floats into the SVG. **Graceful degrade**: pass-rate bars omitted when `report.run.rubric.kind ==
  "none"` (a quick/unscored run rolls pass-rate to 0, indistinguishable from "scored, all failed" — read the
  KIND, never draw a fake bar); the scatter omits its dashed frontier polyline when `<2` frontier points or
  no cost spread (dots still render). The package **does NOT author** the `## Why this can be trusted`
  narrative — it emits a stub with `<!-- author: … -->` markers (Layer B / the operator fills it).
- **Proof field note Layer B (B6 Slice 2, SHIPPED `bf6ab72`):** the **dev-only**
  `.claude/skills/proof-field-note/` skill — scaffold-from-run (`orionfold field-note`) → operator authors
  the `## Why this can be trusted` narrative by hand → `scripts/emit_bundle.py` packages a website-ready
  bundle. **The skill edits NO `src/`** — it only *consumes* the public CLI, so mock `467ddd96c9a5`, the
  receipt, and `RECEIPT_VERSION` are untouched **by construction**. `emit_bundle.py` is **stdlib-only**
  (no package import). Invariants do NOT regress: (1) the **marker guard** must refuse (non-zero, no bundle)
  while `<!-- author: replace this section -->` survives — never weaken to "trust the operator authored it";
  (2) **no frontmatter rewrite** — Layer A's frontmatter is a valid `story`-collection superset
  (`~/orionfold/website/src/content.config.ts`), copied verbatim (if the website ever makes `story`
  `.strict()`, that's a website-side change, not a reason to strip keys here); (3) **figures stay inline**
  (parent spec §3 chose inline SVG so they theme with the site — never extract to `.svg` files);
  (4) **emit only to gitignored `_field-notes/`** — no cross-repo writes (the operator syncs to the website
  by hand); (5) the **secret backstop** regexes mirror the repo's `secrets-guard.py` `SECRET_PATTERNS`. The
  self-test (`scripts/test_emit_bundle.py`) runs directly (NOT pytest — outside the package suite) and
  assembles its fake key at runtime (no key-shaped literal, since the secrets-guard hook blocks both literals
  and `*_KEY/*_SECRET/*_TOKEN` assignments). **B7 deferral:** the skill is a **real dir** today; the
  symlink-into-strategy migration lands with B7 (noted in the SKILL.md header).
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

