# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-20 · **Left-rail destinations wired** — Datasets / Candidates / Receipts
are now real navigable views (the "soon" markers are gone). Frontend-only; all tests green;
browser-verified. **NOT committed** — awaiting operator review of the screenshots, then commit
to `main` (this project commits straight to main, solo). Next: ADR-0003 (progress-based timeout) —
the main remaining OWED item. (Prior pass — design-system polish — is committed as `d1bd820`.)_

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001 +
ADR-0002, and the latest worklog, 2026-06-20-wire-rail-destinations). The rail-wiring pass is
DONE but UNCOMMITTED — operator review pending. The design-system polish pass before it is
already committed (d1bd820).

WHAT CHANGED THIS PASS (web/src, frontend-only — no backend/endpoint/noun/schema change):
- The left rail is now navigation. App.tsx NAV items are real <button>s with aria-current; the
  "soon" markers are gone. A useState<View> ("proof"|"datasets"|"candidates"|"receipts") switches
  the content area — NO router library (deliberate v0 choice). Proof Run is the DEFAULT view, so
  every existing test/e2e assertion still passes untouched.
- report state was LIFTED from ProofCockpit up to App. ProofCockpit is now CONTROLLED
  (report + onReport props); its run mutation calls onReport and invalidates the ["runs"] query.
  A useEffect on report.run.id clears the failure-case selection when the shown run changes.
- Operator decision: a Receipts row click REOPENS that past run in the Proof Run cockpit
  (App.openInCockpit sets report + view="proof"). Proof Run stays MOUNTED (toggled via the
  `hidden` class = display:none, not unmounted) so an in-flight run / brief / result survive a
  side trip; display:none also keeps it out of the tab order. The `contents` class makes the
  cockpit's own grid the content-column grid item.
- New files: features/proof/{DatasetsView,CandidatesView,ReceiptsView,ViewShell}.tsx,
  features/proof/ReceiptsView.test.tsx, test/fixtures.ts (SAMPLE_REPORT), scripts/
  capture_rail_views.mjs (dev-only Playwright evidence script — run from web/ with PORT=<port>).
  lib/api.ts gained getRuns() (GET /api/runs → ProofReport[], reuses proofReportSchema).
- ReceiptsView HTML: the clickable summary is a <button>; the 3 download <a>s live OUTSIDE it
  (anchors must never nest in a button).

Tests green: pytest 65, ruff clean, pyright 0, vitest 8 (was 3 — +rail nav, +receipt round trip,
+ReceiptsView list/click/empty), pnpm build, Playwright e2e 1. Browser-verified (Claude-in-Chrome
+ Playwright, embedded build, free port, PID asserted ours): Proof Run default, Datasets (+expand),
Candidates, Receipts empty, Receipts populated (cache invalidation), receipt→cockpit round trip,
focus ring. Evidence: samples/screenshots/rail-{datasets,candidates,receipts}.png.

Do NOT regress: keyless mock default, the 3-format receipt, Proof Run as the default view, or the
test-contract strings (heading "Orionfold Proof", "Connected", button /Run proof/, regions
Leaderboard / Failure cases / Proof Receipt export, "Export Markdown|HTML|JSON", "100% (5/5)",
"Failure cases (5)", "simulated provider failure"). Tailwind v4: CSS vars use the PARENTHESIS
shorthand bg-(--color-x), never bg-[--color-x].

THE NEXT TASK (operator's call):
1. If operator approves the screenshots → commit this diff to `main` (not pushed). Files:
   web/src/app/App.tsx, web/src/app/App.test.tsx, web/src/lib/api.ts,
   web/src/features/proof/ProofCockpit.tsx + new {DatasetsView,CandidatesView,ReceiptsView,
   ViewShell}.tsx + ReceiptsView.test.tsx, web/src/test/fixtures.ts,
   scripts/capture_rail_views.mjs, samples/screenshots/rail-*.png, this worklog.
2. ADR-0003 (progress-based streaming idle timeout + backstop, per-class defaults) — write the
   ADR first; implement only if operator wants it (touches providers/http.py + 4 providers).

NOTES (non-blocking):
- A sibling `orionfold-proof-codex` checkout runs its own servers; leave its processes alone and
  bind a PROVABLY-FREE port (assert the listener PID is yours) — a stale server can shadow a port
  and serve old code. The embedded cockpit is served from src/orionfold/server/static (gitignored;
  rebuilt by `bash scripts/build.sh`, which copies web/dist there).
- Button copy is "Run proof"/"Rerun proof" (lowercase p) to honor the test contract;
  copy-deck.md shows "Run Proof". Cosmetic, left as-is.
- Settings is still a disabled "soon" marker (deliberate, out of scope).
Start in plan mode for anything beyond the commit. Verify with uv run pytest, pnpm --dir web test,
the Playwright happy path, and a real browser check on a free port. Open review-bound markdown in
Obsidian one at a time. Append a docs/worklog entry and overwrite HANDOFF.md.
```

## Where to look (durable context)

- `docs/ux/product-design-system.md` — the three-pane target, implemented.
- `docs/worklog/2026-06-20-wire-rail-destinations.md` — this pass's evidence (latest).
- `docs/worklog/2026-06-20-design-system-polish.md` — three-pane polish (committed d1bd820).
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
