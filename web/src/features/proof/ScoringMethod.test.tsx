// web/src/features/proof/ScoringMethod.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ScoringMethod } from "./ScoringMethod";

// Default mock: correct SelectionPanel shape with no provider groups.
vi.mock("../../lib/api", async (orig) => ({
  ...(await orig<typeof import("../../lib/api")>()),
  getSelection: vi.fn(async () => ({ providers: [] })),
}));

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

describe("ScoringMethod", () => {
  it("defaults to Auto and emits null", () => {
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} />));
    expect(screen.getByText(/Auto/i)).toBeInTheDocument();
  });

  it("emits a keypoint rubric when Keypoint is chosen", () => {
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} />));
    fireEvent.click(screen.getByRole("button", { name: /Keypoint/i }));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ kind: "keypoint" }));
  });

  it("offers a keyless Mock judge when LLM judge is chosen", () => {
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} />));
    fireEvent.click(screen.getByRole("button", { name: /LLM judge/i }));
    expect(screen.getByText(/Mock judge/i)).toBeInTheDocument();
  });

  it("shows KeyEntry hint when LLM judge selected and provider is unavailable cloud", async () => {
    const { getSelection } = await import("../../lib/api");
    vi.mocked(getSelection).mockResolvedValueOnce({
      providers: [
        {
          provider_id: "anthropic",
          label: "Anthropic",
          privacy: "cloud",
          available: false,
          supports_custom: false,
          candidate_id: null,
          models: [],
        },
      ],
    });

    const onChange = vi.fn();
    render(
      wrap(
        <QueryClientProvider client={new QueryClient()}>
          <ScoringMethod value={null} onChange={onChange} />
        </QueryClientProvider>,
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: /LLM judge/i }));
    // Wait for the async query to resolve
    expect(await screen.findByText(/add a key/i)).toBeInTheDocument();
  });

  it("shows a clickable model chip and emits judge rubric when available cloud provider has models", async () => {
    const { getSelection } = await import("../../lib/api");
    vi.mocked(getSelection).mockResolvedValueOnce({
      providers: [
        {
          provider_id: "openai",
          label: "OpenAI",
          privacy: "cloud",
          available: true,
          supports_custom: false,
          candidate_id: null,
          models: [
            {
              candidate_id: "openai-gpt-5-4-nano",
              model: "gpt-5.4-nano",
              display_name: "GPT-5.4 nano",
              tier: "economy",
              cost_class: "$",
              context_window: null,
              latest: false,
              recommended: false,
            },
          ],
        },
      ],
    });

    const onChange = vi.fn();
    render(
      wrap(
        <QueryClientProvider client={new QueryClient()}>
          <ScoringMethod value={null} onChange={onChange} />
        </QueryClientProvider>,
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: /LLM judge/i }));

    // Wait for the async query to resolve and the chip to appear
    const chip = await screen.findByRole("button", { name: /GPT-5\.4 nano/i });
    expect(chip).toBeInTheDocument();

    fireEvent.click(chip);
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: "judge",
        judge_provider_id: "openai",
        judge_model: "gpt-5.4-nano",
      }),
    );
  });
});
