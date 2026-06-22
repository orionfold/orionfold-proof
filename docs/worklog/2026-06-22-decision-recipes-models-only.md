# 2026-06-22 — Decision recipes scoped to Models mode + crisper titles

## Summary
A decision recipe pre-fills the **candidate model panel** (`setSelected(candidate_ids)`) plus the
decision question. But a Prompts-mode run uses `candidate_ids: [resolvedPromptModel]` (the single
model from the prompt picker), so a recipe's model panel is **ignored** when comparing prompts — and
the cards still advertised "N models" there. So recipes are a Models-mode accelerator that was being
shown above the whole form, including in Prompts mode.

- **Moved `RecipeRow` into `RunSetup`'s Models branch**, above `CandidatePicker`, so it renders only
  when Compare by = Models (and sits with the panel it fills). Passed as a `recipes?: ReactNode` slot
  so `RunSetup` stays agnostic of recipe internals; `ProofCockpit` builds the `RecipeRow` and hands
  it in. The shared side effect (decision-question pre-fill) is now Models-only — acceptable, since
  recipes are model-panel-centric and the question stays hand-editable in either mode.
- **Crisper, generalized recipe titles** in `src/orionfold/recipes/recipes.json` (the one
  domain-specific question generalized too):
  - "Cost vs quality for client summaries" → "Cost vs quality"; question dropped "client summaries".
  - "Local vs cloud (privacy)" → "Local vs cloud".
  - "Cheapest model that still passes" → "Cheapest that passes".
  - "Same model, different providers" — kept (already crisp/general).

## Verification
- `recipes.json` valid JSON; no backend or frontend test pins the real titles (the React tests use
  their own mock recipe fixtures).
- `pnpm exec tsc --noEmit` clean; `pnpm test` 90/90 (incl. the `ProofCockpit` recipe test, which
  defaults to Models mode and still finds + clicks the recipe).
- Backend restarted on :8790 (recipes.json loads at startup) → `/api/recipes` serves the new titles.
- Real browser (Vite :5174 → :8790): in Models mode the recipe row sits inside the Models section
  above Candidates with the new titles; switching to Prompts mode hides it entirely.

## Product impact
Recipes now appear only where they do something, next to the model panel they pre-fill — less
misleading (no "N models" accelerator floating above a prompt comparison), and the titles read as
reusable decisions rather than one specific use case.

## Risks / deferrals
- None functional. `:8787` still occupied by an unrelated app; Orionfold runs on :8790 locally.

## Next recommended step
Resume the standing backlog (top item: git remote + push — `main` is still unpushed).
