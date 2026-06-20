# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-19 · Gate 6 (provider integration) built, verified (incl. live real
runs), reviewed (security + receipt), **committed directly to `main`** (`f6c035d`; not pushed)
· next: **Gate 7 (ship candidate)** · pending: OpenRouter live smoke test once its key resolves_

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001 +
ADR-0002, and the latest docs/worklog entry, 2026-06-19-gate6-provider-integration). Gate 6 is
built, verified, and **committed directly to `main`** (`f6c035d`, not pushed). Tests: 64 pytest
passed / 1 skipped, 3 vitest, 1 Playwright; ruff + pyright clean. Rebuild the wheel before
shipping (the committed wheel predates the max-tokens/timeout knobs — `bash scripts/build.sh`;
RECEIPT_VERSION=3). NOTE: this project commits straight to `main` (solo, single instance) — no
per-gate feature branches.

WHAT GATE 6 DELIVERED (additive — engine/scorer/leaderboard/receipt untouched):
- Four httpx provider profiles behind the same ProviderResult boundary: ollama (local),
  openai_compatible (openai/openrouter/lmstudio), gemini (x-goog-api-key header), anthropic
  (native Messages API, default claude-haiku-4-5). No SDK deps. See ADR-0002.
- config/keys.py: resolve_key checks system env THEN repo-root .env.local (system wins).
  Keys for OPENAI/GEMINI/OPENROUTER/ANTHROPIC. Tiny stdlib parser, bounded upward search.
- Dynamic registry: mocks + ollama + lmstudio always; cloud profiles gated on key presence.
  Candidate.model + LeaderboardEntry.model added; model is in config_hash. Receipt v2→v3.
- Redaction is now load-bearing: _SECRET_PATTERN covers AIza…/sk-proj-…/sk-ant-…, and
  providers/http.py::_scrub_error_body also removes the literal in-flight key value.
- Frontend: ProofCockpit defaults to keyless candidates only (mocks) so "Run proof" doesn't
  fire paid cloud calls on first click. Additive model Zod field.
- VERIFIED LIVE: gemini + anthropic genuinely succeeded end-to-end (real output, real
  estimated cost, no key leak); ollama succeeded; bad-key 401 returns a clean key-free error.
  NOTE: real models show pass=0/5 because the bundled rubric is mock-tuned (similarity ≥ 0.8) —
  expected, the integration is what's proven, not rubric pass rate.

OPEN ITEMS / NOTES:
- PENDING — OPENROUTER LIVE TEST: openrouter is the only profile not yet exercised live (6/7
  done). Its key is in the operator's `.zshrc`, which non-interactive shells don't source, so
  it didn't resolve. Operator is restarting the CLI from an interactive shell (or will add
  OPENROUTER_API_KEY to .env.local). Once `has_key("OPENROUTER_API_KEY")` is true, confirm the
  openrouter candidate appears and run a live no-leak smoke test to close the table at 7/7.
- .env.local at repo root holds the operator's real keys (ANTHROPIC in .env.local; OPENAI +
  GEMINI in system env; OPENROUTER pending — see above). It is gitignored (.env.*) and
  untracked — KEEP IT THAT WAY; never commit, log, echo, or write a key into any receipt.
- LM Studio is installed but needs a one-time GUI launch + a downloaded model + `lms server
  start` (~/.lmstudio/bin/lms) before the lmstudio candidate works. No code owed — same
  proven openai_compatible path.
- Real-provider tests are lenient (a clean 401 passes the no-leak check), so green ≠ proven
  success; rely on the worklog's manual real-run evidence.
- The Gate-5 cockpit is still functional scaffolding, not the documented three-pane design
  system (docs/ux/product-design-system.md). A design-system polish pass is still OWED —
  notify the operator when it lands.

THEN build GATE 7 — SHIP CANDIDATE:
- README/quickstart: how to configure providers via .env.local (document the four keys, the
  env-over-.env.local precedence, and the ORIONFOLD_<PROFILE>_MODEL / *_BASE_URL overrides).
- Release notes, demo script (with a real-provider screenshot + sample receipts), clean-install
  check from the wheel, clean worktree.
Start in plan mode. Verify with uv run pytest, pnpm --dir web test, the Playwright happy path,
a browser check, and the security/receipt review skills. Open any review-bound markdown in
Obsidian one at a time. Append a docs/worklog entry and overwrite HANDOFF.md when done.
```

## Where to look (durable context)

- `docs/release-charter.md` — v0 scope, journey, acceptance criteria (Accepted; provider scope
  expanded by Gate 6 note).
- `docs/adr/0001-local-first-proof-receipt-architecture.md` — architecture (Accepted).
- `docs/adr/0002-provider-integration-and-credentials.md` — Gate 6 decisions (httpx, env
  precedence, redaction, profiles) (Accepted).
- `docs/worklog/2026-06-19-gate6-provider-integration.md` — what Gate 6 delivered + evidence.
- `.claude/rules/{providers,receipts,storage}.md` — enforced constraints.
- `CLAUDE.md` — operating guide and release gates.

## Gate 6 quick reference

- Providers: `src/orionfold/providers/{http,pricing,ollama,openai_compatible,gemini,anthropic,
  registry}.py`; credentials: `src/orionfold/config/keys.py`.
- Env knobs: `OPENAI_API_KEY` `GEMINI_API_KEY` `OPENROUTER_API_KEY` `ANTHROPIC_API_KEY`;
  `OLLAMA_HOST` `OPENAI_BASE_URL` `OPENROUTER_BASE_URL` `LMSTUDIO_BASE_URL`;
  `ORIONFOLD_{OLLAMA,OPENAI,OPENROUTER,GEMINI,ANTHROPIC,LMSTUDIO}_MODEL`;
  `ORIONFOLD_MAX_TOKENS` (default 2048) `ORIONFOLD_TIMEOUT_S` (default 120) `ORIONFOLD_ENV_FILE`.
- OPEN DESIGN ITEM: timeout should be progress-based (streaming idle/read timeout + backstop),
  not a fixed wall-clock value — see worklog "Risks / follow-ups". Candidate for ADR-0003.
- Regenerate sample receipts after any schema change: `uv run python scripts/gen_samples.py`.
- Dev: `uv run orionfold dev` + `pnpm --dir web dev`. Embedded: `bash scripts/build.sh` then
  `uv run orionfold up --port <free>` (avoid 8787 if a sibling instance holds it).
- Tests: `uv run pytest` · `pnpm --dir web test` · `pnpm --dir web e2e`. Real-provider tests
  skip without keys / a reachable local server.
