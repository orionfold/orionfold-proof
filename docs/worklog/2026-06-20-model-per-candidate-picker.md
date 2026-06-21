# 2026-06-20 — Model-per-candidate picker (decision-recipes sub-project #4)

## Summary

Built the **model-per-candidate picker** — sub-project #4 of the decision-recipes thread, the
next build on the shipped model catalog (#1). The user can now choose a specific model per
provider and **compare several models of the same provider in one run**. The operator framed the
core value precisely: *"I want to bring down my cost, improve latency — will my prompt still work
as well?"* — i.e. add Claude Opus **and** Haiku as candidates and let the leaderboard + receipt
prove the cost/latency-vs-quality trade-off.

Built brainstorm → spec → plan → subagent-driven execution (4 TDD tasks, per-task spec+quality
reviews, an Opus whole-branch review), then three operator follow-ups surfaced during a live
browser walkthrough.

What landed (9 commits on `main`, all local — no remote):

- **`build_candidates()`** (`providers/registry.py`, `6479d66`) — widens run validation from the
  fixed one-per-provider set to composite `provider:model` ids: bare ids still resolve (backward
  compatible), composite ids resolve only for **available, model-bearing** providers with a
  non-empty model (split on the FIRST colon, so `ollama:llama3.1:8b` works), everything else →
  `UnknownCandidateError` (400). Both run endpoints route through it. Keyless-safe.
- **`GET /api/selection`** (`providers/selection.py`, `6275102`) — server-merged picker panel:
  catalog models + live availability + mocks-first. Read-only, no secrets (asserted). Re-exports
  `Tier`/`CostClass`.
- **`CandidatePicker`** (`8a5b96a`) — provider-grouped chips (★ latest, cost-class badge),
  multi-select within a provider, a custom-model escape hatch, greyed unavailable providers.
  Mocks pre-selected by default (keyless path preserved). `RunSetup`/`ProofCockpit` rewired to
  `/api/selection`.
- **e2e** (`69b6e6e`) — `proof.spec.ts` asserts the picker renders.

Operator follow-ups (from the live review):

- **Nested-`<form>` fix** (`0d9bd30`) — the custom-model "Add" was a `<form>` nested inside
  `RunSetup`'s `<form>`; clicking Add submitted the outer form, reloaded the page, and wiped
  selections. Replaced with a `div` + `type="button"` + Enter/Escape key handling. Regression
  test renders the picker **inside** a `<form>` and asserts the outer form is not submitted.
  **Found only because of the real-browser check** — the unit test rendered the picker standalone.
- **Catalog refresh to current models** (`18346af`) — researched current mid-2026 API models with
  dated sources: OpenAI GPT-5.x (GPT-4o retired), Gemini 3.x, Claude (Haiku 4.5/Sonnet 4.6/Opus
  4.8/**Fable 5**), Llama 4 Scout. **Fixed a real catalog bug**: Opus 4.8 list price `15/75`→`5/25`
  and Sonnet/Opus context `200K`→`1M`. Dropped the "(via OpenRouter)" display suffix. Updated
  `gemini.py` `DEFAULT_MODEL` + `test_catalog.py` pinned defaults (drift-guard) and `pricing.py`
  run-time costs for the new models/slugs (legacy `gpt-4o*`/`gemini-2.5` kept for provider tests).
- **Provider logos** (`7991ae2`) — `ProviderLogo` inlines monochrome simple-icons (CC0) brand
  glyphs for the six providers, replacing the availability bullet (full ink when available, dimmed
  when not; mocks keep the dot). Rendered via `currentColor`.
- **Post-review hardening** (`1568dde`) — the final review's one Minor: a crafted `mock_good:foo`
  API request would have minted a composite mock candidate with a non-None model (different
  `config_hash`). Mocks are `model=None` in the registry, so `build_candidates` now requires the
  composite provider be model-bearing — enforcing "mocks stay bare-id" at the boundary, with a test.

Design rule held throughout: **the picker/catalog are SELECTION metadata, never provenance.**
`config_hash` and `RECEIPT_VERSION` (3) are byte-for-byte untouched (the final review verified
`proof/engine.py`/`receipts/export.py`/`domain/models.py` have zero changes).

## Verification

- `uv run pytest -q` → **129 passed** (1 pre-existing StarletteDeprecationWarning).
- `uv run ruff check src tests` → clean. `pnpm --dir web test` → **34 passed**. `pnpm --dir web
  build` → clean.
- Playwright e2e (`pnpm --dir web e2e`, against the rebuilt embed) → **3/3**.
- TDD throughout (RED→GREEN in each task/fix report under `.superpowers/sdd/`).
- Per-task reviews: Task 1 Spec✅/Approved, Task 2 Spec✅/Approved, Task 3 Spec✅/Approved (+ the
  nested-form fix found in the live check), Task 4 sweep clean.
- **Final whole-branch review (Opus, `f76bf09..7991ae2`): Ready to merge YES** — 0 Critical, 0
  Important; all 7 binding constraints confirmed (provenance untouched, mocks bare-id, keyless-safe,
  first-colon split, catalog integrity, Tailwind parenthesis vars, logos sound), the nested-form
  regression test judged genuine. Its one Minor (crafted mock composite id) → taken (`1568dde`).
- **Live browser check** (`localhost:8861`, real-key env): logos render for all six providers;
  models are current (Fable 5 / GPT-5.5 / Gemini 3.1 Pro / Llama 4 Scout marked ★); no "(via
  OpenRouter)" suffix; multi-select within a provider works; **custom-add adds a `phi3:mini` chip
  without resetting selections** (the fixed bug). Screenshots captured during the session.

## Product impact

Turns "pick a provider" into "pick the models you're actually weighing" — the cost/latency-vs-
quality decision a consultant makes daily, now a single repeatable proof. The catalog refresh makes
the picker show *real, current* models with corrected prices, restoring the product's evidence-first
credibility (the prior list showed retired models and a wrong Opus price). Logos make the panel
scannable at a glance. This is the substrate #5 decision recipes will compose on.

## Risks

- **Catalog price/source freshness.** Prices are researched list prices dated `2026-06-20` with
  per-model source URLs, but a few values were flagged UNVERIFIED by the research pass (OpenAI
  cached-input/long-context surcharges; Gemini "preview" frontier tier; OpenRouter `:free` slug).
  An operator price/source verification pass is still worth doing before any release that leans on
  exact numbers. A measured receipt cost always outranks a catalog list price downstream.
- `gemini-3.1-pro-preview` is a **Preview** model id — it may change; swap to `gemini-3.5-flash`
  (stable) if a GA-only frontier is wanted.

## Next recommended step

**#5 decision recipes** — named presets that compose a coherent candidate panel (using #4's
model-bearing candidates) + seed the decision question. Operator decision: unavailable providers
show greyed + offer **inline `.env.local` key entry** — that cross-cut needs its own
security-secrets-review (never log/echo/commit keys). Brainstorm before plan/code; assume #4 has
shipped. (Non-blocking: the operator price/source verification pass; set up a git remote + push —
none configured, all `main` commits are local.)
