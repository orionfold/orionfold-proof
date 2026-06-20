import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { RunProgress } from "./RunProgress";
import type { RunStartEvent } from "../../lib/api";

const START: RunStartEvent = {
  type: "start",
  total: 6,
  n_examples: 3,
  candidates: [
    { id: "a", label: "Cand A", provider_id: "mock_good", privacy: "local" },
    { id: "b", label: "Cand B", provider_id: "ollama", privacy: "local" },
  ],
};

test("derives the current cell and per-candidate progress from the done count", () => {
  // 4 of 6 cells done, candidate-major: A fully done (3/3), B on its 2nd example.
  render(<RunProgress start={START} done={4} />);

  expect(screen.getByText("4/6")).toBeInTheDocument();
  // The "now running" line names candidate B on its 2nd example (B also appears in the list).
  const nowRunning = screen.getByText(/Now running/);
  expect(nowRunning).toHaveTextContent("Cand B");
  expect(nowRunning).toHaveTextContent("example 2 of 3");

  // Per-candidate counts: A complete, B partway.
  expect(screen.getByText("3/3")).toBeInTheDocument();
  expect(screen.getByText("1/3")).toBeInTheDocument();

  const bar = screen.getByRole("progressbar");
  expect(bar).toHaveAttribute("aria-valuenow", "4");
  expect(bar).toHaveAttribute("aria-valuemax", "6");
});

test("shows a finishing message once every cell is done", () => {
  render(<RunProgress start={START} done={6} />);
  expect(screen.getByText(/Scoring outputs and assembling the receipt/)).toBeInTheDocument();
});
