// web/src/features/proof/RecipeRow.tsx
import type { RecipesPanel, ResolvedRecipe } from "../../lib/api";
import { KeyEntry } from "./KeyEntry";

// "Start from a decision recipe": an optional accelerator above the setup form. Clicking a card
// pre-fills the candidate panel + decision question below (pre-fill, not lock). The active recipe
// stays highlighted; hand-editing the panel/question flips it back to "Custom" (handled upstream).
export function RecipeRow({
  panel,
  activeRecipeId,
  onSelectRecipe,
}: {
  panel: RecipesPanel;
  activeRecipeId: string | null;
  onSelectRecipe: (recipe: ResolvedRecipe) => void;
}) {
  if (panel.recipes.length === 0) return null;
  const active = panel.recipes.find((r) => r.id === activeRecipeId) ?? null;

  return (
    <section aria-label="Decision recipes" className="grid gap-3">
      <div className="flex flex-col gap-0.5">
        <h3 className="text-sm font-medium text-(--color-ink)">Start from a decision recipe</h3>
        <p className="text-xs text-(--color-ink-faint)">
          Pick the decision you're making — we'll pre-fill a coherent panel and the question. You
          can still edit everything.
        </p>
      </div>
      <div className="flex flex-wrap gap-3">
        {panel.recipes.map((recipe) => {
          const selected = recipe.id === activeRecipeId;
          return (
            <button
              key={recipe.id}
              type="button"
              aria-pressed={selected}
              onClick={() => onSelectRecipe(recipe)}
              className={
                "grid w-56 gap-1 rounded-xl border p-4 text-left transition-colors " +
                (selected
                  ? "border-(--color-accent)/50 bg-(--color-accent)/10"
                  : "border-(--color-panel-line) hover:border-(--color-panel-line-strong)")
              }
            >
              <span className="font-medium text-(--color-ink)">{recipe.title}</span>
              <span className="text-xs text-(--color-ink-muted)">{recipe.subtitle}</span>
              <span className="mt-1 text-xs text-(--color-ink-faint)">
                {recipe.resolved.length} model{recipe.resolved.length === 1 ? "" : "s"}
                {recipe.unmet.length > 0 ? ` · ${recipe.unmet.length} need a key` : ""}
              </span>
            </button>
          );
        })}
      </div>
      {active && active.unmet.length > 0 ? (
        <div className="grid gap-2 rounded-xl border border-(--color-panel-line) bg-(--color-panel) p-4">
          <p className="text-xs text-(--color-ink-muted)">
            This recipe needs a key for{" "}
            {active.unmet.map((u) => u.needs_provider_label).join(", ")}.
          </p>
          {active.unmet.map((u) => (
            <KeyEntry
              key={u.needs_provider_id}
              providerId={u.needs_provider_id}
              providerLabel={u.needs_provider_label}
              keyName={u.key_name}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}
