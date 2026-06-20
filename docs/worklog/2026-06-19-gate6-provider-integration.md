# 2026-06-19 — Gate 6: provider integration

## Summary
Added real providers behind the Gate-5 `ProviderResult` boundary — **the engine, scorer,
leaderboard, and receipt were untouched**; the work was additive (one registry, four thin
provider modules, a credential resolver). Operator-confirmed scope (plan mode): build **four
native profiles**, resolve keys with **system env winning over `.env.local`**, and pin a
**fixed default model per profile** that feeds `config_hash`.

- **Providers (`providers/`, all `httpx` — no SDK deps):**
  - `ollama` (local) — `POST /api/chat`, `stream:false`; `OLLAMA_HOST` override.
  - `openai_compatible` — one class, three instances: `openai`, `openrouter`, `lmstudio`
    (keyless/local). `Authorization: Bearer`.
  - `gemini` — `generateContent`; key in the **`x-goog-api-key` header** (never the `?key=`
    URL), so no URL can echo it.
  - `anthropic` — native Messages API (`x-api-key` + `anthropic-version`), wire shape per the
    bundled `claude-api` skill; default `claude-haiku-4-5` (the model is the *subject under
    test*, env-overridable).
  - Shared `http.py` (`post_json`, `build_result`, task system prompt) and `pricing.py`
    (estimated cost; local/unknown → `$0`).
- **Credentials (`config/keys.py`):** `resolve_key` checks `os.environ` first, then a
  repo-root `.env.local` parsed by a tiny stdlib parser (no `python-dotenv`). Empty values
  treated as absent. Upward search **bounded** to the project root / home (security hardening).
- **Registry (`providers/registry.py`):** dynamic — mocks + `ollama` + `lmstudio` always;
  cloud profiles offered **only when their key resolves**. Each candidate carries its default
  model.
- **Identity:** `Candidate.model` + `LeaderboardEntry.model` added; `config_hash` now includes
  the model. Receipt schema **bumped v2 → v3**; samples regenerated via the new
  `scripts/gen_samples.py`.
- **Redaction (load-bearing now):** `_SECRET_PATTERN` extended for Google `AIza…` and
  hyphenated `sk-proj-…`/`sk-ant-…`. After the security review, redaction was moved into the
  HTTP layer (`_scrub_error_body`) and now **scrubs the literal in-flight key value** from
  error bodies — covering even an unlabeled custom-gateway token the regex can't shape-match.
- **Frontend:** additive `model` Zod field; **`ProofCockpit` default selection changed to the
  keyless candidates only** (the mocks) so "Run proof" no longer fires slow/paid cloud calls on
  first click — a real UX fix surfaced by the e2e.
- **Docs:** `ADR-0002` (decisions + alternatives), charter scope note, `reference-index.md` +
  `docs-update-log.md` entries for the four provider APIs.

## Verification (evidence)
- `uv run pytest` → **61 passed, 2 skipped** (openrouter no key, lmstudio server down). New:
  `test_keys`, `test_providers_http` (parse + redaction incl. literal-key scrub),
  `test_registry`, `test_real_providers`. `ruff` clean; `pyright src` → 0 errors.
- **Live real-provider tests pass** against the operator's keys: `openai`, `gemini`,
  `anthropic` succeed; `ollama` succeeds; bad-key Anthropic 401 returns a clean, key-free error.
- **Real end-to-end runs** (`orionfold up`, real API):
  - Gemini: 5 real completions, est_cost `$0.000783` from real token counts, model in receipt,
    **no key material**.
  - Anthropic (after key refresh): `error=None`, real summary, tokens 58/22, est_cost
    `$0.000168` (= haiku $1/$5 per 1M ✓), no leak.
  - `pass=0/5` for real models is expected — the mock-tuned 0.8-similarity rubric doesn't
    reward verbose real output; the *integration* is what's proven.
- `pnpm --dir web test` → 3 passed; `pnpm --dir web build` clean; **Playwright happy path
  passes** (967ms — confirms the fast mock-only default).
- `scripts/build.sh` → wheel embeds the dataset **and** cockpit; wheel `RECEIPT_VERSION = 3`.
- **Security:** `security-secrets-review` + `security-reviewer` subagent — no critical leak;
  Gemini header-only key confirmed; keys never in `raw_metadata`/payload/receipt; `.env.local`
  git-ignored and **untracked**. Two hardening findings applied (HTTP-layer + literal-value
  redaction; bounded `.env.local` walk). `receipt-quality-review` — samples v3, secret-free,
  all three formats, recommendation/verdict clear.

## Product impact
A user can now prove **real** local and cloud models — Ollama, OpenAI, OpenRouter, Gemini,
Anthropic, LM Studio — on their own task and get the same private, repeatable, secret-free
receipt, naming which candidate to trust. Cloud candidates appear only when configured; the
keyless mock path stays the instant default.

## Late additions (operator testing of local reasoning models)
- **`ORIONFOLD_MAX_TOKENS`** (default 2048) and **`ORIONFOLD_TIMEOUT_S`** (default 120) env
  overrides, applied uniformly across all four providers (`http.py::max_output_tokens` /
  `default_timeout`). Surfaced because reasoning models (qwen3, deepseek-r1, gpt-oss) spend the
  output budget *thinking* and return empty content at a low cap, and need longer than 60s.
- **Proven live:** LM Studio `qwen/qwen3.5-9b` returned a correct one-line summary
  (`ORIONFOLD_MAX_TOKENS=8192`, `ORIONFOLD_TIMEOUT_S=300`) — 64/2474 tokens, 52.3s, local, $0.
- Real-provider tests cap themselves at 256 tokens so `uv run pytest` stays ~12s.

## Risks / follow-ups
- **Timeout is not yet hardware/model-adaptive (DESIGN FOLLOW-UP).** A fixed (even
  env-overridable) wall-clock timeout is the wrong primitive: the same value can't suit a fast
  cloud model and a slow local 30B reasoning model in one matrix. The generalized fix is to key
  off **progress, not duration** — stream the response and apply an **idle/read timeout**
  (time-between-tokens) plus a generous absolute backstop, with per-class (local vs cloud)
  defaults. Worth an ADR-0003 + a focused streaming change; the env knob is the interim.
- **Real-provider tests are lenient by design** — a clean 401 passes the no-leak assertion, so
  a green run doesn't *alone* prove a live success. Mitigated this session by manual real runs
  (Gemini + Anthropic genuinely succeeded). Consider a separate opt-in "must succeed" test
  later.
- **Model `output_text` is not scrubbed** (security finding #2, deliberately deferred): it's
  the user's own content and the core receipt artifact; scrubbing would corrupt it. Documented
  boundary, not a v0 fix.
- **LM Studio installed but not yet runnable headlessly** — needs a one-time GUI launch + model
  download + `lms server start`; then `lmstudio` lights up via the already-proven
  `openai_compatible` path. No code owed.
- **Default models** (`gpt-4o-mini`, `gemini-2.5-flash`, `claude-haiku-4-5`,
  `openai/gpt-4o-mini`, `llama3.2`) are env-overridable; the Gate-5 cockpit is still functional
  scaffolding, not the documented three-pane design system (polish pass still owed).

## Next recommended step
**Gate 7 — ship candidate:** README/quickstart for configuring providers via `.env.local`
(document the four keys + env precedence + model overrides), release notes, demo script with a
real-provider screenshot, sample receipts, clean-install check, clean worktree. Then the owed
**design-system polish pass** on the cockpit.
