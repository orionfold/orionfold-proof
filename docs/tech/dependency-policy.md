# Dependency Policy

Prefer the Python standard library, small focused libraries, explicit adapters,
copy-owned UI components, and deterministic test fixtures. Avoid heavy orchestration
frameworks, generic agent frameworks, broad UI kits that dictate product feel, and
analytics libraries that phone home.

New **production** dependencies require operator approval. Before adding one, fill out:

```markdown
## Dependency request
Package:
Purpose:
Official docs:
Why standard library / existing dependency is insufficient:
Runtime cost:
Bundle size impact:
Security/privacy risk:
Alternatives considered:
Removal plan if it proves unnecessary:
```

## v0 explicitly avoided (add only when the product proves it needs them)

- Backend: LangChain, LlamaIndex, Celery, Kubernetes, Postgres, Redis, distributed job queues.
- Frontend: Next.js, complex design systems, heavy animation libraries, premature desktop wrappers.

## Approved baseline (from the release charter / ADR-0001)

- Backend: uv, FastAPI, Pydantic, Typer, httpx, pytest, pytest-asyncio, ruff, pyright (SQLite via stdlib `sqlite3`).
- Frontend: Vite, React, TypeScript, Tailwind, shadcn/Radix, TanStack Query, Zod, React Hook Form, Recharts.
- Testing: Playwright, Vitest.
