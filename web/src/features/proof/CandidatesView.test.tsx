import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import type { SelectionPanel } from "../../lib/api";
import { CandidatesView } from "./CandidatesView";

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, getSelection: vi.fn() };
});
import { getSelection } from "../../lib/api";

function renderView() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <CandidatesView />
    </QueryClientProvider>,
  );
}

const PANEL: SelectionPanel = {
  providers: [
    {
      provider_id: "anthropic",
      label: "Anthropic",
      privacy: "cloud",
      available: false, // unconfigured cloud → add-key affordance
      supports_custom: true,
      candidate_id: null,
      models: [
        {
          candidate_id: "anthropic:claude-opus-4-8",
          model: "claude-opus-4-8",
          display_name: "Claude Opus 4.8",
          tier: "frontier",
          cost_class: "$$$",
          context_window: 200000,
          latest: true,
          recommended: true,
        },
      ],
    },
    {
      provider_id: "ollama",
      label: "Ollama",
      privacy: "local",
      available: true, // keyless, always reachable as a group; models gate per-model
      supports_custom: true,
      candidate_id: null,
      models: [
        {
          candidate_id: "ollama:llama3.2",
          model: "llama3.2",
          display_name: "Llama 3.2 (local)",
          tier: "economy",
          cost_class: "free",
          context_window: 131072,
          latest: false,
          recommended: true,
          available: true,
        },
        {
          // A curated Orionfold model that hasn't been pulled → "Pull to enable" hint.
          candidate_id: "ollama:hf.co/Orionfold/Saul-7B-Instruct-v1-GGUF",
          model: "hf.co/Orionfold/Saul-7B-Instruct-v1-GGUF",
          display_name: "Saul 7B Instruct (Legal)",
          tier: "balanced",
          cost_class: "free",
          latest: false,
          recommended: false,
          family: "orionfold",
          repo_id: "hf.co/Orionfold/Saul-7B-Instruct-v1-GGUF",
          available: false,
          reason: "Not pulled — run: orionfold pull hf.co/Orionfold/Saul-7B-Instruct-v1-GGUF",
        },
      ],
    },
    {
      provider_id: "openai",
      label: "OpenAI",
      privacy: "cloud",
      available: true, // configured → models listed normally
      supports_custom: true,
      candidate_id: null,
      models: [
        {
          candidate_id: "openai:gpt-4o-mini",
          model: "gpt-4o-mini",
          display_name: "GPT-4o mini",
          tier: "economy",
          cost_class: "$",
          context_window: 128000,
          latest: true,
          recommended: false,
        },
      ],
    },
  ],
};

describe("CandidatesView", () => {
  test("an unconfigured cloud provider shows the add-key affordance and explains its absence", async () => {
    vi.mocked(getSelection).mockResolvedValue(PANEL);
    renderView();

    // The provider is named even though it has no available candidate of its own.
    expect(await screen.findByText("Anthropic")).toBeInTheDocument();
    // Absence is explained, not silent (both unconfigured providers say so).
    expect(screen.getAllByText(/not configured/i).length).toBeGreaterThan(0);
    // The add-key prompt names the env var the cloud provider needs.
    expect(screen.getByText(/ANTHROPIC_API_KEY/)).toBeInTheDocument();
    // The proven inline KeyEntry button is offered (reused component).
    expect(screen.getByRole("button", { name: /add key/i })).toBeInTheDocument();
  });

  test("a curated-but-unpulled Orionfold model shows the Pull-to-enable command hint", async () => {
    vi.mocked(getSelection).mockResolvedValue(PANEL);
    renderView();

    // The model is listed under the available Ollama group, marked not-pulled…
    expect(await screen.findByText("Saul 7B Instruct (Legal)")).toBeInTheDocument();
    expect(screen.getByText(/not pulled/i)).toBeInTheDocument();
    // …with the exact one command that turns it on (the local mirror of "Add key").
    expect(
      screen.getByText(/orionfold pull hf\.co\/Orionfold\/Saul-7B-Instruct-v1-GGUF/),
    ).toBeInTheDocument();
    // A standard local model in the same group has no pull hint.
    expect(screen.getByText("Llama 3.2 (local)")).toBeInTheDocument();
  });

  test("a configured provider lists its models with no add-key prompt", async () => {
    vi.mocked(getSelection).mockResolvedValue(PANEL);
    renderView();

    expect(await screen.findByText("GPT-4o mini")).toBeInTheDocument();
    // Only the unconfigured Anthropic row should offer a key; OpenAI is available.
    expect(screen.getAllByRole("button", { name: /add key/i })).toHaveLength(1);
  });
});
