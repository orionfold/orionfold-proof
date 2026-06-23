import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ScoringMethod } from "./ScoringMethod";
import type { Dataset } from "../../lib/api";

vi.mock("../../lib/api", async (orig) => ({
  ...(await orig<typeof import("../../lib/api")>()),
  getSelection: vi.fn(async () => ({ providers: [] })),
}));

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}
const kpDataset: Dataset = {
  id: "d", name: "D", description: "",
  examples: [{ input_text: "i", expected_text: "e", keypoints: ["22%"] }],
};

describe("ScoringMethod", () => {
  it("renders the free group with Auto/Keypoint/Similarity and the paid LLM judge", () => {
    render(wrap(<ScoringMethod value={null} onChange={() => {}} dataset={kpDataset} />));
    expect(screen.getByRole("button", { name: /Auto/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Keypoint/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Similarity/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /LLM judge/i })).toBeInTheDocument();
  });

  it("shows what Auto resolves to for the dataset", () => {
    render(wrap(<ScoringMethod value={null} onChange={() => {}} dataset={kpDataset} />));
    expect(screen.getByText(/Keypoint coverage/i)).toBeInTheDocument();
  });

  it("emits a keypoint rubric when Keypoint is chosen", () => {
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} dataset={kpDataset} />));
    fireEvent.click(screen.getByRole("button", { name: /Keypoint/i }));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ kind: "keypoint" }));
  });

  it("emits the lenient similarity default (0.55) from the built-in map", () => {
    // No settings fetch is mocked → the query stays pending and thresholdFor falls back to the map.
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} dataset={kpDataset} />));
    fireEvent.click(screen.getByRole("button", { name: /Similarity/i }));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "similarity", threshold: 0.55 }),
    );
  });

  it("offers the keyless Mock judge when LLM judge is chosen", () => {
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} dataset={kpDataset} />));
    fireEvent.click(screen.getByRole("button", { name: /LLM judge/i }));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ kind: "judge", judge_provider_id: "mock_judge" }));
    expect(screen.getByText(/Mock judge/i)).toBeInTheDocument();
  });
});
