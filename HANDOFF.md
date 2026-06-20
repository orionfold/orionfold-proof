# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-19 · **Gate 7 (ship candidate) complete** — built, verified, security
reviewed, **committed directly to `main`** (`355b779`; not pushed). v0 acceptance criteria
all met. OpenRouter live test closed (7/7). Next: **design-system polish pass** (the one
remaining OWED item) + optional **ADR-0003** (progress-based streaming timeout)._

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001 +
ADR-0002, and the latest worklog, 2026-06-19-gate7-ship-candidate). Gate 7 is DONE and
committed to `main` (`355b779`, not pushed): README provider-config section, CHANGELOG.md,
docs/demo-script.md, samples/screenshots/real-provider-leaderboard.png, and the OpenRouter
7/7 live test closed. Tests green: pytest 65, ruff clean, pyright 0, vitest 3, pnpm build,
Playwright e2e 1; clean install from the rebuilt 0.1.0 wheel verified (RECEIPT_VERSION=3,
secret-free); security review PASS on all six checks. NOTE: this project commits straight to
`main` (solo, single instance) — no per-gate feature branches. A sibling `orionfold-proof-codex`
checkout runs its own servers; leave its processes alone and avoid port 8787 if it's held.

THE ONE OWED ITEM — DESIGN-SYSTEM POLISH PASS (this is the next task):
The cockpit (web/src/features/proof/*) is still functional Gate-5 scaffolding — a single
centered card — NOT the documented three-pane design in docs/ux/product-design-system.md.
Bring it to that design. Use the ux-polish-review and browser-visual-verification skills:
inspect the route in a real browser, screenshot each state (empty/loading/error/populated),
compare to the target, list precise diffs, fix scoped issues, re-verify. The operator asked
to be NOTIFIED when this lands (operator-review-cadence memory). Keep all states accessible
and keyboard-navigable. Do NOT regress the keyless-default behavior or the 3-format receipt.

OPTIONAL ALONGSIDE — ADR-0003 (progress-based timeout):
`ORIONFOLD_TIMEOUT_S` is a fixed wall-clock value; the right primitive is a streaming
idle/read timeout (time-between-tokens) + a generous absolute backstop, with per-class
(local vs cloud) defaults. This needs a streaming change across providers/http.py + the four
providers. Write ADR-0003 first; only implement if the operator wants it this pass.

OTHER NOTES (non-blocking):
- Estimated cost shows $0.00 for any model not in the tiny pricing table (pricing.py),
  including OpenRouter's namespaced ids (openai/gpt-4o-mini vs the table's bare gpt-4o-mini).
  Deliberate "unknown -> $0, estimated not authoritative" design; expand the table if asked.
- .env.local at repo root holds the operator's real keys (ANTHROPIC there; OPENAI/GEMINI/
  OPENROUTER in system env this session). Gitignored (.env.*) + untracked — KEEP IT THAT WAY.
- The committed wheel is a build artifact and dist/ is gitignored; rebuild with
  `bash scripts/build.sh` whenever code changes before a clean-install check.
- Real-provider tests are lenient (a clean 401 passes the no-leak check) — green != proven
  live success; rely on the worklog's manual run evidence.
- LM Studio rides the proven openai_compatible path; needs a one-time GUI launch + model +
  `lms server start` before its candidate works. No code owed.
Start in plan mode. Verify with uv run pytest, pnpm --dir web test, the Playwright happy path,
and a real browser check. Open any review-bound markdown in Obsidian one at a time. Append a
docs/worklog entry and overwrite HANDOFF.md when done.
```

## Where to look (durable context)

- `docs/release-charter.md` — v0 scope, journey, acceptance criteria (Accepted; all met).
- `docs/adr/0001-local-first-proof-receipt-architecture.md` — architecture (Accepted).
- `docs/adr/0002-provider-integration-and-credentials.md` — Gate 6 provider decisions (Accepted).
- `docs/worklog/2026-06-19-gate7-ship-candidate.md` — Gate 7 evidence (latest).
- `docs/worklog/2026-06-19-gate6-provider-integration.md` — provider integration evidence.
- `docs/ux/product-design-system.md` — the target three-pane design for the next pass.
- `CHANGELOG.md` · `docs/demo-script.md` — release notes + operator walkthrough.
- `.claude/rules/{providers,receipts,storage}.md` — enforced constraints.
- `CLAUDE.md` — operating guide and release gates.

## Ship-candidate quick reference

- Build wheel: `bash scripts/build.sh` → `dist/orionfold_proof-0.1.0-py3-none-any.whl`
  (cockpit + dataset embedded, RECEIPT_VERSION=3). dist/ is gitignored.
- Clean-install check: `uv venv /tmp/x && uv pip install --python /tmp/x/bin/python dist/*.whl`
  then `/tmp/x/bin/orionfold up --port <free>` — bind a PROVABLY-FREE port and confirm the
  listener PID is yours (a stale prior-session server can shadow a port and serve old code).
- Dev: `uv run orionfold dev` + `pnpm --dir web dev`. Tests: `uv run pytest` ·
  `pnpm --dir web test` · `pnpm --dir web e2e`.
- Regenerate sample receipts after any schema change: `uv run python scripts/gen_samples.py`.
- Env knobs: `OPENAI_API_KEY` `OPENROUTER_API_KEY` `GEMINI_API_KEY` `ANTHROPIC_API_KEY`;
  `OLLAMA_HOST` `OPENAI_BASE_URL` `OPENROUTER_BASE_URL` `LMSTUDIO_BASE_URL`;
  `ORIONFOLD_{OLLAMA,OPENAI,OPENROUTER,GEMINI,ANTHROPIC,LMSTUDIO}_MODEL`;
  `ORIONFOLD_MAX_TOKENS` (2048) `ORIONFOLD_TIMEOUT_S` (120) `ORIONFOLD_ENV_FILE` `ORIONFOLD_DB`.
