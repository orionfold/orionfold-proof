import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { JudgeFilter } from "./JudgeFilter";
import { getSelection } from "../../lib/api";

vi.mock("../../lib/api", async (orig) => ({
  ...(await orig<typeof import("../../lib/api")>()),
  getSelection: vi.fn(async () => ({
    providers: [
      { provider_id: "anthropic", label: "Anthropic", privacy: "cloud", available: false, supports_custom: false, candidate_id: null, models: [] },
    ],
  })),
}));

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

describe("JudgeFilter", () => {
  it("defaults to Local + Cheapest with Mock judge selected", () => {
    render(wrap(<JudgeFilter selectedProviderId="mock_judge" selectedModel={null} onPick={() => {}} />));
    expect(screen.getByRole("button", { name: /Local/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /Cheapest/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(/Mock judge/i)).toBeInTheDocument();
  });

  it("shows KeyEntry for an unavailable cloud provider after switching to Hosted", async () => {
    render(wrap(<JudgeFilter selectedProviderId="mock_judge" selectedModel={null} onPick={() => {}} />));
    fireEvent.click(screen.getByRole("button", { name: /Hosted/i }));
    expect(await screen.findByText(/add a key/i)).toBeInTheDocument();
  });

  it("emits the new cell's default when switching to a populated cell", async () => {
    vi.mocked(getSelection).mockResolvedValueOnce({
      providers: [
        { provider_id: "ollama", label: "Ollama", privacy: "local", available: true, supports_custom: false, candidate_id: null,
          models: [{ candidate_id: "o1", model: "llama-eco", display_name: "Llama eco", tier: "economy", cost_class: "free", context_window: null, latest: false, recommended: false }] },
        { provider_id: "anthropic", label: "Anthropic", privacy: "cloud", available: true, supports_custom: false, candidate_id: null,
          models: [{ candidate_id: "a1", model: "haiku", display_name: "Haiku", tier: "economy", cost_class: "$", context_window: null, latest: false, recommended: true }] },
      ],
    });
    const onPick = vi.fn();
    render(wrap(<JudgeFilter selectedProviderId="mock_judge" selectedModel={null} onPick={onPick} />));
    await screen.findByRole("option", { name: /Llama eco/i }); // panel loaded at local+economy
    onPick.mockClear();
    fireEvent.click(screen.getByRole("button", { name: /Hosted/i }));
    expect(onPick).toHaveBeenCalledWith("anthropic", "haiku"); // cloud+economy default = recommended Haiku
  });

  it("does NOT emit when switching to a gated-only cell (keeps the prior judge)", async () => {
    vi.mocked(getSelection).mockResolvedValueOnce({
      providers: [
        { provider_id: "ollama", label: "Ollama", privacy: "local", available: true, supports_custom: false, candidate_id: null,
          models: [{ candidate_id: "o1", model: "llama-eco", display_name: "Llama eco", tier: "economy", cost_class: "free", context_window: null, latest: false, recommended: false }] },
        { provider_id: "anthropic", label: "Anthropic", privacy: "cloud", available: false, supports_custom: false, candidate_id: null, models: [] },
      ],
    });
    const onPick = vi.fn();
    render(wrap(<JudgeFilter selectedProviderId="mock_judge" selectedModel={null} onPick={onPick} />));
    await screen.findByRole("option", { name: /Llama eco/i });
    onPick.mockClear();
    fireEvent.click(screen.getByRole("button", { name: /Hosted/i }));
    expect(onPick).not.toHaveBeenCalled(); // cloud+economy = gated-only (no options) → no emit
    expect(await screen.findByText(/add a key/i)).toBeInTheDocument();
  });

  it("decodes a dropdown selection into provider + model", async () => {
    vi.mocked(getSelection).mockResolvedValueOnce({
      providers: [
        { provider_id: "ollama", label: "Ollama", privacy: "local", available: true, supports_custom: false, candidate_id: null,
          models: [{ candidate_id: "o1", model: "llama-eco", display_name: "Llama eco", tier: "economy", cost_class: "free", context_window: null, latest: false, recommended: false }] },
      ],
    });
    const onPick = vi.fn();
    render(wrap(<JudgeFilter selectedProviderId="mock_judge" selectedModel={null} onPick={onPick} />));
    await screen.findByRole("option", { name: /Llama eco/i });
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "ollama::llama-eco" } });
    expect(onPick).toHaveBeenCalledWith("ollama", "llama-eco");
  });
});
