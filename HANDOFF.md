# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-20 · **Light theme + theme switcher (#1) SHIPPED & merge-ready.** Three-state
**System / Light / Dark** for the cockpit AND the exported Proof Receipt. Built brainstorm → spec →
plan → subagent-driven (7 TDD tasks, per-task reviews + Opus final whole-branch review). Mechanism:
dark stays the `@theme` base; `:root[data-theme="light"]` overrides the 13 `--color-*` tokens
(specificity beats `@theme`), + `@custom-variant dark ([data-theme="dark"] &)` for literal-color
badges. `useTheme` (web/src/lib/theme.ts) persists `localStorage["orionfold-theme"]`, resolves
System via matchMedia w/ live tracking, sets `<html data-theme>`; pre-paint script in index.html =
no FOUC. Switcher (radiogroup) replaced the "Settings · soon" rail marker. Receipt themed
(export.py): dark `:root` default + `@media(prefers-color-scheme:light)` for standalone downloads +
explicit `:root[data-theme=light|dark]` overrides for the in-app iframe (pinned to cockpit theme,
route validates `theme`∈{light,dark}). RECEIPT_VERSION still 3 (presentation-only); config_hash
untouched. Visual/AA gate (real browser, measured): all light tokens clear WCAG AA after ink-faint
#67768a→#5f6e80; dark theme unregressed; receipt iframe served `<html data-theme="light">`. pytest
95 · vitest 26 · build clean · e2e 3/3. Commits on `main` (NOT pushed): a46b5e3 85245d8 411dbdd
1a7193c 989fd3a c0dca53 acba2b3 de66a71 7aa2fa4 92a4beb 0a67af4 (+ spec 4b62d26, plan c8a1a58).
Final review verdict: Ready to merge: YES._

> Also shipped earlier today (commits 030b9db, 11f035e): **#2 sticky rail footer** and the
> **receipt Task-name sync** (Proof Run Task name mirrors the selected dataset until edited).
> CHANGELOG.md now has an `[Unreleased]` section covering all three.

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001 +
ADR-0002 + ADR-0003, and the latest worklogs: 2026-06-20-light-theme,
2026-06-20-rail-footer-and-task-name, and 2026-06-20-ui-feature-review).

