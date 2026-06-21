# Worklog — 2026-06-21 · Folder rename (`orionfold-proof-claude` → `orionfold-proof`)

## Summary

The operator renamed the project directory and its Claude transcript/memory folder from
`orionfold-proof-claude` to `orionfold-proof` (new path
`/Users/manavsehgal/orionfold-proof`). This session finished the post-move cleanup so the
toolchain and docs are consistent with the new path. **No product code changed.**

## What was done

1. **Repointed the venv.** The old `.venv/bin/*` console-script shebangs still pointed at
   the old interpreter path. A plain `uv sync` only reinstalled the editable project package
   (so only `orionfold` got a fresh shebang); the dev-group scripts (`pytest`, etc.) kept
   the stale `orionfold-proof-claude` interpreter line. Fixed with `uv sync --reinstall`,
   which rewrites every package's scripts. Confirmed `head -1 .venv/bin/{orionfold,pytest}`
   both point at `/Users/manavsehgal/orionfold-proof/.venv/bin/python3`. (`.venv` is
   gitignored and reproducible from the lockfile.)
2. **Updated two old-name doc refs** (operator chose consistency over strict append-only):
   `docs/worklog/2026-06-20-ui-feature-review.md` and
   `docs/superpowers/plans/2026-06-20-model-catalog.md`. `git grep orionfold-proof-claude`
   now returns nothing in tracked files.

## Verification

- `uv sync --reinstall` — all `.venv/bin/*` shebangs repointed to the new path.
- `uv run pytest -q` → **200 passed**, 1 warning (pre-existing Starlette/httpx deprecation).
- `pnpm --dir web build` → clean (`tsc --noEmit && vite build`, built in ~1s).
- `git grep orionfold-proof-claude -- ':!HANDOFF.md'` → no matches.

## Product impact

None — environment/path hygiene only. The product, receipts, and config_hash are untouched
(RECEIPT_VERSION stays 5).

## Risks

- The earlier `uv sync` (without `--reinstall`) is a trap to remember: it silently leaves
  stale shebangs on unchanged packages after a directory move. `--reinstall` is the reliable
  fix.

## Next recommended step

Resume the feature roadmap: **#6 Prompt-variant candidates** (same model, different system
prompt, compared in one run). Creative/feature work → brainstorm first, then spec → plan →
subagent-driven. See HANDOFF for the full pointer.
