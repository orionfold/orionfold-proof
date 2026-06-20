# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-20 · **In-app Proof Receipt preview** shipped (review finding #8). The
receipt — the product's deliverable — is now viewable in-app, not just downloadable: a dedicated
artifact-first **Receipt detail view** renders the real generated HTML in a `sandbox=""` iframe
(backend `?inline=1` + `CSP: sandbox` + `nosniff`); clicking a receipt opens it, "Explore in
cockpit" is the secondary path. Came from an operator-guided UI/feature review (10 findings) →
brainstorm → spec → plan → subagent-driven execution with per-task + final reviews (verdict: ready
to merge). 73 backend + 12 frontend + 1 e2e green. Commits on `main` (NOT pushed): 780daee 50e4dfb
4214a03 725362c 4e8417b 1d8ea18 7b3a09c. The other 9 review findings are an open backlog._

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001 +
ADR-0002 + ADR-0003, and the latest worklogs: 2026-06-20-receipt-preview and
2026-06-20-ui-feature-review).

RECENT WORK (committed to main, not pushed):
- (this session) IN-APP RECEIPT PREVIEW (review finding #8). routes.py: `?inline=1` on
  GET /api/runs/{id}/receipt.{fmt} serves the same to_html() body with Content-Disposition: inline
  (default attachment), plus `Content-Security-Policy: sandbox` + `X-Content-Type-Options: nosniff`
  on the HTML response. Frontend: ReceiptDetailView renders it in a `sandbox=""` iframe via
  receiptPreviewUrl; App gained `receiptInView` state — clicking a Receipts card opens the detail
  view (mutually exclusive with the archive list; both use <main>), "Explore in cockpit" →
  openInCockpit. NO receipt schema change (RECEIPT_VERSION still 3). Three security layers:
  html.escape + server CSP sandbox + iframe sandbox. Design+plan under docs/superpowers/.
- (prior) PROGRESS-BASED IDLE TIMEOUT (ADR-0003 follow-up). providers/http.py idle_budget(privacy):
  local 300s, cloud 90s; ORIONFOLD_TIMEOUT_S overrides; post_json catches httpx.TimeoutException
  before HTTPError. STREAMED RUN PROGRESS (05dd651): SSE POST /api/runs/stream beside batch.

v0 IS FEATURE-COMPLETE against the charter; this was post-v0 polish from an operator UI/feature
review. OPEN BACKLOG (the other 9 review findings, prioritized in
docs/worklog/2026-06-20-ui-feature-review.md §Next steps): #2 sticky rail footer (cheap P1) · #9
dataset import UI (Tier-1 charter gap) · #5+#7+#4 "decision recipes" (the strategic bet — named
comparison presets; needs its own brainstorm) · #1 light theme + switcher · #6 prompt-variant
candidates · #10 URL routing. Operator's call which thread; brainstorm #5 before building.

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

- `docs/worklog/2026-06-20-receipt-preview.md` — receipt-preview evidence (latest).
- `docs/worklog/2026-06-20-ui-feature-review.md` — the 10-finding operator review + backlog.
- `docs/superpowers/specs/2026-06-20-receipt-preview-design.md` · `…/plans/2026-06-20-receipt-preview.md`
  — design + implementation plan for #8 (the pattern for the next finding's build).
- `docs/adr/0003-streaming-run-progress.md` — SSE progress architecture + idle timeout (now
  Accepted-implemented, §follow-up).
- `docs/worklog/2026-06-20-progress-based-idle-timeout.md` — idle-timeout evidence.
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
