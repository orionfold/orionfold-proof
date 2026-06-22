import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { Leaderboard } from "./Leaderboard";
import type { LeaderboardEntry } from "../../lib/api";

function entry(over: Partial<LeaderboardEntry>): LeaderboardEntry {
  return {
    candidate_id: "c", label: "Cand", provider_id: "ollama", privacy: "local",
    total: 5, pass_count: 4, pass_rate: 0.8, avg_score: 0.8, avg_latency_ms: 100,
    total_estimated_cost_usd: 0.01, failure_count: 1, error_count: 0,
    recommended: false, cost_per_quality: 0.0125, ...over,
  };
}

test("medals decorate the top 3 only when a winner exists", () => {
  const entries = [
    entry({ candidate_id: "a", recommended: true, pass_rate: 1, pass_count: 5, failure_count: 0 }),
    entry({ candidate_id: "b" }),
    entry({ candidate_id: "c" }),
    entry({ candidate_id: "d" }),
  ];
  render(<Leaderboard entries={entries} />);
  expect(screen.getByText("🥇")).toBeInTheDocument();
  expect(screen.getByText("🥈")).toBeInTheDocument();
  expect(screen.getByText("🥉")).toBeInTheDocument();
});

test("no medals in the no-winner state — plain rank numbers", () => {
  const entries = [
    entry({ candidate_id: "a", recommended: false, pass_rate: 0.2, pass_count: 1, failure_count: 4 }),
    entry({ candidate_id: "b", recommended: false }),
  ];
  const { container } = render(<Leaderboard entries={entries} />);
  expect(container.textContent).not.toContain("🥇");
  // The rank cell is the first <td> of each row — plain sequential numbers, no medals.
  const rankCells = [...container.querySelectorAll("tbody tr")].map(
    (tr) => tr.querySelector("td")!.textContent,
  );
  expect(rankCells).toEqual(["1", "2"]);
});

test("score bar uses the traffic-light status token for the pass rate", () => {
  const { container } = render(
    <Leaderboard entries={[entry({ pass_rate: 0.2, pass_count: 1, failure_count: 4 })]} />,
  );
  // A <0.5 pass rate paints the bar danger — a status token, never the accent.
  expect(container.innerHTML).toContain("bg-(--color-danger)");
  expect(container.innerHTML).not.toContain("--color-accent");
});

test("$/quality cell renders Free / em-dash / value", () => {
  render(
    <Leaderboard
      entries={[
        entry({ candidate_id: "free", cost_per_quality: 0 }),
        entry({ candidate_id: "none", cost_per_quality: null }),
        entry({ candidate_id: "paid", cost_per_quality: 0.004 }),
      ]}
    />,
  );
  expect(screen.getByText("Free")).toBeInTheDocument();
  expect(screen.getByText("—")).toBeInTheDocument();
  expect(screen.getByText("$0.0040")).toBeInTheDocument();
});
