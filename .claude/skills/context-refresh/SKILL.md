---
name: context-refresh
description: Use when starting a new session or after a long pause, to rebuild minimal working context without re-reading large docs. Reads the release charter, product brief, and relevant ADRs, then names the next best task.
---

# Context refresh

Goal: rebuild the smallest sufficient working context, fast, without flooding the window.

## Steps

1. Do **not** re-read `CLAUDE.md` or unscoped rules — they load automatically.
2. Read `docs/release-charter.md` (current scope, journey, acceptance criteria, non-goals).
   If it does not exist yet, the project is pre-charter: run `product-release-interview`.
3. Read only the relevant section of `docs/product-brief.md`.
4. Read the latest 1–2 files in `docs/worklog/` to recover open threads and the
   previously recommended next step.
5. Read relevant ADRs **only** if the task changes architecture.
6. Read relevant `docs/ux/` files **only** if the task touches user-facing UI or copy.

## Output

Produce a short status note (do not write a file unless asked):

- **Where we are:** current gate / last completed step.
- **Next best task:** one focused task, with the files likely involved.
- **Open risks:** anything flagged in the last worklog that still matters.

Do not reload `docs/opportunity.md` unless the operator is revisiting strategy.
