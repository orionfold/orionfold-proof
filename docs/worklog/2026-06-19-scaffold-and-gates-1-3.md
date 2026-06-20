# 2026-06-19 — Scaffold + Gates 1–3 approved; PyPI names reserved

## Summary
- Scaffolded the Claude Code setup (CLAUDE.md, `.claude/` rules/skills/agents,
  `docs/` context system, repo skeleton dirs). No product code yet.
- Ran the product-release interview. **Gate 1 (product brief)** and **Gate 2 (release
  charter)** approved. **Gate 3 (ADR-0001)** approved.
- v0 decisions locked: persona = AI consultant; proof scope = **text examples only**;
  providers = mock pair + Ollama + OpenAI-compatible; receipts = Markdown + HTML + JSON;
  scoring = deterministic primitives (LLM-as-judge deferred).
- Architecture (ADR-0001): local-first single machine; Python + FastAPI + Typer;
  Vite/React cockpit **embedded in the wheel** (no Node at runtime); SQLite (append-only
  migrations); **no LangChain/LlamaIndex**; error-returning `ProviderResult`.
- Packaging/naming: distribution **`orionfold-proof`**, CLI command **`orionfold`**
  (product surfaces as a subcommand later: `orionfold proof up`; `orionfold up` = flagship
  shortcut). **PyPI names reserved** — published `orionfold`, `orionfold-proof`,
  `orionfold-arena` as `0.0.0` placeholders, owned by personal account `manavsehgal`.
  PyPI org **deferred**.

## Verification
- PyPI: all three packages confirmed live (HTTP 200, version 0.0.0).
- `twine check` passed on all six artifacts before upload.
- No product code written; no tests run yet (nothing to test).

## Product impact
- Product strategy and architecture are settled and documented; brand/package names secured.

## Risks
- Embedded-frontend build ordering (compile `web/dist` → copy into package → `uv build`)
  must be enforced by `build.sh`/CI or the wheel ships without UI.
- Account-wide PyPI token sits in `~/.pypirc` (plaintext). Follow-up: switch to
  project-scoped tokens + revoke; consider Trusted Publishing later.
- Not a git repo yet (`git init` when ready; `.gitignore` is in place).
- `.claude/settings.json.example` not yet activated (rename to `settings.json` to enable
  the permission allowlist).

## Next recommended step
- **Gate 4: build the skeleton ONLY** — Typer CLI (`orionfold up` / `orionfold dev`),
  FastAPI server + health endpoint at `http://localhost:8787`, Vite/React shell, README
  quickstart, baseline pytest + Vitest. **No proof logic.** Start in plan mode; verify with
  `uv run pytest`, `pnpm test`, `pnpm build`, and a browser check of the served shell.
