// web/src/features/proof/RecipeRow.test.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RecipeRow } from "./RecipeRow";
import type { RecipesPanel } from "../../lib/api";

const PANEL: RecipesPanel = {
  recipes: [
    {
      id: "provider-arbitrage",
      title: "Same model, different providers",
      subtitle: "One model family across providers",
      decision_question: "Same model, different hosts?",
      candidate_ids: ["ollama:llama-4-scout"],
      resolved: [
        {
          label: "Llama on Ollama",
          candidate_id: "ollama:llama-4-scout",
          display_name: "Llama 4 Scout",
          provider_id: "ollama",
          cost_class: "free",
        },
      ],
      unmet: [
        {
          label: "Llama on OpenRouter",
          needs_provider_id: "openrouter",
          needs_provider_label: "OpenRouter",
          key_name: "OPENROUTER_API_KEY",
        },
      ],
    },
  ],
};

function wrap(ui: React.ReactNode) {
  return render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);
}

describe("RecipeRow", () => {
  it("renders a card per recipe with a summary", () => {
    wrap(<RecipeRow panel={PANEL} activeRecipeId={null} onSelectRecipe={vi.fn()} />);
    expect(screen.getByText("Same model, different providers")).toBeInTheDocument();
    expect(screen.getByText(/1 need/i)).toBeInTheDocument(); // "1 needs a key"
  });

  it("calls onSelectRecipe with the recipe when clicked", () => {
    const onSelect = vi.fn();
    wrap(<RecipeRow panel={PANEL} activeRecipeId={null} onSelectRecipe={onSelect} />);
    fireEvent.click(screen.getByRole("button", { name: /Same model, different providers/i }));
    expect(onSelect).toHaveBeenCalledWith(PANEL.recipes[0]);
  });

  it("marks the active recipe as pressed and shows its unmet key entry", () => {
    wrap(<RecipeRow panel={PANEL} activeRecipeId="provider-arbitrage" onSelectRecipe={vi.fn()} />);
    expect(
      screen.getByRole("button", { name: /Same model, different providers/i }),
    ).toHaveAttribute("aria-pressed", "true");
    // Unmet banner exposes a KeyEntry "Add key" affordance for the missing provider.
    expect(screen.getByRole("button", { name: /add key/i })).toBeInTheDocument();
    expect(screen.getByText(/OpenRouter/)).toBeInTheDocument();
  });
});
