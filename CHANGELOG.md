# Changelog

All notable changes to **Orionfold Proof** (`orionfold-proof`) are recorded here. The
format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project aims
for [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

- **Proof Run Task name auto-syncs to the selected dataset** until you edit it, so an imported
  dataset's receipt heading no longer inherits the bundled dataset's name.

### Fixed

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
