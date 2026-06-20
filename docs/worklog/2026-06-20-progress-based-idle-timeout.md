# 2026-06-20 — Progress-based idle timeout (ADR-0003 follow-up)

## Summary
Closed the last owed item from ADR-0003: a run that stalls now **fails the stuck cell as a
`timed out after …` row instead of hanging or crashing**, with budgets tuned per provider class.
Because cells run **sequentially** (`iter_matrix`, candidate-major), "no cell completes within
the idle budget" reduces to "this cell's HTTP call exceeded its budget" — so the heartbeat window
is just the per-request **read timeout**, set by class. No watchdog, thread, or job queue (the
charter's non-goals hold); the streaming substrate from the prior pass made this the natural shape.

### What changed
- **`providers/http.py`** — replaced the single flat `default_timeout()` (`ORIONFOLD_TIMEOUT_S`,
  120s) with **`idle_budget(privacy)`**: local **300s** (generous — a cold model load + slow
  generation on qwen3/deepseek-r1 runs minutes), cloud **90s** (tighter — a hosted call idle that
  long is wedged). `ORIONFOLD_TIMEOUT_S` stays the single global override and **extends, not
  replaces** the defaults (one knob wins for everyone); a garbage/non-positive value falls back to
  the class default.
- **Absolute backstop** — `post_json` builds `httpx.Timeout(budget, connect=min(10s, budget))`, so
  the *connection* must land within ~10s even when the read budget is generous. A black-holed host
  (wrong `OLLAMA_HOST`, dropped route) fails fast instead of burning the full 300s.
- **Clean, safe failure** — `post_json` now catches `httpx.TimeoutException` **before** the generic
  `HTTPError` and raises `ProviderError("{provider} timed out after {n}s")`, which `safe_generate`
  turns into a normal failing `ResultRow`. The message carries no body, headers, or key.
- **Wiring** — the four real providers (`ollama`, `openai_compatible`, `gemini`, `anthropic`) each
  pass `privacy=self.privacy` to `post_json`; mocks are untouched (they never call out).
- **Docs** — ADR-0003 follow-up section flipped to **Accepted-implemented**; README env-knob entry
  rewritten (per-class defaults + connect backstop).

New tests in `tests/unit/test_providers_http.py`: per-class budgets; env override applies to both
classes and falls back on garbage/zero; a stubbed `ReadTimeout` surfaces as a `timed out after
300s` row through `safe_generate` (not the generic "request failed"); the `httpx.Timeout` passed
to the wire has `connect == 10` while `read == 300`.

## Verification
- `uv run pytest` → **71 passed** (+4). `uv run ruff check src/ tests/` clean. `uv run pyright src`
  → **0 errors**. (One pre-existing starlette/httpx `TestClient` deprecation warning, unrelated.)
- Frontend untouched (this is a backend failure-path concern); no `pnpm`/browser change needed.
- Fresh-context `diff-reviewer` pass on the uncommitted diff.

## Product impact
A slow or wedged provider can no longer leave the operator staring at a half-finished run with no
resolution. The stuck example resolves into the receipt as an honest failure with a reason, the
leaderboard still computes from the cells that did complete, and the run always ends. Local models
get room to be slow; cloud calls fail sooner when they're truly stuck; an unreachable endpoint
fails in seconds.

## Risks / follow-ups
- Budgets are static per class (not adaptive). If real heavy-reasoning local runs need more than
  300s, `ORIONFOLD_TIMEOUT_S` overrides; revisit defaults only if that proves common.
- A true per-cell **wall-clock** cap (vs. socket-read idle) would require running `generate` off
  the request thread — deliberately out of scope; the read-idle + connect-backstop pair covers the
  observed failure modes (dead daemon, wrong host, hung generation) without that machinery.

## Next recommended step
Operator review. With ADR-0003 fully closed, the v0 build is feature-complete against the charter;
natural next candidates are the deferred post-v0 items (document ingestion + minimal RAG template)
or a polish/packaging pass before a wider share.
