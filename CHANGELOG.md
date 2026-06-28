# Changelog

All notable changes to **Orionfold Proof** (`orionfold-proof`) are recorded here. The
format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project aims
for [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Host telemetry — Proof now shows the hardware a proof ran on.** A best-effort, cross-platform
  host profile (chip / cores / unified memory / OS / GPU label / serving runtime) drives an
  always-on Host signal, and a new `## Hardware` receipt stanza records "reproduced on hardware
  like X" in Markdown / HTML / JSON. The hardware context is **excluded from `config_hash`** — the
  same model / prompt / dataset hashes identically on a Mac or a Linux box. Honest about absence:
  no host → no stanza, unsampled → "not captured", GPU "unavailable" without the opt-in.
- **Live run telemetry.** A background sampler reads CPU / unified-memory / serving-RSS / GPU
  during a run and streams them over `GET /api/telemetry/stream`; the cockpit gauges go live while
  the hardware is under load and return to rest when the run ends. Reads OS stats only — never
  touches provider threads or `config_hash`.
- **Apple-Silicon GPU utilization (opt-in).** A Settings toggle (default off, consent-gated
  `sudo -n powermetrics`) surfaces real GPU residency during a run.
- **Arena-shape cockpit redesign (in progress).** A compact top app bar (Prove · Datasets ·
  Receipts · Settings, with iconography) + a full-width, always-on horizontal telemetry rail +
  full-width canvas, replacing the old three-column grid. The rail is a standing instrument cluster
  on every screen: host CPU / GPU / memory trends (this-run-vs-last, SVG sparklines), warm runtime,
  live run progress (pass-rate-so-far + candidates done), and cost.
- **Cost rollup (read-only, hash-inert).** A new `GET /api/cost-summary?window=today|all`
  aggregates persisted per-run costs into a windowed **eval + judge split** plus a cost / pass-rate
  trend series — driving the rail's "Cost today" (split) and "Cost to date" cells. A pure rollup
  over existing `cost_summary` fields (same pattern as `track_record`): re-runs no scoring, touches
  no `config_hash`, no receipt byte, no migration. Un-picked quick-compare drafts are excluded, so
  the cost reconciles 1:1 with the Runs list.
- **Proof Receipt visual redesign (v12).** The exported HTML receipt — the flagship deliverable —
  now leads with a verdict hero (mono eyebrow + verdict headline + a `pass% · n/N · cost` metric
  spine), embeds the pass-rate and cost-vs-quality SVG figures (with subtle gridlines + dot labels),
  splits the cost ledger into an eval/judge/total block, and renders structured "retrieved context"
  inputs as a Question + progressive-disclosure source cards (reusing the cockpit's parser, native
  `<details>`, no JS). Shares the orionfold.com receipts vocabulary while keeping the cockpit's
  evidence genre. Presentation only — `config_hash` and the receipt data are byte-identical;
  `RECEIPT_VERSION` 11→12 signals the render change.
- **Receipts screen redesign (bento + folded Track Record).** Receipts now opens with a dense
  above-the-fold bento masthead — Latest proof, Cost today (eval + judge split), Cost to date,
  library counts, and a wide pass-rate-vs-cost trend chart — over a `[ Runs | Track Record ]`
  toggle. Runs is a compact sortable table (verdict · pass · scored-by · cost · when · export · open)
  with checkbox compare, replacing the old tall cards. Track Record (formerly its own tab) folds in
  as dense 2-up dataset standings cards. Telemetry-rail cost / result cells deep-link into the
  matching mode. Presentation-only — no scoring / receipt / hash change.
- **Receipt detail is its own screen (L3), absorbing the old Inspector.** Opening a run from the
  Receipts table lands on a full detail view carrying the v12 receipt plus the complete record —
  run config + config hash + Hardware stanza, the full leaderboard + cost-vs-quality frontier + the
  eval/judge cost ledger, and the failure cases with an inline input/expected/output/error pane. The
  Prove canvas is now a single full-width working surface (the transitional right-side Inspector is
  gone), with a "View full receipt →" one-click into the detail screen. Presentation-only.
- **Receipt detail is now tabbed.** The L3 detail view splits its record across tabs — Receipt
  (the artifact, maximized to fill the fold) · Run config · Leaderboard · Cost · Failure cases — so
  no single panel needs a long scroll; the receipt export links (Markdown / HTML / JSON) ride the
  tab row. Analysis tabs show only for a scored run. Presentation-only.
- **Consistent screen layout.** Every view (Prove · Datasets · Receipts · the receipt detail ·
  Settings) now centers in the same `max-w-[96rem]` reading measure with matching padding, instead
  of left-jamming or spanning edge-to-edge. The blueprint draughting-grid background reads at a
  calm, just-perceptible alpha in whitespace.
- **Settings is a full-width bento.** The Settings sections tile into a responsive grid at the
  same width as every other view — Appearance · Runtime (the Sandbox + GPU toggles) · Default
  scoring thresholds · Data management (Seed / Remove / Clear) — each an icon-led card, so the
  width carries density instead of stretched single-toggle rows. Layout only; every control kept.
- **Telemetry rail hydrates at rest.** The always-on rail no longer reads empty until a run fires
  this session — it now fills from history on load. "Last result" / "Last receipt" hydrate from the
  newest stored run via a read-only `GET /api/runs/latest` (the run open in the cockpit still wins
  when present); the dimmed "last run" CPU / GPU / memory sparklines redraw from a persisted
  per-bucket trend series carried on the stored run (additive, hash-inert — no migration); and the
  GPU cell shows a real idle % at rest via a single throttled `GET /api/telemetry/gpu-idle` read,
  gated server-side behind the existing opt-in (NVIDIA tried unprivileged first; the macOS
  powermetrics read never fires without consent), polled at most every 30s and only while the tab is
  visible and no run is active. The rail sparklines now fill to the baseline (a light shaded area
  under the trend line) so a sparse trace reads as a mound rising from the x-axis, not a line
  floating at an unclear elevation. Presentation-only — telemetry stays out of `config_hash`.
- **Turnkey GPU telemetry setup — `orionfold gpu enable | status | disable`.** Enabling
  Apple-Silicon GPU sampling no longer means hand-editing sudoers and fighting `visudo`. The new CLI
  group installs a NOPASSWD drop-in scoped strictly to `/usr/bin/powermetrics` (written via
  `tee` + `chmod 0440` + `visudo -cf`, with automatic rollback if validation fails so a broken
  sudoers file is never left on disk), flips the opt-in, and confirms reachability; `status` reports
  opt-in / rule-present / reachable, and `disable` removes the rule. Settings now shows a live
  "✓ GPU ready" / "⚠ Needs setup — run `orionfold gpu enable`" badge under the GPU toggle (fed by a
  read-only `GET /api/telemetry/gpu-setup` probe), closing the gap where flipping the toggle alone
  silently read "unavailable". Presentation-only — telemetry stays out of `config_hash`.

### Fixed

- **Cockpit follows the dataset on change.** Loading a past bench run then selecting a different
  dataset kept the stale bench rubric (tripping the corpus-binding gate on Run), a stale "Rerun
  proof" button, and a stale "Scored by the bench" line. Switching datasets now resets to a fresh
  setup — rubric re-defaults, the loaded result clears, the recipe resets — and the scoring cards
  re-highlight to match. Presentation-only.

- **GPU opt-in now reads real utilization on macOS Sequoia.** The `powermetrics` parser only
  matched the old `GPU active` / `GPU Busy` labels; Sequoia (15.x) emits
  `GPU HW active residency: NN.NN% (...)`. The parser now matches all three label forms.
- **Live gauges fire mid-run.** The rail gated "run active" on the finished report (which only
  exists *after* a run), so the gauges never lit up during one. A real `runActive` signal is lifted
  from the in-flight mutation, so the gauges light exactly while the hardware is under load.
- **Serving-RSS sums the runtime's process tree.** Ollama is a client/server split — the model
  weights live in an `ollama runner` child, not the name-matched shim — so a multi-GB model
  under-reported as ~0.1 GB. RSS now walks the parent→child process tree from each name-matched
  seed and sums it, with a plausibility floor that reports honest absence over a misleading number.

## [0.1.3] — 2026-06-26

### Fixed

- **OpenRouter real cost is now reported (was `$0.00`).** The OpenAI-compatible provider
  discarded the real billed amount OpenRouter returns in `usage.cost` and re-estimated from a
  static price table that returns `0.0` for any model id it doesn't know, so custom OpenRouter
  models read "$0.00 / Free" on real paid calls. `build_result` now prefers the real
  `actual_cost_usd` when the response carries one, falling back to the `price × tokens`
  estimate table otherwise (and `z-ai/glm-4.6` is now priced). Cost-vs-quality and the run-cost
  ledger now show a custom model's true cost and its real share of the run. OpenAI / LM Studio
  are unchanged (they return no `usage.cost`). Cost is not part of `config_hash`, so freezes are
  unaffected.
- **Leak gate no longer false-flags a correct refusal that names a sensitive file.** The
  governance bench scored a refusal that merely *named* a sensitive file (e.g. `.env.local`) as
  `private-state-leak`. The risky-pattern set is split into content-snippets (which fire alone)
  vs secret-names (which fire only alongside a co-located `NAME=value`): naming a secret while
  refusing now passes; emitting a value still fails. Provably inert on the published 21-row
  governance lock.

### Added

- **Post-receipt false-positive / false-negative review pass (receipt schema v10).** A
  deterministic, no-LLM review annotates a failed row whose verdict is *possibly* wrong, inline
  under the affected failure case. The deterministic score stays authoritative — the review only
  annotates, never overrides pass/fail. Two narrow rules: a bench leak that fired only on the
  opaque-token heuristic on an otherwise-clean refusal, and an exact/contains miss that
  case+punctuation normalization would flip to a pass. `RECEIPT_VERSION` 9 → 10.
- **Browsable Corpora list on the Datasets screen.** A compact "Corpora (N)" section lists each
  governed corpus (name, description, manifest source count) and opens it directly, independent
  of the bench `corpus` badge — so a corpus not bound to a bench dataset is no longer invisible
  in the cockpit. Renders nothing when there are no corpora.
- **Curated OpenRouter model picker** — the latest frontier set (GLM 4.6 default, GLM 5.2,
  DeepSeek V4 Pro, Kimi K2.6, Qwen3.5 397B, Llama 4 Maverick, Grok 4.3, GPT-5.5) with live
  slugs and pricing.

### Changed

- **Internal cockpit refactor (no behavior change):** the retrieved-context source cards in the
  bench example view and the corpus browse view now share one presentational `SourceDisclosure`
  primitive (collapsible disclosure shell), while each surface keeps its own data type and
  cited-marker semantics.

## [0.1.2] — 2026-06-26

### Changed

- **README reframed value-led** (per the website's `/proof/` copy alignment). Dropped the
  free-vs-paid comparison table and demoted "open source" from a hero claim to a quiet
  transparency note ("read it, run it, verify the proof before you buy"). The value hero
  (prove which AI you can trust, rerun it) and the headline 18 / 21 governance receipt stay
  as the pitch. The free/paid boundary remains stated as a factual footnote, not a selling
  table, so the README, PyPI long-description, and orionfold.com/proof read as one voice.
  No code or API change.

## [0.1.1] — 2026-06-26

### Changed

- **README is now a funnel surface for the flagship.** The GitHub and PyPI front door leads
  with the brand promise ("prove which AI you can trust"), opens with `pip install
  orionfold-proof`, puts the headline governance receipt (Advisor 4B scoring 18/21 vs an
  8x-bigger model, config hash `50c38b0b7439`) above the fold as the credibility anchor, and
  adds a free-vs-paid table plus two CTAs to [orionfold.com/proof](https://orionfold.com/proof/).
  The honest task-specific caveat (the big models are smarter in general) stays in the copy.
  Image and reference links are absolute so the README renders cleanly as the PyPI
  long-description. No code or API change.

## [0.1.0] — 2026-06-25

> First public release to PyPI: `uv tool install orionfold-proof` → `orionfold up`. The local-first
> Proof Receipt — compare AI models/prompts/workflows on your own task and export a signed, rerunnable
> receipt. Apache-2.0 open engine; the cockpit rides embedded in the wheel (no Node at runtime). All
> v0 scope below ships in this release.

### Added

- **Meaning-aware scoring.** The receipt no longer fails a correct summary just because it is worded
  or formatted differently from the expected text. Two scoring methods join the v0 similarity rubric:
  **keypoint coverage** (deterministic, keyless) scores the fraction of authored required facts an
  output contains and is now the **default** when a dataset carries keypoints; an opt-in **LLM judge**
  grades meaning against the expected answer (0..1). A new **Scoring method** control in the Proof Run
  setup lets you pick Auto · Keypoint · Similarity · LLM judge, and choose a judge model — reusing the
  same availability + inline-key machinery as the candidate picker (a keyless **Mock judge** is always
  offered for deterministic, no-key runs). The bundled demo dataset ships with keypoints, so the
  keyless demo scores by meaning out of the box. Live evidence that prompted this: a factually complete
  Markdown table scored 0.12/Fail under similarity; it now passes under keypoint coverage.

- **Full run cost accounting.** The receipt now reports a run-level cost summary —
  **candidate cost · judge cost · total** — across the cockpit and all three receipt formats. Judge
  calls are tracked **separately** (`ResultRow.judge_cost_usd` + a run-level `RunCostSummary`) and
  are never folded into a candidate's own measured cost or the leaderboard ranking, so per-candidate
  comparisons and the "what to trust" recommendation stay undistorted while every dollar is still
  accounted for. The receipt also shows a **"Scored by"** line (e.g. _Keypoint coverage_ or
  _LLM judge · &lt;model&gt;_). The judge API key never appears in a receipt, log, or response.

- **Decision recipes.** Named comparison presets that turn "pick models" into "pick the decision
  you're making." A recipe row above the Proof setup offers cards like _Cost vs quality for client
  summaries_, _Local vs cloud (privacy)_, _Cheapest model that still passes_, and _Same model,
  different providers_; clicking one **pre-fills** the candidate panel and the decision question
  (you can still edit everything — hand-editing marks the recipe "Custom"). Recipes declare
  **semantic** intent (family / tier / privacy / provider), resolved server-side against the live
  catalog ∩ availability, so each recipe adapts to whatever you have configured. Served read-only at
  `GET /api/recipes` (no secrets — provider labels, model ids, and the env-var _name_ a provider
  needs). It is selection metadata only: recipes never affect a run's `config_hash` or the Proof
  Receipt.

- **Inline provider key entry.** A greyed (unavailable) cloud provider — in the picker or on a
  recipe's "needs a key" banner — now offers an inline key field that writes the key to a local,
  git-ignored `.env.local` (mode `0o600`), unlocking that provider's candidates **without a
  restart**. Keys are never logged, echoed in any HTTP response (including validation errors), or
  written to a receipt; only the four cloud providers are accepted (no arbitrary env writes). New
  `POST /api/credentials` returns only `{provider_id, available}`.

- **Prompt-variant candidates.** A new `Compare by: Models | Prompts` toggle in the Proof Run setup
  compares one model across several **named system prompts** in a single run — answering "which
  wording of my instructions is most trustworthy on my task?" Each prompt becomes a leaderboard row;
  the Proof Receipt records every variant's full prompt text for provenance (receipt schema **v6**).
  Keyless: a prompt-compare run on a mock provider exercises the whole path without any API keys —
  and the mocks are now **prompt-aware**, so the no-key demo produces a real, intuitive winner
  (a brevity instruction like "as few words as possible" deterministically drops trailing facts, so
  on the bundled dataset _Baseline_ scores 100% and _Concise_ ~56% — a genuine decision, not a tie).

- **Model-per-candidate picker.** The Proof Run setup now lets you choose a specific model per
  provider — and compare **several models of the same provider in one run** (the cost/latency-vs-
  quality proof, e.g. Claude Opus vs Haiku). Provider-grouped chips mark the latest (★) and
  recommended models with a cost-class badge, plus a free-text **custom-model** escape hatch;
  unavailable providers (no key) are shown greyed. Each `(provider, model)` is its own candidate
  with a composite `provider:model` id that already feeds `config_hash`; the keyless mocks stay
  bare-id. Served by a new read-only `GET /api/selection` (availability resolved server-side, no
  secrets). Each provider row carries its **official brand logo** in place of the status bullet
  (dimmed when unavailable).

- **Model catalog.** A bundled `provider → model → capabilities` catalog (`orionfold.catalog`)
  describing the six real providers and their curated models — `family`, quality `tier`, privacy,
  context window, cost class, and dated/sourced list prices (local models are free/unpriced). The
  per-provider default models now read from this single source of truth (behavior-preserving;
  `ORIONFOLD_<PROVIDER>_MODEL` still overrides). Exposed read-only at `GET /api/catalog`. This is
  the foundation for an upcoming model picker and comparison "decision recipes"; it is selection
  metadata only — it never affects a run's `config_hash` or the Proof Receipt.

- **Light theme + theme switcher.** A three-state **System / Light / Dark** control in the
  rail footer (replacing the old "Settings · soon" marker). The choice persists
  (`localStorage`), "System" follows the OS and tracks live changes, and a pre-paint script
  applies it before first paint (no flash). The exported **Proof Receipt is themed too**:
  a downloaded receipt follows the reader's OS via `@media (prefers-color-scheme)`, while the
  in-app preview is pinned to the cockpit's theme. Every light token meets WCAG 2.2 AA.

### Changed

- **Proof Receipt schema `RECEIPT_VERSION` 4 → 5** — receipts now carry a `scored_by` descriptor
  (the scoring method, e.g. _Keypoint coverage_ / _LLM judge · &lt;model&gt;_) and a `cost` block
  (candidate / judge / total). Because the scoring contract changed, `config_hash` inputs grew by the
  additive `Example.keypoints` and `Rubric.judge_provider_id` / `judge_model` fields, so hashes for new
  runs differ from prior ones — this is intentional (a run scored a different way is a different run);
  bundled sample receipts were regenerated. Old persisted reports without a `cost_summary` still read
  back (it defaults to a zeroed summary).

- **Catalog refreshed to current (mid-2026) models** with dated, sourced list prices: OpenAI
  GPT-5.x (replacing the retired GPT-4o line), Google Gemini 3.x, Claude (Haiku 4.5 / Sonnet 4.6 /
  Opus 4.8), and Llama 4 Scout. OpenRouter display names dropped the "(via OpenRouter)"
  suffix (the provider row already names it). Run-time cost estimation (`pricing.py`) covers the
  new models and OpenRouter slugs.

- **Proof Run Task name auto-syncs to the selected dataset** until you edit it, so an imported
  dataset's receipt heading no longer inherits the bundled dataset's name.

### Fixed

- **OpenAI candidates and the OpenAI hosted judge no longer error on the output cap.** OpenAI's
  GPT-5.x models reject the legacy `max_tokens` parameter (`HTTP 400: "Unsupported parameter:
  'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead."`), which
  blocked **every** OpenAI run and any LLM-judge run routed to OpenAI. The OpenAI-compatible provider
  now carries a per-profile `token_param`: the OpenAI profile sends `max_completion_tokens`, while
  OpenRouter and LM Studio (which share the class and accept the legacy name) keep `max_tokens`. No
  receipt-schema or wire change for the other providers; the cap value (`ORIONFOLD_MAX_TOKENS`) is
  unchanged.

- **Leaderboard never recommends a candidate that produced nothing.** An errored candidate reports
  `0 ms / $0.00`, so at a 0%-pass tie it used to win the latency/cost tiebreak and get crowned
  **Recommended** (a model returning HTTP 404 on every example was once "recommended"). A fully-
  errored candidate now ranks **last** (ranking adds an `error_count` signal, then `avg_score`
  before latency/cost), and a candidate is marked Recommended **only if it passed at least one
  example**. When nothing passes, the cockpit and all three receipt formats show a calm **"No clear
  winner"** state — "No candidate passed the rubric (threshold N)" — instead of badging a loser, and
  fully-errored rows are annotated "errored, no output". The receipt schema adds the additive
  `error_count` field (**`RECEIPT_VERSION` 3 → 4**); `config_hash` and run provenance are unchanged.

- **Removed `claude-fable-5` from the catalog** — it is not generally available and made the
  cost-vs-quality "Frontier" arm resolve to an unavailable model; the Frontier arm now resolves to
  `claude-opus-4-8` (flagged ★ latest). The anthropic default (`claude-haiku-4-5`) is unchanged.

- **Claude Opus 4.8 catalog price/context corrected** — list price `$15/$75` → `$5/$25` per MTok
  and context `200K` → `1M` (Sonnet 4.6 context also `1M`).

- **Rail footer stays pinned.** The left rail is now viewport-height and sticky on desktop, so
  the theme switcher and engine-status pill no longer scroll away on long run pages.

## [0.1.0] — 2026-06-19

First v0 ship candidate. The complete Proof Receipt loop runs locally — keyless by default,
real local and cloud providers when configured.

### Added

- **Local project + Proof Brief.** Create a project, define a Proof Brief (task, decision
  question, success criteria, privacy boundary), backed by local SQLite (`~/.orionfold/`).
- **Dataset import.** Frozen input/expected text pairs from the bundled demo dataset
  (investment-memo summarization).
- **Providers behind one `ProviderResult` boundary** — uniform output, latency, estimated
  cost, and error on every path:
  - Deterministic, keyless **`mock_good`** / **`mock_bad`** (the default proof path).
  - **Ollama** and **LM Studio** — local, keyless, reachable-server gated.
  - **OpenAI**, **OpenRouter**, **Google Gemini**, **Anthropic** — cloud, offered only when
    their API key resolves. Native `httpx` calls; no provider SDK dependencies.
- **Credential resolution.** Keys read from the system environment first, then a repo-root
  `.env.local` (git-ignored); system env wins, empty values treated as absent. Keys are
  never logged, printed, or written into receipts or screenshots.
- **Matrix run engine** (candidates × examples) capturing output, similarity score, latency,
  and estimated cost; **failure-case browser**; **leaderboard** with quality, latency,
  estimated cost, failure count, privacy mode, and a recommendation.
- **Proof Receipt export** in **Markdown, HTML, and JSON** (schema **v3**), each stamped
  with a config hash, timestamp, and schema version. The model is part of a candidate's
  identity and feeds the `config_hash`.
- **Embedded cockpit.** The Vite/React UI is built and embedded into the wheel and served by
  FastAPI — no Node at runtime. `orionfold up` opens it at `http://localhost:8787`.
- **Env overrides** per provider (`ORIONFOLD_*_MODEL`, `*_BASE_URL`, `OLLAMA_HOST`) plus
  cross-cutting `ORIONFOLD_MAX_TOKENS` (2048) and `ORIONFOLD_TIMEOUT_S` (120).
- **Docs:** README quickstart + provider configuration, `docs/demo-script.md`, release
  charter, ADR-0001 (architecture) and ADR-0002 (provider integration + credentials).

### Security

- Secret redaction is load-bearing in the HTTP layer: error bodies are scrubbed of both
  shaped key patterns (`sk-…`, `sk-proj-…`, `sk-ant-…`, `AIza…`) and the literal in-flight
  key value. Gemini sends its key in the `x-goog-api-key` header (never a `?key=` URL).
  `.env.local` is git-ignored and untracked.

### Known limitations

- **Estimated costs** use a small built-in price table for the default models; unknown
  models (including OpenRouter's namespaced ids, e.g. `openai/gpt-4o-mini`) show `$0.00`.
  Costs are always labeled estimated, never authoritative.
- **`ORIONFOLD_TIMEOUT_S` is a fixed wall-clock timeout.** A progress-based (streaming
  idle) timeout that suits both fast cloud and slow local reasoning models is a planned
  follow-up (candidate ADR-0003).
- The cockpit is functional and accessible but is **not yet the documented three-pane
  design system** (`docs/ux/product-design-system.md`); a polish pass is planned.
- The bundled rubric is tuned for the mock demo (similarity ≥ 0.8), so verbose real-model
  output can score `pass=0` — the integration is proven, not a given model's rubric score.

[0.1.0]: https://example.com/orionfold-proof/releases/0.1.0
