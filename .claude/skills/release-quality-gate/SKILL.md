---
name: release-quality-gate
description: Operator-triggered. Use before tagging or shipping. Runs tests, lint/type/build, Playwright, exports a sample receipt, inspects the worktree, updates README and release notes, and lists known limitations.
disable-model-invocation: true
---

# Release quality gate

Run before any release candidate is treated as shippable. Show evidence for each check.

## Checks

1. `uv run pytest` — all backend tests pass; mock path passes without external keys.
2. `uv run ruff check` and `uv run pyright` — lint and types clean.
3. `pnpm test` and `pnpm build` — frontend units pass and build succeeds.
4. Playwright happy-path e2e passes.
5. Export a sample Proof Receipt from the demo dataset; eyeball Markdown + HTML + JSON.
6. Run the `security-secrets-review` skill (or `security-reviewer` subagent).
7. Fresh-directory install/run sanity check of the documented quickstart.
8. `git status` — worktree clean; no stray artifacts or secrets staged.

## Then

- Update `README.md` quickstart and release notes.
- List known limitations and deferred items explicitly.
- Append a `docs/worklog/` entry.

## Stop condition

Present results and the known-limitations list. **Do not push or tag** until the operator
approves.
