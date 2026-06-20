# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-20 · **Streamed run progress + orientation touches** shipped and committed.
Long runs now show a live determinate bar + "now running" cell (SSE); added a Configure→Run→Decide
stepper, first-run CTA nudge, inline field helpers, and a calm result reveal. ADR-0003 written
(streaming architecture + path to the deferred idle timeout). All tests green; browser-verified.
This session's commits on `main` (not pushed): `0015f23` rail views · `a9eda42` icons+rail-foot
polish · `<this>` streamed progress + orientation. Next OWED: ADR-0003's follow-up — the
progress-based idle timeout itself._

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001 +
ADR-0002 + ADR-0003, and the latest worklog, 2026-06-20-streamed-progress-and-orientation).

RECENT WORK (all committed to main this session, not pushed):
- 0015f23 — left-rail destinations wired (Datasets/Candidates/Receipts are real views; a Receipts
  row reopens that run in the cockpit). ProofCockpit is CONTROLLED (report lifted to App).
- a9eda42 — Lucide iconography (functional, calm) + rail-foot polish (EngineStatus 2-line,
  Settings as disabled "soon"). Icons are aria-hidden; ProviderTag/StatusBadge in badges.tsx.
- <this commit> — STREAMED RUN PROGRESS + orientation. Backend: engine.iter_matrix() +
  POST /api/runs/stream (SSE: start/progress/report) beside the unchanged batch POST /api/runs.
  Frontend: lib/api.ts createRunStream (fetch + ReadableStream); ProofCockpit holds {start,done}
  progress state; RunProgress.tsx (determinate bar + "Now running {cand}·example x/n", derived
  client-side from done since cells run candidate-major); StageStepper.tsx (Configure→Run→Decide);
  RunSetup first-run breathe + inline helpers; index.css @theme motion tokens (reveal/emphasis/
  breathe, reduced-motion-safe). ADR-0003 records this + the DEFERRED idle timeout.

THE NEXT OWED TASK: ADR-0003's follow-up — the progress-based idle timeout itself (per-provider-
class idle budget keyed off completed cells as heartbeats + an absolute backstop, surfaced as a
failing ResultRow, never a crash). Touches providers/http.py + the 4 providers; needs its own
tests. Write/extend the ADR section to "Accepted-implemented" when done.

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

- `docs/adr/0003-streaming-run-progress.md` — SSE progress architecture + deferred idle timeout.
- `docs/worklog/2026-06-20-streamed-progress-and-orientation.md` — this pass's evidence (latest).
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
