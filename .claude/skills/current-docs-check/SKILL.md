---
name: current-docs-check
description: Use before adding dependencies, using unfamiliar APIs, or changing framework/build config. Consults the local reference index, fetches current guidance only as needed, and logs what changed.
---

# Current docs check

Your training data may be stale. Verify framework specifics before relying on them.

## Steps

1. Look in `docs/tech/reference-index.md` for the relevant library and its canonical URL.
2. If the local reference is missing or stale, fetch current guidance — **scoped, not
   bulk**. Prefer the Context7 MCP for library docs; fall back to web fetch.
3. Add a short note to `docs/tech/docs-update-log.md`: URL, date checked, version, and a
   few repo-relevant notes. Do not paste large docs into the repo.
4. Summarize only the relevant detail back into your plan.

## Before adding a dependency

Complete the dependency request in `docs/tech/dependency-policy.md` (package, purpose,
why stdlib/existing deps are insufficient, runtime/bundle cost, security/privacy risk,
alternatives, removal plan). New production dependencies require operator approval.
