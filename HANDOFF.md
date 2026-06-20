# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-19 · Gate 5 (vertical slice) built, verified, reviewed & **merged to `main`** (`3fea82a` feat + doc commits, HEAD `d6344ed`; **not pushed**) · next: **Gate 6 (provider integration)**_

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001,
and the latest docs/worklog entry, 2026-06-19-gate5-vertical-slice). Gate 5 is built,
verified, reviewed, and MERGED to `main` (HEAD `d6344ed`; NOT pushed). The mock-only proof
loop works end-to-end (dataset → run → leaderboard → failure case → receipt md/html/json,
schema v2 with config hash + timestamp + verdict + repro), on SQLite with append-only
migrations. Tests: 30 pytest, 3 vitest, 1 Playwright; ruff + pyright clean. Both review
skills + diff-reviewer/security-reviewer passed. (Merged branch `gate-5-vertical-slice` is
local-only and can be deleted.)

NOTE: the Gate 5 cockpit UI is functional SCAFFOLDING, not the documented design system
(docs/ux/product-design-system.md — three-pane layout + Decision→Verdict results hierarchy
are NOT yet implemented). A dedicated design-system polish pass is owed; notify the operator
when it lands.

Then build GATE 6 — PROVIDER INTEGRATION:
- Add `ollama` (local) and `openai_compatible` (hosted; LM Studio rides this profile) behind
  the SAME ProviderResult boundary (errors returned, not raised; privacy="cloud" for hosted).
- Use httpx (already a dep). Run `current-docs-check` before wiring the HTTP clients.
- Keys read from env/config ONLY; never logged, never written to receipts. Exercise the
  redaction path in providers/base.py (safe_generate → redact_secrets) against REAL provider
  error messages.
- OPERATOR INSTRUCTION (2026-06-19): modify the Gate 6 SPEC and IMPLEMENTATION to resolve
  provider API keys by checking BOTH the system environment AND a repo-root `.env.local`
  file, for each of: OPENAI_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY, ANTHROPIC_API_KEY.
  Notes: (1) precedence — decide and document (suggest system env overrides .env.local, or
  vice-versa; pick one and note it in the ADR/spec). (2) `.env.local` is ALREADY gitignored
  (`.env.*` in .gitignore) — keep it that way; never commit it, never log/echo a key, never
  write a key into any receipt. (3) loading `.env.local`: prefer a tiny stdlib parser (no new
  dep) over python-dotenv unless the operator approves the dep. (4) this implies provider
  profiles beyond the charter's named two — OPENROUTER rides `openai_compatible`; OpenAI rides
  it too; GEMINI and ANTHROPIC are their own profiles. Confirm scope with the operator in plan
  mode before building (the charter v0 named mock + ollama + openai_compatible; this expands
  it). (5) real-provider tests still SKIP gracefully when a given key is absent.
- Mock path stays the keyless default; real-provider tests SKIP gracefully without creds
  (pytest skipif on env vars).
- Register the new providers in providers/registry.py so they appear as candidates with no
  engine/leaderboard/receipt changes. Re-confirm all three receipt formats.
Start in plan mode. Verify with uv run pytest, pnpm --dir web test, the Playwright happy
path, a browser check, and the security-secrets-review skill (focus: real-key handling).
Open any review-bound markdown in Obsidian one at a time. Append a docs/worklog entry and
overwrite HANDOFF.md when done.
```

## Where to look (durable context)

- `docs/release-charter.md` — v0 scope, journey, acceptance criteria (Accepted)
- `docs/adr/0001-local-first-proof-receipt-architecture.md` — architecture (Accepted)
- `docs/worklog/2026-06-19-gate5-vertical-slice.md` — what Gate 5 delivered + risks
- `.claude/rules/{providers,receipts,storage}.md` — enforced constraints for Gate 6
- `CLAUDE.md` — operating guide and release gates

## Slice quick reference (Gate 5 output)

- Dev: `uv run orionfold dev` + `pnpm --dir web dev` (Vite proxies `/api`).
- Embedded run: `bash scripts/build.sh` then `uv run orionfold up` → http://localhost:8787
  (a parallel `orionfold-proof-codex` instance may hold :8787 — use `--port` if so).
- Tests: `uv run pytest` · `pnpm --dir web test` · `pnpm --dir web e2e` (needs
  `pnpm --dir web exec playwright install chromium` once).
- Proof loop entry points: `src/orionfold/proof/engine.py`, `providers/mock.py`,
  `receipts/export.py`, `server/routes.py`, `web/src/features/proof/ProofCockpit.tsx`.
- Sample receipts: `samples/receipts/sample-proof-receipt.{md,html,json}` (schema v2).
- **Packaging guard:** the bundled dataset lives in `src/orionfold/data/datasets/` and must
  appear in the wheel — `unzip -l dist/*.whl | grep data/datasets` after `scripts/build.sh`.
