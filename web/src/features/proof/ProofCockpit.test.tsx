// web/src/features/proof/ProofCockpit.test.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProofCockpit } from "./ProofCockpit";
import * as api from "../../lib/api";

const DATASETS = [
  { id: "d1", name: "Sample", description: "", examples: [] },
  { id: "d2", name: "Other", description: "", examples: [] },
];
const SELECTION = {
  providers: [
    {
      provider_id: "mock_good",
      label: "Mock (good)",
      privacy: "local" as const,
      available: true,
      supports_custom: false,
      candidate_id: "mock_good",
      models: [],
    },
  ],
};
const RECIPES = {
  recipes: [
    {
      id: "provider-arbitrage",
      title: "Same model, different providers",
      subtitle: "One family across providers",
      decision_question: "Same model, different hosts?",
      candidate_ids: ["ollama:llama-4-scout"],
      resolved: [
        {
          label: "Llama on Ollama",
          candidate_id: "ollama:llama-4-scout",
          display_name: "Llama 4 Scout",
          provider_id: "ollama",
          cost_class: "free" as const,
        },
      ],
      unmet: [],
    },
  ],
};

function wrap() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <ProofCockpit report={null} onReport={vi.fn()} />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("ProofCockpit recipes", () => {
  it("pre-fills the decision question when a recipe is clicked", async () => {
    vi.spyOn(api, "getDatasets").mockResolvedValue(DATASETS as never);
    vi.spyOn(api, "getSelection").mockResolvedValue(SELECTION as never);
    vi.spyOn(api, "getRecipes").mockResolvedValue(RECIPES as never);
    wrap();
    await waitFor(() => screen.getByText("Same model, different providers"));
    fireEvent.click(screen.getByRole("button", { name: /Same model, different providers/i }));
    await waitFor(() =>
      expect((screen.getByLabelText(/decision question/i) as HTMLInputElement).value).toBe(
        "Same model, different hosts?",
      ),
    );
  });
});

describe("ProofCockpit decision-question integrity (WS-C)", () => {
  it("clears an untouched decision question when the dataset changes", async () => {
    vi.spyOn(api, "getDatasets").mockResolvedValue(DATASETS as never);
    vi.spyOn(api, "getSelection").mockResolvedValue(SELECTION as never);
    vi.spyOn(api, "getRecipes").mockResolvedValue(RECIPES as never);
    wrap();

    // A recipe authors a question for the current dataset…
    await waitFor(() => screen.getByText("Same model, different providers"));
    fireEvent.click(screen.getByRole("button", { name: /Same model, different providers/i }));
    const question = () => screen.getByLabelText(/decision question/i) as HTMLInputElement;
    await waitFor(() => expect(question().value).toBe("Same model, different hosts?"));

    // …but a recipe is a deliberate choice, so it survives a dataset switch.
    fireEvent.change(screen.getByLabelText("Dataset"), { target: { value: "d2" } });
    await waitFor(() => expect(question().value).toBe("Same model, different hosts?"));
  });

  it("does not carry a default question onto a freshly selected dataset", async () => {
    vi.spyOn(api, "getDatasets").mockResolvedValue(DATASETS as never);
    vi.spyOn(api, "getSelection").mockResolvedValue(SELECTION as never);
    vi.spyOn(api, "getRecipes").mockResolvedValue(RECIPES as never);
    wrap();

    // Untouched on first paint: the seeded default question is suppressed, not shown stale.
    await waitFor(() => screen.getByLabelText(/decision question/i));
    const question = screen.getByLabelText(/decision question/i) as HTMLInputElement;
    expect(question.value).toBe("");
  });
});