RECENT WORK (committed to main, not pushed):
- (this session) LIGHT THEME + SWITCHER (#1). Full-stack, 7 TDD tasks, merge-ready. Three-state
  System/Light/Dark. web/src/lib/theme.ts (useTheme: getStoredChoice/resolveTheme/applyTheme;
  localStorage key orionfold-theme; <html data-theme=light|dark, never "system"). Pre-paint script
  in web/index.html (mirrors the module; no FOUC). index.css: @custom-variant dark
  ([data-theme="dark"] &) + :root[data-theme="light"] overriding the 13 --color-* tokens (dark =
  @theme base). badges.tsx: light base + dark: override for all 5 kinds. App.tsx: ThemeSwitcher
  (radiogroup) replaced the Settings·soon marker. Receipt (export.py to_html(report, theme=None)):
  var(--rc-*) with dark :root default + @media(prefers-color-scheme:light) [standalone→reader OS] +
  :root[data-theme=light|dark] overrides [iframe, pinned to cockpit]; the two light branches must
  hold IDENTICAL values (a parity test enforces count==2). routes.py download_receipt validates
  theme to {light,dark}→None at the boundary (defense-in-depth) + XSS regression test.
  ReceiptDetailView passes useTheme().resolved to receiptPreviewUrl. Light AA: ink-faint is #5f6e80
  (NOT #67768a — that failed AA on the rail). RECEIPT_VERSION still 3.
- (earlier today) #2 sticky rail footer (App.tsx lg:sticky lg:top-0 lg:h-screen) + receipt
  Task-name sync (ProofCockpit effectiveBrief mirrors the selected dataset until taskNameTouched).
- (prior) dataset import (#9), in-app receipt preview (#8), streamed run progress (SSE). v0 is
  feature-complete against the charter.

OPEN BACKLOG (from docs/worklog/2026-06-20-ui-feature-review.md §Next steps). Done so far: #9, #8,
#2, the task-name follow-up, and #1 (light theme). REMAINING:
- #5 DECISION RECIPES (#5+#7+#4) — the strategic bet: named comparison presets that bundle a
  candidate panel + a starter decision question. NEEDS ITS OWN BRAINSTORM before any plan/code.
- #6 prompt-variant candidates (same model, different system prompt) — natural next candidate axis.
- #10 URL routing / deep links — only if shareable view URLs are wanted.
Operator's call which thread; brainstorm #5 first if chosen.

Also pending whenever wanted: PUSH the accumulated main commits (this session + earlier backlog are
all unpushed).

Do NOT regress: keyless mock default; Proof Run is the DEFAULT view; the 3-format receipt; both run
endpoints (batch + stream); dataset routes (preview no-write + create); Task-name sync; sticky rail
footer; the THEME system (data-theme on <html>; orionfold-theme localStorage key; the two receipt
light branches must stay identical — parity test guards it; RECEIPT_VERSION 3; route validates
theme∈{light,dark}). Test-contract strings (heading "Orionfold Proof", "Connected", button
/Run proof/, regions Leaderboard / Failure cases / Proof Receipt export, "Export Markdown|HTML|JSON",
"100% (5/5)", "Failure cases (5)", "simulated provider failure"). Tailwind v4: CSS vars use the
PARENTHESIS shorthand bg-(--color-x), never bg-[--color-x]; filled-accent button =
bg-(--color-accent-strong) + text-(--color-accent-ink); inputs use bg-(--color-panel-card).

NOTES (non-blocking):
- A sibling `orionfold-proof-codex` checkout runs its own servers; leave its processes alone and
  bind a PROVABLY-FREE port (assert the listener PID is yours). uvicorn does NOT hot-reload backend
  code: restart `orionfold up` after backend changes. The embedded cockpit is served from
  src/orionfold/server/static (gitignored; rebuilt by `bash scripts/build.sh` — REBUILD before any
  e2e or browser check so the new UI is in the artifact).
- The harness emits STALE TS "cannot find module / @playwright/test" diagnostics mid-edit — false
  alarms; trust `pnpm --dir web test` + `build` + the actual `pnpm e2e` run as truth.
- create-dataset route field is `text` (not `content`): POST /api/datasets {name, format, text}.
- Button copy is "Run proof"/"Rerun proof" (lowercase p) for the test contract.
- Settings is GONE as a rail marker — that slot is now the theme switcher.
- Tailwind v4 colors render as oklch/oklab in computed styles; for contrast math, compute from the
  source hex (the @theme / :root tokens), not getComputedStyle rgb.
Start in plan mode for anything substantial; brainstorm creative/feature work first. Verify with
uv run pytest, pnpm --dir web test, the Playwright e2e (rebuild embed first), and a real browser
check on a free port. Open review-bound markdown in Obsidian one at a time. Append a docs/worklog
entry and overwrite HANDOFF.md.
```

## Where to look (durable context)

- `docs/worklog/2026-06-20-light-theme.md` — this session's light-theme evidence (latest).
- `docs/superpowers/specs/2026-06-20-light-theme-design.md` · `…/plans/2026-06-20-light-theme.md`
  — design + 7-task plan (the pattern for the next finding's build).
- `docs/worklog/2026-06-20-rail-footer-and-task-name.md` — sticky footer (#2) + task-name sync.
- `docs/worklog/2026-06-20-ui-feature-review.md` — the 10-finding operator review + remaining backlog.
- `docs/worklog/2026-06-20-dataset-import.md` · `…-receipt-preview.md` — #9 / #8 evidence.
- `docs/ux/product-design-system.md` — the three-pane target + the new Theming subsection.
- `docs/adr/0003-streaming-run-progress.md` — SSE progress architecture + idle timeout.
- `docs/release-charter.md` — v0 scope, journey, acceptance criteria (Accepted; all met).
- `docs/adr/0001-…-architecture.md` · `0002-provider-integration-and-credentials.md` — Accepted.
- `CHANGELOG.md` (now has [Unreleased]) · `docs/demo-script.md` — release notes + walkthrough.
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
- Regenerate sample receipts after any receipt change: `uv run python scripts/gen_samples.py`.
- Env knobs: `OPENAI_API_KEY` `OPENROUTER_API_KEY` `GEMINI_API_KEY` `ANTHROPIC_API_KEY`;
  `OLLAMA_HOST` `OPENAI_BASE_URL` `OPENROUTER_BASE_URL` `LMSTUDIO_BASE_URL`;
  `ORIONFOLD_{OLLAMA,OPENAI,OPENROUTER,GEMINI,ANTHROPIC,LMSTUDIO}_MODEL`;
  `ORIONFOLD_MAX_TOKENS` (2048) `ORIONFOLD_TIMEOUT_S` (120) `ORIONFOLD_ENV_FILE` `ORIONFOLD_DB`.
```
