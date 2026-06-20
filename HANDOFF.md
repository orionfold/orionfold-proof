# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-19 · Gates 1–3 approved · next: **Gate 4 (skeleton)**_

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001,
and the latest docs/worklog entry). Then build ONLY the Gate 4 skeleton:

- Typer CLI: `orionfold up` and `orionfold dev`
- FastAPI local server with a health endpoint at http://localhost:8787
- Vite + React + TypeScript cockpit shell (served by FastAPI; wire the embedded-build path)
- README quickstart
- baseline tests: pytest (backend) + Vitest (frontend)

NO proof logic, providers, datasets, or receipts yet. Start in plan mode and show the plan
before building. Verify with `uv run pytest`, `pnpm test`, `pnpm build`, and a browser check
of the served shell. Open any review-bound markdown in Obsidian one at a time. When done,
append a docs/worklog entry and overwrite this HANDOFF.md with the next step.
```

## Where to look (durable context)

- `docs/release-charter.md` — v0 scope, journey, acceptance criteria (Accepted)
- `docs/adr/0001-local-first-proof-receipt-architecture.md` — architecture (Accepted)
- `docs/worklog/2026-06-19-scaffold-and-gates-1-3.md` — full state + risks
- `CLAUDE.md` — operating guide and release gates
