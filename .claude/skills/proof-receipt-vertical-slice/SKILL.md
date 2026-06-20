---
name: proof-receipt-vertical-slice
description: Use to build or update the core proof path end-to-end — sample dataset to proof run to leaderboard to receipt export. Keeps the slice thin and verified with tests and a Playwright smoke run.
---

# Proof Receipt vertical slice

The core product loop must always work end-to-end before adding breadth.

## The slice (keep it thin)

1. **Sample dataset** — a small, frozen set of examples under `samples/datasets/`.
2. **Two candidates** — start with `mock_good` and `mock_bad` (deterministic, keyless).
3. **Proof run** — execute the matrix (candidates × examples), capturing output,
   scores, latency, and estimated cost into `RunResult` rows.
4. **Leaderboard** — quality, latency, cost, failure count, privacy mode, recommendation.
5. **Receipt export** — Markdown, HTML, and JSON, each with a config hash and timestamp.
6. **Local persistence** — SQLite, append-only migrations.

## Verify (show evidence, not claims)

- `uv run pytest` — unit + integration, including the keyless mock path.
- Frontend units (`pnpm test`) where UI logic changed.
- One Playwright happy-path run: open app → start sample run → see leaderboard →
  open a failure case → export receipt.
- Browser visual check of the core route (use `browser-visual-verification`).
- Inspect an exported receipt for correctness and confirm **no secrets** appear.

## Guardrails

- Do not expand the data model or provider set inside this slice. Land the loop first.
- Prefer deterministic fixtures so the slice is reproducible without external keys.
- Finish with the `diff-reviewer` subagent or `/code-review`.
