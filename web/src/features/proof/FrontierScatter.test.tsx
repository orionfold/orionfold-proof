import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, beforeAll } from "vitest";

import { FrontierScatter, CandidateDot } from "./FrontierScatter";
import type { ScatterPoint } from "./paretoFrontier";
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

  const populated = [
    entry({ candidate_id: "a", label: "Haiku", total_estimated_cost_usd: 1.0, pass_rate: 0, avg_score: 0.06 }),
    entry({ candidate_id: "b", label: "Opus", total_estimated_cost_usd: 0.5, pass_rate: 0, avg_score: 0.15 }),
  ];

  it("defaults to Pass rate; the metric toggle flips Y to Avg score", () => {
    render(<FrontierScatter entries={populated} />);
    const passBtn = screen.getByRole("button", { name: "Pass rate" });
    const avgBtn = screen.getByRole("button", { name: "Avg score" });
    // First paint = Pass rate (WS-D1 behaviour preserved).
    expect(passBtn).toHaveAttribute("aria-pressed", "true");
    expect(avgBtn).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(avgBtn);
    expect(avgBtn).toHaveAttribute("aria-pressed", "true");
    expect(passBtn).toHaveAttribute("aria-pressed", "false");
    // Axis re-labels — "Avg score" text appears in the rendered chart SVG.
    expect(screen.getAllByText("Avg score").length).toBeGreaterThan(0);
  });

  it("renders the deterministic explainer with a tone matching the run", () => {
    // All-fail-but-real-scores → warn tone, names the avg-score leader.
    render(<FrontierScatter entries={populated} />);
    const explainer = screen.getByTestId("decide-explainer");
    expect(explainer).toHaveAttribute("data-tone", "warn");
    expect(explainer).toHaveTextContent(/0% pass/i);
    expect(explainer).toHaveTextContent("Opus");
  });

  it("explainer text is metric-agnostic — it does not change when the toggle flips", () => {
    render(<FrontierScatter entries={populated} />);
    const before = screen.getByTestId("decide-explainer").textContent;
    fireEvent.click(screen.getByRole("button", { name: "Avg score" }));
    expect(screen.getByTestId("decide-explainer").textContent).toBe(before);
  });

  it("recommended dot draws the accent ring; a non-recommended metric leader does not", () => {
    // Recharts can't compute dot geometry under jsdom, so verify the dot shape directly.
    // The accent follows `recommended`, NOT the higher-quality (metric-leading) point.
    const point = (over: Partial<ScatterPoint>): ScatterPoint => ({
      candidateId: "p",
      label: "P",
      cost: 0.5,
      quality: 0.9,
      recommended: false,
      onFrontier: false,
      ...over,
    });
    const hasAccentRing = (p: ScatterPoint) => {
      const { container } = render(
        <svg>{CandidateDot({ cx: 10, cy: 10, payload: p })}</svg>,
      );
      return container.querySelector('circle[stroke="var(--color-accent)"]') != null;
    };
    // Recommended → accent ring, regardless of quality value (works for either metric).
    expect(hasAccentRing(point({ recommended: true, quality: 0.0 }))).toBe(true);
    expect(hasAccentRing(point({ recommended: true, quality: 0.15 }))).toBe(true);
    // Highest-quality point that is NOT recommended → no accent (status-toned only).
    expect(hasAccentRing(point({ recommended: false, quality: 0.99 }))).toBe(false);
  });
});
