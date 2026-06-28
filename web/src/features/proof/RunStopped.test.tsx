import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { RunProgress } from "./RunProgress";
import { RunStopped } from "./RunStopped";
import type { RunStartEvent } from "../../lib/api";

const start: RunStartEvent = {
  type: "start",
  total: 4,
  n_examples: 2,
  candidates: [
    { id: "mock_good", label: "Mock · good", provider_id: "mock_good", privacy: "local" },
    { id: "mock_bad", label: "Mock · bad", provider_id: "mock_bad", privacy: "local" },
  ],
};

describe("RunProgress Stop button", () => {
  it("renders a Stop button mid-run and calls onStop when clicked", () => {
    const onStop = vi.fn();
    render(<RunProgress start={start} completed={{ mock_good: 1 }} onStop={onStop} />);
    const stop = screen.getByRole("button", { name: /Stop run/i });
    fireEvent.click(stop);
    expect(onStop).toHaveBeenCalledTimes(1);
  });

  it("omits the Stop button once the run is finishing (all cells done)", () => {
    render(
      <RunProgress start={start} completed={{ mock_good: 2, mock_bad: 2 }} onStop={() => {}} />,
    );
    expect(screen.queryByRole("button", { name: /Stop run/i })).toBeNull();
  });

  it("omits the Stop button when no onStop handler is given", () => {
    render(<RunProgress start={start} completed={{ mock_good: 1 }} />);
    expect(screen.queryByRole("button", { name: /Stop run/i })).toBeNull();
  });
});

describe("RunStopped panel", () => {
  it("shows the discard notice, cell count, and incurred cost, and Start over fires", () => {
    const onStartOver = vi.fn();
    render(
      <RunStopped
        summary={{ completedCells: 3, totalCells: 10, incurredCost: 0.0042 }}
        onStartOver={onStartOver}
      />,
    );
    expect(screen.getByText(/partial results not saved/i)).toBeInTheDocument();
    expect(screen.getByText(/3 of 10 checks completed/i)).toBeInTheDocument();
    // Sub-cent spend renders at 4dp.
    expect(screen.getByText(/already spent ~\$0\.0042/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Start over/i }));
    expect(onStartOver).toHaveBeenCalledTimes(1);
  });

  it("omits the dollar line entirely on a free (zero-cost) run", () => {
    render(
      <RunStopped
        summary={{ completedCells: 2, totalCells: 6, incurredCost: 0 }}
        onStartOver={() => {}}
      />,
    );
    expect(screen.getByText(/2 of 6 checks completed/i)).toBeInTheDocument();
    expect(screen.queryByText(/already spent/i)).toBeNull();
  });
});
