# ADR 0001: Local-first Proof Receipt architecture

- **Status:** Accepted (operator-approved 2026-06-19 — Gate 3 passed)
- **Date:** 2026-06-19
- **Deciders:** Manav Sehgal (operator) + Claude Code
- **Related:** `docs/release-charter.md`, `docs/product-brief.md`

## Context

We are building the v0 of Orionfold Proof Receipt: a tool that runs private proof tests
across local and cloud AI workflows and exports a repeatable **Proof Receipt**. The
release charter locks v0 scope to a text-examples-only proof loop with mock + Ollama +
OpenAI-compatible providers and Markdown/HTML/JSON receipts, optimized for the **AI
consultant** persona.

Constraints that drive the architecture:

- **Solo founder.** Small surface area, low support burden, boring/maintainable tech.
- **Local-first & privacy.** Private client data must be processable with no hosted
  account and, by default, no network egress. The user must be able to prove what left
  the machine.
- **Single-command install** for a non-developer consultant: `uv tool install
  orionfold-proof` → `orionfold up`.
- **Testability & reproducibility.** Proof runs must be deterministic enough to test
  without external API keys.
- **Distribution is public PyPI**, proprietary license; business model gated in-app, not
  via the registry.

## Decision

### 1. Local-first, single-machine application — no hosted backend in v0

The app runs entirely on the user's machine: a local HTTP server + a local web cockpit +
a local database. No accounts, no cloud storage, no multi-tenant backend. Cloud model
calls are **opt-in** per candidate.

**Why:** The core promise ("prove what your AI can do, privately") is undermined by a
hosted backend. Local-first also removes the entire ops/security/cost burden a solo
founder cannot sustain, and matches how the target communities (LocalLLaMA, local-RAG)
already work.

### 2. Python engine + FastAPI local API + Typer CLI

- **Typer** provides the `orionfold` CLI (`orionfold up`, `orionfold dev`).
- **FastAPI** serves a typed local HTTP API at `http://localhost:8787`.
- **Pydantic** models are the single source of truth for domain objects and API schemas.
- **httpx** for provider calls (sync+async capable, modern).

**Why:** The proof engine is I/O-bound orchestration over model providers — Python's
ecosystem (httpx, Pydantic, FastAPI, pytest) fits exactly. Pydantic-everywhere keeps the
domain model, API contract, and receipt schema consistent and validated. Typer gives a
clean CLI with minimal code.

### 3. Vite + React + TypeScript cockpit, embedded in the Python wheel

The frontend is built with Vite/React/TypeScript/Tailwind (shadcn/Radix, TanStack Query,
Zod, React Hook Form, Recharts). It is **pre-built to static assets at package-build time
and embedded in the wheel**, served by FastAPI. No Node at runtime.

**Why:** A consultant installs one thing from one ecosystem and never touches Node. The
SPA is a thin client over the local API. **Build ordering is a hard requirement:** compile
`web/dist` → copy into the package → `uv build`. CI and the local `build.sh` must enforce
this, or the wheel ships without a UI.

### 4. SQLite (stdlib `sqlite3`) for local persistence

One local SQLite file per install holds projects, briefs, datasets, candidates, runs,
results, and receipts. Migrations are **append-only**.

**Why:** Zero-config, single-file, ships with Python, perfect for single-user local data.
No server to run, back up, or secure. DuckDB may be added later **only** if analytical
queries over results become a real need; not in v0.

### 5. No LangChain / LlamaIndex / agent frameworks in v0

The proof loop (prompt → provider → score → aggregate) is implemented directly.

**Why:** These frameworks add large dependency surfaces, abstraction churn, and hidden
control flow for a loop we can write in a few hundred lines. They would also make
deterministic testing and cost/latency capture harder. The product's identity is the
**receipt**, not a framework. Revisit only if document ingestion/RAG (deferred) proves it
needs them — and even then, prefer small focused libraries.

### 6. Provider abstraction with a uniform, error-safe result

```text
Provider
  id, label
  kind: mock | openai_compatible | ollama | lmstudio | bedrock_later
  generate(input, config) -> ProviderResult

ProviderResult
  output_text
  latency_ms
  input_tokens, output_tokens
  estimated_cost_usd        # always labeled "estimated" for cloud
  raw_metadata              # sanitized; never secrets
  error                     # populated instead of raising across the boundary
```

Implemented in v0: `mock_good`, `mock_bad` (deterministic, keyless), `ollama` (local),
`openai_compatible` (hosted; LM Studio rides this profile). Bedrock is a profile stub
only, pending operator approval.

