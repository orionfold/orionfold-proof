import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeAll } from "vitest";

import { FrontierScatter } from "./FrontierScatter";
import type { LeaderboardEntry } from "../../lib/api";

// Recharts' ResponsiveContainer measures its parent; jsdom reports 0×0, so stub
// the box so the chart actually renders its SVG in tests.
beforeAll(() => {
  Object.defineProperty(HTMLElement.prototype, "offsetWidth", { configurable: true, value: 640 });
  Object.defineProperty(HTMLElement.prototype, "offsetHeight", { configurable: true, value: 288 });
  // ResizeObserver isn't in jsdom.
  if (!globalThis.ResizeObserver) {
    globalThis.ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    } as unknown as typeof ResizeObserver;
  }
});

function entry(over: Partial<LeaderboardEntry>): LeaderboardEntry {
  return {
    candidate_id: "c",
    label: "Cand",
    provider_id: "mock",
    privacy: "local",
    total: 5,
    pass_count: 3,
    pass_rate: 0.6,
    avg_score: 0.6,
    avg_latency_ms: 100,
    total_estimated_cost_usd: 0.01,
    failure_count: 2,
    error_count: 0,
    recommended: false,
    ...over,
  };
}

describe("FrontierScatter", () => {
  it("shows a calm empty state with fewer than two candidates", () => {
    render(<FrontierScatter entries={[entry({ candidate_id: "only" })]} />);
    expect(screen.getByText(/Not enough candidates/i)).toBeInTheDocument();
    expect(screen.queryByTestId("frontier-scatter")).not.toBeInTheDocument();
  });

  it("renders the chart surface for a populated run", () => {
    render(
      <FrontierScatter
        entries={[
          entry({ candidate_id: "a", total_estimated_cost_usd: 1.0, pass_rate: 0.6 }),
          entry({
            candidate_id: "b",
            label: "Winner",
            total_estimated_cost_usd: 0.5,
            pass_rate: 0.8,
            recommended: true,
          }),
        ]}
      />,
    );
    expect(screen.getByTestId("frontier-scatter")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /cost vs quality/i })).toBeInTheDocument();
  });
});
