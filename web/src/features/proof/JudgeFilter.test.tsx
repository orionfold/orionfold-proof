import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { JudgeFilter } from "./JudgeFilter";

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
});
