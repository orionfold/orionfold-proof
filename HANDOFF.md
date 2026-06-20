# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-20 · **Progress-based idle timeout** shipped (ADR-0003 follow-up — the last
owed item, now CLOSED). A stalled cell fails as a `timed out after Ns` row instead of hanging/
crashing. Per-provider-class idle budgets in `providers/http.py`: local 300s, cloud 90s;
`ORIONFOLD_TIMEOUT_S` still overrides both; connect capped at 10s (absolute backstop). `post_json`
catches `httpx.TimeoutException` before generic `HTTPError`; four providers pass `privacy=self.
privacy`. ADR-0003 flipped to Accepted-implemented; README knob rewritten. 71 tests green, ruff +
pyright clean, fresh diff-review clean. This session's commit on `main` (not pushed): see git log
(idle-timeout). **No owed task remains** — v0 is feature-complete against the charter._

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001 +
ADR-0002 + ADR-0003, and the latest worklog, 2026-06-20-progress-based-idle-timeout).

RECENT WORK (committed to main, not pushed):
- (this session) PROGRESS-BASED IDLE TIMEOUT — the last ADR-0003 owed item, now CLOSED. A stalled
  cell fails as a `timed out after Ns` ResultRow instead of hanging/crashing. providers/http.py:
  `idle_budget(privacy)` replaces the old flat default_timeout — local 300s, cloud 90s;
  `ORIONFOLD_TIMEOUT_S` still overrides both (extends, not replaces); `post_json` builds
  `httpx.Timeout(budget, connect=min(10s,budget))` (10s connect = absolute backstop) and catches
  `httpx.TimeoutException` BEFORE generic `HTTPError` → `ProviderError("{p} timed out after {n}s")`,
  swallowed by safe_generate. The four real providers pass `privacy=self.privacy`. ADR-0003 §follow-up
  flipped to Accepted-implemented; README env-knob rewritten. Tests in test_providers_http.py.
- 05dd651 — STREAMED RUN PROGRESS + orientation. engine.iter_matrix() + POST /api/runs/stream (SSE:
  start/progress/report) beside batch POST /api/runs. Frontend: createRunStream, RunProgress.tsx,
  StageStepper.tsx, first-run breathe + inline helpers, @theme motion tokens.
- a9eda42 — Lucide iconography + rail-foot polish. 0015f23 — left-rail destinations wired.

NO OWED TASK REMAINS. v0 is feature-complete against the release charter (all acceptance criteria
met; ADR-0001/0002/0003 all Accepted-implemented). Likely next candidates, operator's call: the
deferred post-v0 items (document ingestion + minimal RAG template — "first thing after v0"), a
polish/packaging pass before a wider share, or a fresh ship-candidate rebuild. Brainstorm with the
operator before picking; start in plan mode for anything substantial.

Do NOT regress: keyless mock default; Proof Run is the DEFAULT view; the 3-format receipt; both
run endpoints (batch + stream); test-contract strings (heading "Orionfold Proof", "Connected",
button /Run proof/, regions Leaderboard / Failure cases / Proof Receipt export, "Export
Markdown|HTML|JSON", "100% (5/5)", "Failure cases (5)", "simulated provider failure"). Tailwind
v4: CSS vars use the PARENTHESIS shorthand bg-(--color-x), never bg-[--color-x]. Mocks don't
sleep, so the live progress panel only shows meaningfully for real/slow providers (or a CDP
download throttle, as in scripts — see the worklog).

NOTES (non-blocking):
- A sibling `orionfold-proof-codex` checkout runs its own servers; leave its processes alone and
  bind a PROVABLY-FREE port (assert the listener PID is yours) — a stale server can shadow a port
  and serve old code. uvicorn does NOT hot-reload backend code: restart `orionfold up` after
  backend changes (the running app server otherwise serves old routes). The embedded cockpit is
  served from src/orionfold/server/static (gitignored; rebuilt by `bash scripts/build.sh`).
- Button copy is "Run proof"/"Rerun proof" (lowercase p) to honor the test contract.
- Settings is still a disabled "soon" marker (deliberate, out of scope).
Start in plan mode for anything substantial. Verify with uv run pytest, pnpm --dir web test, the
Playwright happy path, and a real browser check on a free port. Open review-bound markdown in
Obsidian one at a time. Append a docs/worklog entry and overwrite HANDOFF.md.
```

## Where to look (durable context)

- `docs/adr/0003-streaming-run-progress.md` — SSE progress architecture + idle timeout (now
  Accepted-implemented, §follow-up).
- `docs/worklog/2026-06-20-progress-based-idle-timeout.md` — this pass's evidence (latest).
- `docs/worklog/2026-06-20-streamed-progress-and-orientation.md` — the streaming substrate.
- `docs/worklog/2026-06-20-wire-rail-destinations.md` — rail views (committed 0015f23).
- `docs/ux/product-design-system.md` — the three-pane target, implemented.
- `docs/worklog/2026-06-19-gate7-ship-candidate.md` — Gate 7 ship-candidate evidence.
- `docs/release-charter.md` — v0 scope, journey, acceptance criteria (Accepted; all met).
- `docs/adr/0001-local-first-proof-receipt-architecture.md` — architecture (Accepted).
- `docs/adr/0002-provider-integration-and-credentials.md` — Gate 6 provider decisions (Accepted).
- `CHANGELOG.md` · `docs/demo-script.md` — release notes + operator walkthrough.
- `.claude/rules/{providers,receipts,storage}.md` — enforced constraints.
- `CLAUDE.md` — operating guide and release gates.

## Ship-candidate quick reference

- Build wheel: `bash scripts/build.sh` → `dist/orionfold_proof-0.1.0-py3-none-any.whl`
  (cockpit + dataset embedded, RECEIPT_VERSION=3). dist/ and src/orionfold/server/static are gitignored.
- Clean-install check: `uv venv /tmp/x && uv pip install --python /tmp/x/bin/python dist/*.whl`
  then `/tmp/x/bin/orionfold up --port <free>` — bind a PROVABLY-FREE port and confirm the
  listener PID is yours (a stale prior-session server can shadow a port and serve old code).
- Dev: `uv run orionfold dev` + `pnpm --dir web dev`. Tests: `uv run pytest` ·
  `pnpm --dir web test` · `pnpm --dir web e2e`. Frontend build: `pnpm --dir web build`.
- Regenerate sample receipts after any schema change: `uv run python scripts/gen_samples.py`.
- Env knobs: `OPENAI_API_KEY` `OPENROUTER_API_KEY` `GEMINI_API_KEY` `ANTHROPIC_API_KEY`;
  `OLLAMA_HOST` `OPENAI_BASE_URL` `OPENROUTER_BASE_URL` `LMSTUDIO_BASE_URL`;
  `ORIONFOLD_{OLLAMA,OPENAI,OPENROUTER,GEMINI,ANTHROPIC,LMSTUDIO}_MODEL`;
  `ORIONFOLD_MAX_TOKENS` (2048) `ORIONFOLD_TIMEOUT_S` (120) `ORIONFOLD_ENV_FILE` `ORIONFOLD_DB`.
```
