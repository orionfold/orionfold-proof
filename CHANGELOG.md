# Changelog

All notable changes to **Orionfold Proof** (`orionfold-proof`) are recorded here. The
format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project aims
for [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

- **Catalog refreshed to current (mid-2026) models** with dated, sourced list prices: OpenAI
  GPT-5.x (replacing the retired GPT-4o line), Google Gemini 3.x, Claude (Haiku 4.5 / Sonnet 4.6 /
  Opus 4.8 / Fable 5), and Llama 4 Scout. OpenRouter display names dropped the "(via OpenRouter)"
  suffix (the provider row already names it). Run-time cost estimation (`pricing.py`) covers the
  new models and OpenRouter slugs.

- **Proof Run Task name auto-syncs to the selected dataset** until you edit it, so an imported
  dataset's receipt heading no longer inherits the bundled dataset's name.

### Fixed

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