**Why:** A single uniform result type lets the matrix engine, scoring, leaderboard, and
receipt treat every provider identically. **Errors are returned, not raised**, so one bad
candidate never aborts a run. The local/cloud boundary is a first-class field so the UI
and receipt can label it. (Enforced by `.claude/rules/providers.md`: keys never logged or
written to receipts; cloud opt-in; provider tests skip without credentials.)

### 7. Scoring: deterministic primitives in v0; LLM-as-judge deferred

v0 scoring uses deterministic rubric primitives (exact match, contains, normalized
similarity, simple structural checks). LLM-as-judge is **deferred** post-v0.

**Why:** Keeps the default proof path keyless, reproducible, and cheap — essential for
tests and for the "works in minutes without API keys" first-run promise. LLM-judge adds
nondeterminism, cost, and a circular "use a model to grade a model" problem better tackled
deliberately later.

### 8. Test strategy

- **pytest** (+ pytest-asyncio) for the engine, providers, scoring, receipts, storage.
  Deterministic **mock providers** are the default path so the full suite runs with no
  network and no keys. Real-provider tests **skip gracefully** when credentials are absent.
- **Vitest** for frontend unit logic.
- **Playwright** for the e2e happy path (open → sample run → leaderboard → failure case →
  export) and targeted visual checks.
- Fixtures under `tests/fixtures/`; behavior-named tests
  (e.g. `test_provider_key_never_appears_in_receipt`).

**Why:** Tests are the most compact durable context for an agentic build. A keyless,
deterministic default suite is what makes "give Claude a check it can run" actually true.

### 9. Packaging & naming

Single public PyPI wheel. Distribution name **`orionfold-proof`**, CLI command
**`orionfold`**. Brand names **`orionfold`** and **`orionfold-arena`** reserved (published
`0.0.0` placeholders, 2026-06-19). PyPI org **deferred**; projects owned by the personal
account for now. Proprietary license; product tiers gated **in-app**, not via the registry.

The CLI command is the **brand** (`orionfold`), not the product word (`proof`), because a
command lives on the user's global `$PATH`: `orionfold` is collision-free, brandable, and
trademark-aligned, whereas a generic `proof` binary risks shadowing/being shadowed by
other tools and reinforces nothing. The product name surfaces as a **subcommand** so the
suite nests cleanly as it grows:

```text
orionfold up            # flagship shortcut — Proof is the default product today
orionfold proof up      # explicit, future-proof form
orionfold arena ...     # a future product under the same umbrella command
```

`orionfold up` is retained as the flagship shortcut for `orionfold proof up`. When a second
product ships, all top-level products are subcommands of the single `orionfold` binary
(one package should own the `orionfold` entry point to avoid PATH collisions between
sibling distributions).

## Consequences

**Positive**
- One-command install, one ecosystem for the user; nothing to host or operate.
- Privacy is structural, not a feature toggle: local by default, cloud opt-in, receipts
  scrubbed of secrets.
- Deterministic mock path → fast, reliable, keyless CI and a strong first-run experience.
- Small, legible codebase a solo founder can maintain.

**Negative / trade-offs**
- Embedded-frontend build ordering adds a packaging step that must be enforced (risk: wheel
  without UI). Mitigated by `build.sh` + CI check.
- SQLite single-file means no concurrent multi-process writers — fine for single-user local
  use; would need rework for any future hosted/multi-user mode (explicitly out of scope).
- Hand-rolling the proof loop means we own more code than a framework would, in exchange
  for control, testability, and a small dependency surface.
- Public PyPI means the wheel is readable; proprietary logic protection (if ever needed) is
  a separate, later concern (server-side bits / licensing).

**Follow-ups to revisit (post-v0, not now)**
- Document ingestion + minimal RAG template (first thing after v0).
- LLM-as-judge scoring; DuckDB for analytics; regression diffing between runs.
- Switch to project-scoped PyPI tokens; consider Trusted Publishing (OIDC) in CI.

## Alternatives considered

- **Hosted SaaS backend** — rejected: contradicts the privacy promise and imposes ops,
  security, and cost burden incompatible with a solo founder. (Future paid features can be
  thin hosted add-ons without moving the core off the machine.)
- **Electron / native desktop shell** — rejected for v0: heavier build/release pipeline and
  app-store friction; a local web cockpit delivers the same UX with far less overhead.
- **Next.js (SSR) frontend** — rejected: no SSR need for a local single-user SPA; adds a
  Node runtime dependency that breaks the one-ecosystem install.
- **Postgres / a client-server DB** — rejected: operational overhead with no benefit for
  single-user local data; SQLite is the right size.
- **LangChain / LlamaIndex** — rejected (see Decision 5).
- **Community (free) PyPI org** — not applicable: legitimate only for community/OSS
  projects, not a commercial product; Company org deferred on cost/approval grounds.
