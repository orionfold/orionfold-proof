# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-20 · **Dataset import** shipped (review finding #9 — the one real v0 charter
acceptance gap; the whole import layer was absent). Users can now import their **own** dataset
(JSONL / CSV / heading-delimited Markdown, by file or paste) through a **preview → confirm → freeze**
flow in the Datasets view. New pure parser (`importers.py`) → name-unique `save_dataset` → two routes
(`POST /api/datasets/preview` no-write + `POST /api/datasets` 201; 422 on zero-valid, 409 on dup
name) → `previewDataset`/`createDataset` Zod client → inline `DatasetImportPanel`. File is read
client-side (`FileReader`) so the server stays JSON-only; create RE-parses server-side as source of
truth. NO schema migration (existing `datasets` table). Built brainstorm → spec → plan →
subagent-driven (6 TDD tasks, per-task + Opus whole-branch review: **ready to merge**). 91 backend +
16 frontend + 2 e2e green. Commits on `main` (NOT pushed): 1001a60 03290fb 1f8864a f83e4fb 26673b6
9184f93 6f4ac9f ca7d69c 71855ae (+ spec 2d67e25, plan 38f6ec8). **Operator-evaluated live in the
browser** against the real embedded build: full loop confirmed end-to-end — pasted JSONL (with a bad
line) → preview "3 examples parsed" + "Line 3 skipped" → froze "Client memo summaries v1" → it's
selectable in Proof Run → ran keyless mocks → leaderboard (Mock·good 3/3 recommended) → failure-case
drill-down on the imported input/expected → in-app receipt artifact (verdict Ship, names the dataset
+ slug + config hash, schema v3). The other backlog findings remain._

> **Quick follow-up surfaced during the live eval (optional, ~1-line):** the receipt's *subtitle*
> uses the Proof Run **Task name** field, which defaults to the bundled dataset's name ("Investment
> memo summarization") even when a different dataset is selected — so a receipt for an imported set
> can show a mismatched heading. Consider defaulting/auto-syncing Task name to the selected dataset's
> name. Cosmetic, not a bug; the receipt's *Dataset* line is always correct.

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001 +
ADR-0002 + ADR-0003, and the latest worklogs: 2026-06-20-dataset-import and
2026-06-20-ui-feature-review).

RECENT WORK (committed to main, not pushed):
- (this session) DATASET IMPORT (review finding #9). Full-stack; the import layer was entirely
  absent before. Parser src/orionfold/data/importers.py: parse_dataset(text, fmt) ->
  ParseResult{examples, warnings, count}; JSONL (input/expected + *_text fallback), CSV
  (case-insensitive headers, names the missing column), Markdown (HEADING-DELIMITED ## Input /
  ## Expected pairs, level-agnostic, split on ---/EOF — chosen because content is prose). Skips
  unreadable rows with a numbered warning; ZERO valid -> DatasetParseError. repository.save_dataset:
  name-unique (case-insensitive, trimmed) -> DuplicateDatasetError; slug id de-dups distinct names
  (-2, -3). Uniqueness check runs BEFORE id assignment (no silent -2). routes.py: POST
  /api/datasets/preview (handler takes no Request -> structurally cannot write) + POST /api/datasets
  (201; RE-parses server-side, never trusts a client example list); 422 empty, 409 dup. Frontend:
  api.ts previewDataset/createDataset (+ parseResultSchema, importFormatSchema); ViewShell gained an
  optional `action` header slot; DatasetImportPanel (format radios; file picker AND paste textarea,
  file read client-side via FileReader so server stays JSON-only; Preview -> pairs + warnings + count
  -> name -> Freeze; on success invalidateQueries(["datasets"]) then onClose). DatasetsView toggles
  the panel above the unchanged list. NO schema migration. Design+plan under docs/superpowers/.
- (prior) IN-APP RECEIPT PREVIEW (#8): ReceiptDetailView renders the generated HTML in a sandbox=""
  iframe (?inline=1 + CSP sandbox + nosniff). PROGRESS-BASED IDLE TIMEOUT + STREAMED RUN PROGRESS
  (SSE POST /api/runs/stream beside batch).

v0 IS FEATURE-COMPLETE against the charter; #9 closed the last UI-side acceptance gap. OPEN BACKLOG
(prioritized in docs/worklog/2026-06-20-ui-feature-review.md §Next steps): #2 sticky rail footer
(cheap P1) · #5+#7+#4 "decision recipes" (the strategic bet — named comparison presets; needs its
own brainstorm) · #1 light theme + switcher · #6 prompt-variant candidates · #10 URL routing.
Operator's call which thread; brainstorm #5 before building. Deferred Minors from #9 live in
.superpowers/sdd/progress.md (CSV/MD whitespace-skip untested; preview route no explicit
status_code=200; postJson DRY; <ol> not visually numbered) — none blocking.

Do NOT regress: keyless mock default; Proof Run is the DEFAULT view; the 3-format receipt; both run
endpoints (batch + stream); the NEW dataset routes (preview no-write + create); test-contract strings
(heading "Orionfold Proof", "Connected", button /Run proof/, regions Leaderboard / Failure cases /
Proof Receipt export, "Export Markdown|HTML|JSON", "100% (5/5)", "Failure cases (5)", "simulated
provider failure"). Dataset import: server is JSON-only (file read client-side); create re-parses
server-side; name-uniqueness check BEFORE id assignment. Tailwind v4: CSS vars use the PARENTHESIS
shorthand bg-(--color-x), never bg-[--color-x]; filled-accent button = bg-(--color-accent-strong) +
text-(--color-accent-ink); inputs use bg-(--color-panel-card). Mocks don't sleep, so the live
progress panel only shows meaningfully for real/slow providers.

NOTES (non-blocking):
- A sibling `orionfold-proof-codex` checkout runs its own servers; leave its processes alone and
  bind a PROVABLY-FREE port (assert the listener PID is yours) — a stale server can shadow a port
  and serve old code. uvicorn does NOT hot-reload backend code: restart `orionfold up` after
  backend changes. The embedded cockpit is served from src/orionfold/server/static (gitignored;
  rebuilt by `bash scripts/build.sh` — REBUILD before any e2e so the new UI is in the artifact).
- The harness sometimes emits STALE TS "cannot find module / no exported member" diagnostics
  mid-edit (seen 3x this session) — false alarms; trust `pnpm --dir web test` + `build` as truth.
- Button copy is "Run proof"/"Rerun proof" (lowercase p) to honor the test contract.
- Settings is still a disabled "soon" marker (deliberate, out of scope).
Start in plan mode for anything substantial. Verify with uv run pytest, pnpm --dir web test, the
Playwright e2e (rebuild embed first), and a real browser check on a free port. Open review-bound
markdown in Obsidian one at a time. Append a docs/worklog entry and overwrite HANDOFF.md.
```

## Where to look (durable context)

- `docs/worklog/2026-06-20-dataset-import.md` — dataset-import evidence (latest).
- `docs/superpowers/specs/2026-06-20-dataset-import-design.md` · `…/plans/2026-06-20-dataset-import.md`
  — design + implementation plan for #9 (the pattern for the next finding's build).
- `docs/worklog/2026-06-20-ui-feature-review.md` — the 10-finding operator review + remaining backlog.
- `.superpowers/sdd/progress.md` — the #9 task ledger + deferred Minors (gitignored scratch).
- `docs/worklog/2026-06-20-receipt-preview.md` — receipt-preview evidence (#8).
- `docs/adr/0003-streaming-run-progress.md` — SSE progress architecture + idle timeout.
- `docs/ux/product-design-system.md` — the three-pane target, implemented.
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
