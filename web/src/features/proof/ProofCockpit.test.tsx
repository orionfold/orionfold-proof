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
      <ProofCockpit report={null} onReport={vi.fn()} onViewDataset={vi.fn()} />
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

  it("auto-fills the System prompt from a dataset's bundled system prompt", async () => {
    const withPrompt = [
      { id: "d1", name: "Plain", description: "", examples: [] },
      {
        id: "bench",
        name: "Governance bench",
        description: "",
        examples: [],
        corpus_id: "c1",
        system_prompt: "You are an advisor. Finish with Citations: [source_id].",
      },
    ];
    vi.spyOn(api, "getDatasets").mockResolvedValue(withPrompt as never);
    vi.spyOn(api, "getSelection").mockResolvedValue(SELECTION as never);
    vi.spyOn(api, "getRecipes").mockResolvedValue(RECIPES as never);
    wrap();
    await waitFor(() => screen.getByLabelText(/^Dataset$/i));
    // Select the bench dataset → its contract lands in the System prompt field.
    fireEvent.change(screen.getByLabelText(/^Dataset$/i), { target: { value: "bench" } });
    await waitFor(() =>
      expect((screen.getByLabelText(/System prompt/i) as HTMLTextAreaElement).value).toBe(
        "You are an advisor. Finish with Citations: [source_id].",
      ),
    );
  });

  it("swaps the System prompt when switching between datasets (not stranding the prior one)", async () => {
    const benches = [
      { id: "a", name: "Bench A", description: "", examples: [], corpus_id: "c1", system_prompt: "PROMPT A" },
      { id: "b", name: "Bench B", description: "", examples: [], corpus_id: "c1", system_prompt: "PROMPT B" },
      { id: "plain", name: "Plain", description: "", examples: [] },
    ];
    vi.spyOn(api, "getDatasets").mockResolvedValue(benches as never);
    vi.spyOn(api, "getSelection").mockResolvedValue(SELECTION as never);
    vi.spyOn(api, "getRecipes").mockResolvedValue(RECIPES as never);
    wrap();
    await waitFor(() => screen.getByLabelText(/^Dataset$/i));
    const field = () => screen.getByLabelText(/System prompt/i) as HTMLTextAreaElement;

    // Bench A → its prompt fills the field.
    fireEvent.change(screen.getByLabelText(/^Dataset$/i), { target: { value: "a" } });
    await waitFor(() => expect(field().value).toBe("PROMPT A"));

    // Switch to Bench B → the field must now hold B's prompt, not A's (the bug).
    fireEvent.change(screen.getByLabelText(/^Dataset$/i), { target: { value: "b" } });
    await waitFor(() => expect(field().value).toBe("PROMPT B"));

    // Switch to a plain dataset (no prompt) → the auto-filled prompt clears.
    fireEvent.change(screen.getByLabelText(/^Dataset$/i), { target: { value: "plain" } });
    await waitFor(() => expect(field().value).toBe(""));
  });

  it("preserves an operator-edited System prompt across a dataset switch", async () => {
    const benches = [
      { id: "a", name: "Bench A", description: "", examples: [], corpus_id: "c1", system_prompt: "PROMPT A" },
      { id: "b", name: "Bench B", description: "", examples: [], corpus_id: "c1", system_prompt: "PROMPT B" },
    ];
    vi.spyOn(api, "getDatasets").mockResolvedValue(benches as never);
    vi.spyOn(api, "getSelection").mockResolvedValue(SELECTION as never);
    vi.spyOn(api, "getRecipes").mockResolvedValue(RECIPES as never);
    wrap();
    await waitFor(() => screen.getByLabelText(/^Dataset$/i));
    const field = () => screen.getByLabelText(/System prompt/i) as HTMLTextAreaElement;

    fireEvent.change(screen.getByLabelText(/^Dataset$/i), { target: { value: "a" } });
    await waitFor(() => expect(field().value).toBe("PROMPT A"));

    // Operator overrides the prompt by hand.
    fireEvent.change(field(), { target: { value: "MY OWN INSTRUCTION" } });
    expect(field().value).toBe("MY OWN INSTRUCTION");

    // Switching datasets must NOT clobber the operator's text.
    fireEvent.change(screen.getByLabelText(/^Dataset$/i), { target: { value: "b" } });
    await new Promise((r) => setTimeout(r, 0));
    expect(field().value).toBe("MY OWN INSTRUCTION");
  });

  it("preselects a dataset from 'Run proof →' and consumes the one-shot", async () => {
    vi.spyOn(api, "getDatasets").mockResolvedValue(DATASETS as never);
    vi.spyOn(api, "getSelection").mockResolvedValue(SELECTION as never);
    vi.spyOn(api, "getRecipes").mockResolvedValue(RECIPES as never);
    const onConsumed = vi.fn();
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ProofCockpit
          report={null}
          onReport={vi.fn()}
          onViewDataset={vi.fn()}
          preselectDatasetId="d2"
          onPreselectConsumed={onConsumed}
        />
      </QueryClientProvider>,
    );
    // The selector reflects the preselected dataset, not the default first row.
    await waitFor(() =>
      expect((screen.getByLabelText(/^Dataset$/i) as HTMLSelectElement).value).toBe("d2"),
    );
    expect(onConsumed).toHaveBeenCalled();
  });
});

