# ADR 0002: Provider integration & credential resolution

- **Status:** Accepted (operator-approved 2026-06-19 — Gate 6)
- **Date:** 2026-06-19
- **Deciders:** Manav Sehgal (operator) + Claude Code
- **Related:** `docs/adr/0001-local-first-proof-receipt-architecture.md`, `docs/release-charter.md`

## Context

Gate 5 shipped the keyless mock-only proof loop. Gate 6 adds **real providers** behind the
same uniform `ProviderResult` boundary (ADR-0001 §6), so the engine, scorer, leaderboard, and
receipt are unchanged. The release charter named mock + Ollama + OpenAI-compatible; an operator
instruction (2026-06-19) expanded credential resolution to four keys (`OPENAI_API_KEY`,
`GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`) and, in plan mode, confirmed
building **four native profiles**. This ADR records the decisions that resolution implies.

## Decision

### 1. Four provider profiles, all over `httpx`

- `ollama` (local) · `openai_compatible` serving **`openai` / `openrouter` / `lmstudio`** ·
  `gemini` (native) · `anthropic` (native). One non-streaming JSON POST per example.
- **`httpx` for every provider — no SDK dependencies.** The provider module is deliberately
  provider-neutral, the call is the simplest possible (one completion in, text + token counts
  out), and `httpx` is already a dependency. Adding the Anthropic and Google SDKs would each be
  a new production dependency for negligible benefit and would split the boundary into
  per-provider shapes. Wire formats and current model IDs were confirmed via the bundled
  `claude-api` skill (Anthropic) and `current-docs-check`/Context7 (others); see
  `docs/tech/docs-update-log.md`.
- Shared plumbing lives in `providers/http.py` (`post_json`, `build_result`, the task
  system prompt); each provider module is a thin parser of its own response shape.

### 2. Credential resolution: system env wins over `.env.local`

- `resolve_key(name)` checks `os.environ` first, then a repo-root **`.env.local`** parsed by a
  tiny stdlib parser (no `python-dotenv`). **Precedence: system environment is authoritative**
  (12-factor / CI); `.env.local` is a local dev convenience.
- `.env.local` is git-ignored (`.env.*`) and must never be committed, logged, or echoed. An
  empty/whitespace value is treated as **absent**, so a misconfigured key never offers a broken
  candidate.
- Non-secret config (base URLs, hosts, model overrides) uses the same precedence via
  `resolve(name, default)`.

### 3. Cloud candidates are gated on key presence; model is part of identity

- The registry is built **dynamically**: mocks + local profiles (`ollama`, `lmstudio`) are
  always offered; cloud profiles appear **only when their key resolves**. Selecting a
  misconfigured candidate still fails gracefully (error returned, never raised).
- Each candidate carries a **fixed default model** (env-overridable, e.g.
  `ORIONFOLD_ANTHROPIC_MODEL`). The model is part of candidate identity and feeds
  `config_hash`, so two runs that differ only by model don't collide. The default Anthropic
  model is a cheap, current model (`claude-haiku-4-5`) because here the model is the *subject
  under test*, chosen by the operator — not the app's own intelligence.

### 4. Redaction is load-bearing; cost is estimated

- A non-2xx or transport failure becomes a terse `ProviderError` (status + short body, never
  headers/keys), which `safe_generate` redacts via `redact_secrets`. The pattern was extended
  for `AIza…` Google keys and hyphenated `sk-proj-…` / `sk-ant-…` families. Gemini sends its
  key in the `x-goog-api-key` **header** (not the `?key=` URL param) so no URL can echo it.
  Verified end-to-end: a real Anthropic 401 returns a clean error with no key material.
- Hosted cost is **estimated** from token counts via a tiny price table
  (`providers/pricing.py`); unknown/local models cost `$0.00`. Never block the local-first path
  on cost precision.

## Consequences

- v0 provider scope is wider than the charter's named two (recorded in the charter). Real
  providers work when configured; their tests **skip gracefully** without credentials or a
  reachable local server. The mock path remains the keyless default.
- New env knobs: `OLLAMA_HOST`, `OPENAI_BASE_URL`, `OPENROUTER_BASE_URL`, `LMSTUDIO_BASE_URL`,
  `ORIONFOLD_<PROFILE>_MODEL`, and `ORIONFOLD_ENV_FILE` (explicit `.env.local` path, used by
  tests). `config_hash` changed once (added `model`); sample receipts regenerated via
  `scripts/gen_samples.py`.

## Alternatives considered

- **Official Anthropic/Google SDKs** — rejected for v0: new dependencies, a non-uniform
  boundary, and unused features (streaming, tool runners) for a single completion call. The
  `claude-api` skill's own guidance defers to provider-neutral code here.
- **`.env.local` wins over system env** — rejected: a stale dotenv silently shadowing CI is a
  worse failure mode than the reverse.
- **Per-Proof-Brief prompt templating** — deferred. v0 sends the example input with one generic
  task instruction; richer prompt control is post-v0.
