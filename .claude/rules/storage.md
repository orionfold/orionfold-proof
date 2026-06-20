---
paths:
  - "src/orionfold/storage/**"
---
- Migrations are append-only.
- All persistence is local SQLite by default; no cloud database in v0.
- No user data leaves the machine without an explicit, opt-in action.
