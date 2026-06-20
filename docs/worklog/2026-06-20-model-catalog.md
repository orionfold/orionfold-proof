# 2026-06-20 — Model catalog (decision-recipes sub-project #1)

## Summary

Built the **model catalog** — the data foundation for the "decision recipes" thread (review
finding #5, chosen by the operator together with #4 model-per-candidate). The operator framed it
as a strategic anchor: a comprehensive `provider → model → capabilities` catalog that future
features hang off, and (future) one whose ranking is refined by measured receipts.

Shipped as sub-project #1 of a sequenced decomposition (#1 catalog → #2 model picker → #3 recipes,
with inline key entry as a cross-cut). Built brainstorm → spec → plan → subagent-driven execution
(3 TDD tasks, per-task spec+quality reviews, an Opus whole-branch review).

What landed:

- **`orionfold.catalog` package** (mirrors the `orionfold.data` datasets pattern):
  - `models.py` — `ModelPricing` / `CatalogModel` / `CatalogProvider` / `ModelCatalog`. Capability
    fields: `family`, `tier` (frontier/balanced/economy), `privacy`, `context_window`, `cost_class`
    (`free`/`$`/`$$`/`$$$`), `pricing` (optional), `latest`, `recommended`. A `CatalogProvider`
    validator enforces `default_model ∈ models` and unique model ids.
  - `catalog.json` — six real providers (anthropic, openai, gemini, openrouter, ollama, lmstudio),
    13 curated models. Cloud prices carry `as_of` + `source`; local models are `cost_class:"free"`,
    `pricing:null`. Mocks are excluded (they carry `model=None`).
  - `load_catalog()` — cached, via `importlib.resources` (wheel-safe, like datasets).
- **`default_model_for(provider_id)`** — the single source of truth for per-provider default
  models. The provider registry now calls it instead of four scattered literal constants;
  override precedence (`ORIONFOLD_<P>_MODEL` env/`.env.local` > catalog default) is unchanged.
  Behavior-preserving — defaults identical, pinned by a regression test + a drift-guard test that
  ties the provider-module `DEFAULT_MODEL` constants to the catalog.
- **`GET /api/catalog`** — read-only endpoint surfacing the catalog for the upcoming model picker
  (#4) and recipes (#5). Carries no credentials (asserted).

Design rule preserved throughout: **the catalog is selection scaffolding, not provenance.** It
never enters `config_hash` or the receipt; `RECEIPT_VERSION` stays 3. Prices are dated, sourced
list prices — a measured receipt cost outranks them downstream (catalog informs *selection*; the
receipt delivers *truth*).

## Verification

- `uv run pytest -q` → **114 passed**, 1 pre-existing StarletteDeprecationWarning (unrelated).
- `uv run ruff check src tests` → clean.
- **Provenance untouched:** `git diff 8700395..e7e1e79 -- proof/engine.py receipts/export.py
  domain/models.py` is **empty**.
- TDD throughout (RED→GREEN evidence in each task report under `.superpowers/sdd/`).
- Per-task reviews: Task 1 Spec✅/Approved, Task 2 Spec✅/Approved, Task 3 Spec✅/Approved.
- Final whole-branch review (Opus, 8700395..2fc9be2): **Ready to merge: YES** — 0 Critical, 0
  Important; verified the behavior-preserving consolidation, no import cycle
  (registry→catalog→domain), pricing-honesty enforced by required fields, and the genuine
  (non-tautological) no-secrets / regression / drift tests.

Commits on `main` (NOT pushed — no remote configured): `459e8ca` `0114b05` `dcd96a0` `9e048c4`
`beb7cb0` `2fc9be2` `e7e1e79` (+ spec `2484839`, plan `8700395`).

## Reviewer findings — disposition

- **Fixed:** validator error-path tests (T1 I1); E402/F811 mid-file imports (T2 + T3, hoisted by
  controller); `as_of` typed as `datetime.date` (rejects malformed dates; JSON contract unchanged
  since `date` serializes to the same ISO string); explicit env-override-wins registry test (closes
  the one spec acceptance line not asserted end-to-end).
- **Rejected (with reasoning):** Gemini 2.5 Pro `tier:"frontier"` + `cost_class:"$$"` is *correct* —
  the spec deliberately decouples quality tier from price class (a frontier model can be a bargain).
  The final review confirmed this adjudication.
- **Deferred:** re-exporting `Tier`/`CostClass` from the package `__init__` → the #2 builder (YAGNI,
  no consumer yet). OpenRouter `source` URLs point at the models list page, not per-model anchors →
  the operator price/source verification pass (already mandated by plan Task-1 Step 5).

## Product impact

Turns "which models exist and what are they like?" into a single, validated, extensible source of
truth — the substrate the model picker (#4) and decision recipes (#5) need before they can compose
coherent comparison panels. No user-visible UI yet (by design); the endpoint is the seam.

## Risks

- **Price staleness** in an evidence-first product. Mitigated by required `as_of` + `source` on
  every price, a catalog-wide `as_of`, and the rule that measured receipt cost outranks list price.
  Exact numbers still need an operator verification pass against the source pages.
- The catalog/registry could drift if a provider were added to one but not the other — guarded by
  `default_model_for` raising `KeyError` on an unknown provider + the drift-guard test.

## Next recommended step

Operator's call on the thread's next slice:

- **#4 model-per-candidate picker** — the natural next build on the catalog: a per-provider
  recommended-models dropdown (from `/api/catalog`, `latest`/`recommended` marked) + a free-text
  custom-model escape hatch; candidates carry a chosen model into the run. Needs its own
  spec/plan.
- **#5 decision recipes** — named presets that compose a panel + seed the decision question;
  graceful degradation when a provider is unavailable. Operator chose "show + offer inline key
  entry" for the unavailable case → that pulls in the inline-`.env.local`-key-entry cross-cut
  (its own security review). Brainstorm before plan/code.
- **Operator price/source verification pass** for `catalog.json` (deferred I2).
- Whenever wanted: set up a git remote + push (none configured; all `main` commits are local).
