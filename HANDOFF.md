# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-19 · Gate 4 (skeleton) complete, verified & committed (`cb2476d` on `main`, worktree clean) · next: **Gate 5 (vertical slice)**_

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001,
and the latest docs/worklog entry, 2026-06-19-gate4-skeleton). The Gate 4 skeleton is built
and verified (CLI + FastAPI /api/health + embedded Vite/React shell; pytest + Vitest green;
wheel embeds the cockpit).

Now build the Gate 5 PROOF-RECEIPT VERTICAL SLICE — thin and verified — using the
proof-receipt-vertical-slice skill:

- Domain models (Pydantic) + SQLite storage (stdlib sqlite3, append-only migrations)
- One bundled sample dataset (text input/expected pairs)
- Mock providers mock_good / mock_bad (deterministic, keyless) behind the ProviderResult
  abstraction (errors returned, not raised)
- Minimal rubric + deterministic scoring primitives
- Matrix run engine (candidates × examples) capturing output, score, latency, est. cost
- Leaderboard + at least one failure case view
- Proof Receipt export in Markdown + HTML + JSON, each with config hash + timestamp

Keep it the THINNEST end-to-end path (mock-only first per the charter's scope-risk
mitigation); real providers (Ollama / OpenAI-compatible) are Gate 6. Start in plan mode and
show the plan before building. Verify with `uv run pytest`, `pnpm --dir web test`, a
Playwright happy-path smoke (open → run → leaderboard → failure case → export), and a browser
check. Run the receipt-quality-review + security-secrets-review skills on the receipt output.
Open any review-bound markdown in Obsidian one at a time. When done, append a docs/worklog
entry and overwrite this HANDOFF.md with the next step.
```

## Where to look (durable context)

- `docs/release-charter.md` — v0 scope, journey, acceptance criteria (Accepted)
- `docs/adr/0001-local-first-proof-receipt-architecture.md` — architecture (Accepted)
- `docs/worklog/2026-06-19-gate4-skeleton.md` — what Gate 4 delivered + risks
- `CLAUDE.md` — operating guide and release gates

## Skeleton quick reference (Gate 4 output)

- Run dev: `uv run orionfold dev` + `pnpm --dir web dev` (Vite proxies `/api` → :8787)
- Run embedded: `bash scripts/build.sh` then `uv run orionfold up` → http://localhost:8787
  (NOTE: a parallel `orionfold-proof-codex` instance may hold :8787 — use `--port` if so)
- Tests: `uv run pytest` · `pnpm --dir web test`
- Key files: `src/orionfold/cli.py`, `src/orionfold/server/app.py`, `web/src/app/App.tsx`
