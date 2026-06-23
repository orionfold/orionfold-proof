// web/src/features/proof/RecipeRow.tsx
import { Scale, Server, Tag, Shuffle, Sparkles, type LucideIcon } from "lucide-react";

import type { RecipesPanel, ResolvedRecipe } from "../../lib/api";
import { KeyEntry } from "./KeyEntry";

// One icon per decision, keyed by the stable recipe id (not title/order). A recipe added to
// recipes.json later falls back to Sparkles rather than crashing or misaligning.
const RECIPE_ICONS: Record<string, LucideIcon> = {
  "cost-vs-quality": Scale, // weighing economy against frontier
  "local-vs-cloud": Server, // private local box vs hosted cloud
  "cheapest-that-passes": Tag, // lowest price that still clears the bar
  "provider-arbitrage": Shuffle, // same model family across providers
};

// A recipe can have several unmet selectors that all need the SAME provider key (e.g. economy +
// frontier of one family). Show each provider once so the user adds its key a single time.
function dedupeByProvider(unmet: ResolvedRecipe["unmet"]): ResolvedRecipe["unmet"] {
  const seen = new Set<string>();
  return unmet.filter((u) => {
    if (seen.has(u.needs_provider_id)) return false;
    seen.add(u.needs_provider_id);
    return true;
  });
}

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
      <div className="flex flex-wrap items-stretch gap-3">
        {panel.recipes.map((recipe) => {
          const selected = recipe.id === activeRecipeId;
          const Icon = RECIPE_ICONS[recipe.id] ?? Sparkles;
          return (
            <button
              key={recipe.id}
              type="button"
              aria-pressed={selected}
              onClick={() => onSelectRecipe(recipe)}
              className={
                "flex w-56 flex-col gap-0.5 rounded-xl border p-3 text-left transition-colors " +
                (selected
                  ? "border-(--color-accent)/50 bg-(--color-accent)/10"
                  : "border-(--color-panel-line) hover:border-(--color-panel-line-strong)")
              }
            >
              <span className="flex items-center gap-2">
                <Icon
                  aria-hidden="true"
                  className={
                    "size-5 shrink-0 " +
                    (selected ? "text-(--color-accent)" : "text-(--color-ink-muted)")
                  }
                />
                <span className="min-w-0 font-medium text-(--color-ink)">{recipe.title}</span>
              </span>
              <span className="text-xs text-(--color-ink-muted)">{recipe.subtitle}</span>
              <span className="mt-auto flex flex-wrap items-center gap-1.5 pt-1">
                <span className="inline-flex items-center rounded-full border border-(--color-panel-line) px-2 py-0.5 text-[11px] text-(--color-ink-faint)">
                  {recipe.resolved.length} model{recipe.resolved.length === 1 ? "" : "s"}
                </span>
                {recipe.unmet.length > 0 ? (
                  <span className="inline-flex items-center rounded-full border border-(--color-warn)/40 bg-(--color-warn)/10 px-2 py-0.5 text-[11px] text-(--color-warn)">
                    {recipe.unmet.length} need a key
                  </span>
                ) : null}
              </span>
            </button>
          );
        })}
      </div>
      {active && active.unmet.length > 0 ? (
        <div className="grid gap-2 rounded-xl border border-(--color-panel-line) bg-(--color-panel) p-4">
          <p className="text-xs text-(--color-ink-muted)">
            This recipe needs an API key for the greyed providers below. Keys are saved locally to
            .env.local and sent only to that provider.
          </p>
          {dedupeByProvider(active.unmet).map((u) => (
            <div key={u.needs_provider_id} className="flex items-center gap-2">
              <span className="w-28 text-xs text-(--color-ink-faint)">{u.needs_provider_label}</span>
              <KeyEntry
                providerId={u.needs_provider_id}
                providerLabel={u.needs_provider_label}
                keyName={u.key_name}
              />
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
