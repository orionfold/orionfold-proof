# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-20 · **Two polish fixes shipped** from the operator's backlog (chosen
priority 1 > 2 > 4 > 3 → did #2 then the receipt task-name follow-up). (1) **#2 sticky rail
footer**: the rail used `lg:h-full` + `mt-auto`, but in the 2-col grid `h-full` resolves to the
tall **row** height, so the footer (Settings + engine status) parked below the fold on long run
pages. Now `lg:sticky lg:top-0 lg:h-screen lg:overflow-y-auto` → footer pinned to the viewport.
(2) **Receipt Task-name sync**: the receipt's HTML subtitle is `brief.task_name`, but it was a
static default that ignored the Dataset dropdown, so an imported set's receipt headline showed the
**bundled** name. ProofCockpit now derives an `effectiveBrief` that mirrors the selected dataset's
name until the user edits Task name (`taskNameTouched` locks it); feeds both form + run body. **No
receipt schema change (still v3).** Both verified in a real browser on a free port (PID asserted):
footer measured `position:sticky` + on-screen at `scrollY==scrollMax`; imported "Client memo
summaries v1" → Task name auto-synced → receipt subtitle reads "Client memo summaries v1". 17
frontend units + clean build + 2/2 e2e green. Commits on `main` (NOT pushed): 030b9db (footer),
11f035e (task-name). The earlier backlog (commits 1001a60..71855ae) is still unpushed too._

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001 +
ADR-0002 + ADR-0003, and the latest worklogs: 2026-06-20-rail-footer-and-task-name and
2026-06-20-ui-feature-review).

RECENT WORK (committed to main, not pushed):
- (this session) Two small UI fixes. #2 STICKY RAIL FOOTER (web/src/app/App.tsx LeftRail aside):
  lg:h-full -> lg:sticky lg:top-0 lg:h-screen lg:overflow-y-auto so Settings + Connected pin to
  the viewport instead of scrolling away on long run pages (grid h-full was resolving to the tall
  row height). RECEIPT TASK-NAME SYNC (web/src/features/proof/ProofCockpit.tsx): added
  taskNameTouched state + effectiveBrief — Task name mirrors the selected dataset's name until the
  user types (then locks); effectiveBrief feeds RunSetup AND the run mutation body. Fixes a
  mismatched receipt HEADLINE (receipts/export.py:229 subtitle = brief.task_name) when an imported
  dataset is selected; the receipt Dataset line was always correct. NO receipt schema change (v3).
  New Vitest in App.test.tsx asserts sync-on-dataset-change + lock-after-edit.
- (prior) DATASET IMPORT (#9), IN-APP RECEIPT PREVIEW (#8), streamed run progress (SSE). v0 is
  feature-complete against the charter.

OPEN BACKLOG (operator priority had 1>2>4>3; #2 + the task-name follow-up are now DONE). Remaining,
from docs/worklog/2026-06-20-ui-feature-review.md §Next steps:
- #1 LIGHT THEME + SWITCHER (next in priority) — sizable: audit ALL --color-* in
  web/src/styles/index.css @theme for a light token set, add a persisted data-theme/class toggle,
  and a switcher in the (now sticky) rail footer where "Settings · soon" sits. START IN PLAN MODE.
- #5 DECISION RECIPES (#5+#7+#4) — the strategic bet: named comparison presets that bundle a
  candidate panel + starter decision question. NEEDS ITS OWN BRAINSTORM before any plan/code.
- Lower: #6 prompt-variant candidates · #10 URL routing / deep links.
Operator's call which thread.

Do NOT regress: keyless mock default; Proof Run is the DEFAULT view; the 3-format receipt; both run
endpoints (batch + stream); dataset routes (preview no-write + create); the NEW Task-name sync
(effectiveBrief mirrors dataset until taskNameTouched); the sticky rail footer. Test-contract
strings (heading "Orionfold Proof", "Connected", button /Run proof/, regions Leaderboard / Failure
cases / Proof Receipt export, "Export Markdown|HTML|JSON", "100% (5/5)", "Failure cases (5)",
"simulated provider failure"). Dataset import: server JSON-only (file read client-side); create
re-parses server-side; name-uniqueness BEFORE id assignment. Tailwind v4: CSS vars use the
PARENTHESIS shorthand bg-(--color-x), never bg-[--color-x]; filled-accent button =
bg-(--color-accent-strong) + text-(--color-accent-ink); inputs use bg-(--color-panel-card). Mocks
don't sleep, so the live progress panel only shows meaningfully for real/slow providers.

NOTES (non-blocking):
- A sibling `orionfold-proof-codex` checkout runs its own servers; leave its processes alone and
  bind a PROVABLY-FREE port (assert the listener PID is yours) — a stale server can shadow a port
  and serve old code. uvicorn does NOT hot-reload backend code: restart `orionfold up` after
  backend changes. The embedded cockpit is served from src/orionfold/server/static (gitignored;
  rebuilt by `bash scripts/build.sh` — REBUILD before any e2e so the new UI is in the artifact).
- The harness sometimes emits STALE TS "cannot find module / no exported member" diagnostics
  mid-edit — false alarms; trust `pnpm --dir web test` + `build` as truth.
- The create-dataset route field is `text` (not `content`): POST /api/datasets {name, format, text}.
- Button copy is "Run proof"/"Rerun proof" (lowercase p) to honor the test contract.
- Settings is still a disabled "soon" marker (deliberate, out of scope) — it's where the theme
  switcher (#1) would land.
Start in plan mode for anything substantial. Verify with uv run pytest, pnpm --dir web test, the
Playwright e2e (rebuild embed first), and a real browser check on a free port. Open review-bound
markdown in Obsidian one at a time. Append a docs/worklog entry and overwrite HANDOFF.md.
```

## Where to look (durable context)

- `docs/worklog/2026-06-20-rail-footer-and-task-name.md` — this session's evidence (latest).
- `docs/worklog/2026-06-20-ui-feature-review.md` — the 10-finding operator review + remaining backlog.
- `docs/worklog/2026-06-20-dataset-import.md` — dataset-import evidence (#9).
- `docs/superpowers/specs/2026-06-20-dataset-import-design.md` · `…/plans/2026-06-20-dataset-import.md`
  — the design + plan pattern for a full-stack finding's build.
- `docs/worklog/2026-06-20-receipt-preview.md` — receipt-preview evidence (#8).
- `docs/adr/0003-streaming-run-progress.md` — SSE progress architecture + idle timeout.
- `docs/ux/product-design-system.md` — the three-pane target, implemented (token source for #1).
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
  `pnpm --dir web test` · `pnpm --dir web e2e` (rebuild embed first). Frontend build: `pnpm --dir web build`.
- Regenerate sample receipts after any schema change: `uv run python scripts/gen_samples.py`.
- Env knobs: `OPENAI_API_KEY` `OPENROUTER_API_KEY` `GEMINI_API_KEY` `ANTHROPIC_API_KEY`;
  `OLLAMA_HOST` `OPENAI_BASE_URL` `OPENROUTER_BASE_URL` `LMSTUDIO_BASE_URL`;
  `ORIONFOLD_{OLLAMA,OPENAI,OPENROUTER,GEMINI,ANTHROPIC,LMSTUDIO}_MODEL`;
  `ORIONFOLD_MAX_TOKENS` (2048) `ORIONFOLD_TIMEOUT_S` (120) `ORIONFOLD_ENV_FILE` `ORIONFOLD_DB`.
```
