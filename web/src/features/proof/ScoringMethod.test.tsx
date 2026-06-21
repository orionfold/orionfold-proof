// web/src/features/proof/ScoringMethod.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ScoringMethod } from "./ScoringMethod";

vi.mock("../../lib/api", async (orig) => ({
  ...(await orig<typeof import("../../lib/api")>()),
  getSelection: vi.fn(async () => ({ groups: [], mocks: [] })),
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
});
