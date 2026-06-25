import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { RunProgress } from "./RunProgress";
import type { RunStartEvent } from "../../lib/api";

const START: RunStartEvent = {
  type: "start",
  total: 6,
  n_examples: 3,
  candidates: [
    { id: "a", label: "Cand A", provider_id: "openai", privacy: "cloud" },
    { id: "b", label: "Cand B", provider_id: "anthropic", privacy: "cloud" },
  ],
};

test("renders per-candidate progress from the completed map", () => {
  // Concurrent: A is done (3/3) while B is partway (1/3) — total 4 of 6.
  render(<RunProgress start={START} completed={{ a: 3, b: 1 }} />);

  expect(screen.getByText("4/6")).toBeInTheDocument();
  // Both candidates are shown with their own counts; B is still running.
  expect(screen.getByText("3/3")).toBeInTheDocument();
  expect(screen.getByText("1/3")).toBeInTheDocument();

  const bar = screen.getByRole("progressbar");
  expect(bar).toHaveAttribute("aria-valuenow", "4");
  expect(bar).toHaveAttribute("aria-valuemax", "6");
});

test("is order-independent: candidate B ahead of A renders correctly", () => {
  // Under concurrency B can outrun A. The component keys on candidate id, not arrival order.
  render(<RunProgress start={START} completed={{ a: 1, b: 3 }} />);
  expect(screen.getByText("4/6")).toBeInTheDocument();
  expect(screen.getByText("1/3")).toBeInTheDocument();
  expect(screen.getByText("3/3")).toBeInTheDocument();
});

test("names the single running candidate, or counts them when several run in parallel", () => {
  // One candidate left running → name it.
  const { unmount } = render(<RunProgress start={START} completed={{ a: 3, b: 1 }} />);
  expect(screen.getByText(/Now running/)).toHaveTextContent("Cand B");
  unmount();

  // Both still running → show the parallel count, not a single name.
  render(<RunProgress start={START} completed={{ a: 1, b: 2 }} />);
  expect(screen.getByText(/in\s*parallel/)).toHaveTextContent("2");
});

test("shows a finishing message once every cell is done", () => {
  render(<RunProgress start={START} completed={{ a: 3, b: 3 }} />);
  expect(screen.getByText(/Scoring outputs and assembling the receipt/)).toBeInTheDocument();
});

test("treats a missing candidate entry as zero done", () => {
  render(<RunProgress start={START} completed={{ a: 2 }} />);
  expect(screen.getByText("2/6")).toBeInTheDocument();
  expect(screen.getByText("2/3")).toBeInTheDocument();
  expect(screen.getByText("0/3")).toBeInTheDocument();
});
