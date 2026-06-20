# ADR 0003: Streamed run progress (and the path to a progress-based timeout)

- **Status:** Accepted (operator-approved 2026-06-20)
- **Date:** 2026-06-20
- **Deciders:** Manav Sehgal (operator) + Claude Code
- **Related:** `docs/adr/0001-local-first-proof-receipt-architecture.md`,
  `docs/adr/0002-provider-integration-and-credentials.md`, `docs/release-charter.md`

## Context

`POST /api/runs` runs the entire candidate×example matrix server-side and returns only the
finished `ProofReport`. For mock runs that is instant, but a real local model can take tens of
seconds per run (observed: an LM Studio run ~39s). During that window the cockpit showed only a
boolean "pending" — no sense of how far along, which candidate is active, or whether anything is
happening. The operator asked for live, truthful progress, and chose the option that "lays the
groundwork for ADR-0003" (the previously-owed progress-based timeout).

## Decision

### 1. Stream progress as Server-Sent Events from a sibling endpoint

Add **`POST /api/runs/stream`** (SSE, `text/event-stream`) alongside the unchanged
`POST /api/runs`. The batch endpoint stays for the CLI, programmatic callers, and existing
tests; the **cockpit uses the streaming endpoint**. Frames (one JSON object per `data:` line,
kind in `type`):

- `start` — `total` cells, `n_examples` per candidate, and the ordered candidate list.
- `progress` — cumulative `done` count plus the just-finished cell's `passed`/`error`.
- `report` — the full, persisted `ProofReport` (identical shape to the batch endpoint).

Validation (unknown dataset / empty or unknown candidates) runs **synchronously before the
stream opens**, so a bad request is a normal 4xx — not an error buried mid-stream.

### 2. The engine gains an iterator; the matrix logic is unchanged

`engine.iter_matrix()` yields one scored `ResultRow` per cell, candidate-major; `run_matrix()`
becomes `list(iter_matrix(...))`. Identical cell logic and ordering — only the shape differs.
The engine stays deterministic and clock-free (run id / timestamp injected by the route).

### 3. The client derives everything from `done`; progress frames stay tiny

Because cells run candidate-major, the **client** computes the currently-running cell
(`candidates[floor(done / n)]`, example `done % n`) and each candidate's completion
(`clamp(done − k·n, 0, n)`) from the cumulative count plus the `start` plan. So `progress`
frames carry only a number and the last outcome — no per-cell plan re-sent. SSE is parsed with
`fetch` + a `ReadableStream` reader (not `EventSource`, which is GET-only); `createRunStream`
resolves with the validated `ProofReport`, so it drops into the existing TanStack mutation.

### 4. No new dependencies, no background jobs

SSE over a FastAPI `StreamingResponse` driving a synchronous generator. No websockets, no job
queue, no progress store — consistent with the charter's "no scheduled jobs / Celery / Redis"
non-goals. The run is still one request; it simply reports as it goes. `X-Accel-Buffering: no`
defeats proxy/dev-server buffering so frames arrive cell-by-cell.

## Consequences

- Long local runs are legible: a determinate bar, the active candidate/example, and
  per-candidate completion. The same stream is the **liveness signal** a future idle timeout
  keys off.
- Two run endpoints to keep in step. Mitigated by the shared engine iterator; the streaming
  route only adds framing + persistence around it.
- Receipt schema, leaderboard, scoring, and storage are untouched (ADR-0001 boundaries hold).

## Follow-up: progress-based idle timeout — **Accepted-implemented (2026-06-20)**

The owed timeout is now in place, exactly on this substrate. Because cells run **sequentially**
(`iter_matrix`, candidate-major), "no cell completes within the idle budget" reduces to "this
cell's HTTP call exceeded its budget" — so the heartbeat window is the per-request **read
timeout**, tuned by provider class. No watchdog, thread, or job queue (charter non-goals hold).

- **Per-class idle budget** (`idle_budget(privacy)` in `providers/http.py`): **local 300s**
  (generous — a cold model load + slow generation on qwen3/deepseek-r1 runs minutes), **cloud
  90s** (tighter — a hosted call idle that long is wedged). `ORIONFOLD_TIMEOUT_S` remains the
  single global override and **extends, not replaces** these — one knob still wins for everyone;
  a garbage/non-positive value falls back to the class default.
- **Absolute backstop**: `httpx.Timeout(budget, connect=min(10s, budget))` — the connection must
  be established within ~10s even when the read budget is generous, so a black-holed host (wrong
  `OLLAMA_HOST`, dropped route) fails fast instead of burning the full local budget.
- **Surfaced as a failing row, never a crash**: `post_json` catches `httpx.TimeoutException`
  *before* the generic `HTTPError` and raises `ProviderError("{provider} timed out after {n}s")`,
  which `safe_generate` turns into a normal failing `ResultRow` (`error="… timed out after …"`).
  The message carries no body, headers, or key — nothing redaction would need to catch.
- **Wiring**: each of the four real providers passes `privacy=self.privacy` to `post_json`; the
  mocks are unaffected (they never call out). Verified by unit tests in
  `tests/unit/test_providers_http.py` (per-class budgets, env override + fallback, the clean
  timed-out message via `safe_generate`, and connect=10s while read=300s).
