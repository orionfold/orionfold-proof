# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-20 · **Design-system polish pass complete** (the one remaining OWED
item) — cockpit brought to the three-pane instrument panel. Frontend-only; all tests green;
browser-verified. **NOT committed** — awaiting operator review of the screenshots, then commit
to `main` (this project commits straight to main, solo). Next: ADR-0003 (progress-based
timeout) or wire the deferred rail destinations — operator's call._

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001 +
ADR-0002, and the latest worklog, 2026-06-20-design-system-polish). The design-system polish
pass is DONE but UNCOMMITTED — operator review pending. The cockpit (web/src) is now the
documented three-pane instrument panel from docs/ux/product-design-system.md: quiet left rail
(Proof Run active; Datasets/Candidates/Receipts are "soon" markers per operator's "structural
shell only" choice; Settings + engine pill at the foot), a main workspace (decision→winner
band → leaderboard → failure cases), and a right inspector (run config, config hash in mono,
Proof Receipt exports, selected failure-case detail). Emerald is the single accent (CTA +
winner only); status=pass/warn/fail and provider=local/cloud/mock have their own colors via
web/src/features/proof/badges.tsx. New files: Inspector.tsx, badges.tsx.

IMPORTANT FIX baked into this diff — Tailwind v4 CSS variables: use the PARENTHESIS shorthand
`bg-(--color-x)`, NEVER `bg-[--color-x]` (v4 emits an unwrapped, invalid `background-color:
--color-x` that silently does nothing — the whole [--color-*] token system had never
rendered). 95 occurrences converted across 7 files. If you add tokens, use `(--color-*)`.

Tests green: pytest 65, ruff clean, pyright 0, vitest 3, pnpm build, Playwright e2e 1.
Browser-verified states (samples/screenshots/design-system-{empty,populated,inspector}.png):
empty, populated, failure-selection→inspector, narrow-reflow (400px), focus ring. Loading +
error engine states are implemented (CenteredNotice text) but not separately screenshotted
(transient). Do NOT regress: keyless mock default, the 3-format receipt, or the test-contract
strings (heading "Orionfold Proof", "Connected", button /Run proof/, regions Leaderboard /
Failure cases / Proof Receipt export, "Export Markdown|HTML|JSON", "100% (5/5)", "Failure
cases (5)", "simulated provider failure").

THE NEXT TASK (operator's call):
1. If operator approves the screenshots → commit the diff to `main` (not pushed). Files:
   web/src/styles/index.css, web/src/app/App.tsx, web/src/features/proof/*.tsx (+ new
   Inspector.tsx, badges.tsx), samples/screenshots/design-system-*.png, this worklog.
2. ADR-0003 (progress-based streaming idle timeout + backstop, per-class defaults) — write
   the ADR first; implement only if operator wants it (touches providers/http.py + 4 providers).
3. OR wire the deferred left-rail destinations (Datasets/Candidates have GET endpoints already).

NOTES (non-blocking):
- A sibling `orionfold-proof-codex` checkout runs its own servers; leave its processes alone
  and bind a PROVABLY-FREE port (assert the listener PID is yours) — a stale server can shadow
  a port and serve old code. The embedded cockpit is served from src/orionfold/server/static
  (gitignored; rebuilt by `bash scripts/build.sh`, which copies web/dist there).
- Button copy is "Run proof"/"Rerun proof" (lowercase p) to honor the test contract;
  copy-deck.md shows "Run Proof". Cosmetic, left as-is.
- `--color-ink-faint` was bumped #6b7c8c→#7c8b9b for WCAG AA (was ~4.49:1).
Start in plan mode for anything beyond the commit. Verify with uv run pytest, pnpm --dir web
test, the Playwright happy path, and a real browser check on a free port. Open review-bound
markdown in Obsidian one at a time. Append a docs/worklog entry and overwrite HANDOFF.md.
```

## Where to look (durable context)

- `docs/ux/product-design-system.md` — the three-pane target now implemented.
- `docs/worklog/2026-06-20-design-system-polish.md` — this pass's evidence (latest).
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