// WS-E2: the guided first-run CTA. Shown only when ≥2 cheap cloud candidates are reachable; clicking
// it preselects the seeded sample + cheap cloud and auto-runs once the sample's judge default lands.
const CLOUD_SELECTION = {
  providers: [
    {
      provider_id: "anthropic",
      label: "Anthropic",
      privacy: "cloud" as const,
      available: true,
      supports_custom: false,
      candidate_id: null,
      models: [
        { candidate_id: "anthropic:haiku", model: "haiku", display_name: "Haiku", tier: "economy" as const, cost_class: "$" as const, context_window: null, latest: false, recommended: true },
      ],
    },
    {
      provider_id: "openai",
      label: "OpenAI",
      privacy: "cloud" as const,
      available: true,
      supports_custom: false,
      candidate_id: null,
      models: [
        { candidate_id: "openai:nano", model: "nano", display_name: "Nano", tier: "economy" as const, cost_class: "$" as const, context_window: null, latest: false, recommended: true },
      ],
    },
  ],
};
const SAMPLE_DATASETS = [
  { id: "sample-investment-memo", name: "Sample · investment memo summarization", description: "", is_sample: true, examples: [{ input_text: "i", expected_text: "e", keypoints: ["22%"] }] },
];
const SETTINGS = { sandbox_enabled: false, thresholds: { similarity: 0.55, keypoint: 0.8, judge: 0.8 } };

describe("ProofCockpit guided first-run CTA (WS-E2)", () => {
  it("hides the CTA when there are no cheap cloud candidates", async () => {
    vi.spyOn(api, "getDatasets").mockResolvedValue(SAMPLE_DATASETS as never);
    vi.spyOn(api, "getSelection").mockResolvedValue(SELECTION as never); // local mock only
    vi.spyOn(api, "getRecipes").mockResolvedValue(RECIPES as never);
    vi.spyOn(api, "getSettings").mockResolvedValue(SETTINGS as never);
    wrap();
    await waitFor(() => screen.getByText(/No proof run yet/i));
    expect(screen.queryByRole("button", { name: /Run the demo proof on real models/i })).toBeNull();
  });

  it("shows the CTA and auto-runs with the judge rubric + cheap cloud candidates", async () => {
    vi.spyOn(api, "getDatasets").mockResolvedValue(SAMPLE_DATASETS as never);
    vi.spyOn(api, "getSelection").mockResolvedValue(CLOUD_SELECTION as never);
    vi.spyOn(api, "getRecipes").mockResolvedValue(RECIPES as never);
    vi.spyOn(api, "getSettings").mockResolvedValue(SETTINGS as never);
    const run = vi
      .spyOn(api, "createRunStream")
      .mockResolvedValue({ run: { id: "r1", mode: "full" } } as never);
    wrap();

    const cta = await screen.findByRole("button", { name: /Run the demo proof on real models/i });
    fireEvent.click(cta);

    await waitFor(() => expect(run).toHaveBeenCalledTimes(1));
    const body = run.mock.calls[0][0] as api.RunRequest;
    expect(body.dataset_id).toBe("sample-investment-memo");
    expect(body.candidate_ids).toEqual(["anthropic:haiku", "openai:nano"]);
    expect(body.rubric?.kind).toBe("judge"); // never the keypoint backend fallback
  });

  it("disarms (does not spin forever) if the user pre-picked a non-judge method", async () => {
    vi.spyOn(api, "getDatasets").mockResolvedValue(SAMPLE_DATASETS as never);
    vi.spyOn(api, "getSelection").mockResolvedValue(CLOUD_SELECTION as never);
    vi.spyOn(api, "getRecipes").mockResolvedValue(RECIPES as never);
    vi.spyOn(api, "getSettings").mockResolvedValue(SETTINGS as never);
    const run = vi.spyOn(api, "createRunStream").mockResolvedValue({ run: { id: "r1", mode: "full" } } as never);
    wrap();

    const cta = await screen.findByRole("button", { name: /Run the demo proof on real models/i });
    // The sample auto-applies the judge on mount. Switch to Keypoint first — this spends the latch
    // with a non-judge rubric, so clicking the demo can never reach a judge rubric.
    fireEvent.click(screen.getByRole("button", { name: /Keypoint/i }));
    fireEvent.click(cta);

    // The button must resolve back to its idle label rather than spin "Preparing…" forever, and no
    // run fires (safety: never run with the wrong rubric).
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /Run the demo proof on real models/i })).toBeEnabled(),
    );
    expect(run).not.toHaveBeenCalled();
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
