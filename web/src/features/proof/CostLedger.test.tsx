import { render, screen, within } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import { CostLedger } from "./CostLedger";
import { SAMPLE_REPORT } from "../../test/fixtures";
import type { ProofReport, LeaderboardEntry, ResultRow } from "../../lib/api";

const entry = (over: Partial<LeaderboardEntry>): LeaderboardEntry => ({
  candidate_id: "c",
  label: "Candidate",
  provider_id: "anthropic",
  privacy: "cloud",
  total: 5,
  pass_count: 3,
  pass_rate: 0.6,
  avg_score: 0.6,
  avg_latency_ms: 100,
  total_estimated_cost_usd: 0,
  failure_count: 0,
  error_count: 0,
  recommended: false,
  ...over,
});

const row = (over: Partial<ResultRow>): ResultRow => ({
  candidate_id: "c",
  example_index: 0,
  input_text: "in",
  expected_text: "exp",
  output_text: "out",
  score: 1,
  passed: true,
  latency_ms: 100,
  estimated_cost_usd: 0,
  input_tokens: 0,
  output_tokens: 0,
  judge_cost_usd: 0,
  judge_latency_ms: 0,
  privacy: "cloud",
  error: null,
  ...over,
});

// A populated paid run: Opus (recommended) and Haiku, with a judge cost on Opus.
const PAID_REPORT: ProofReport = {
  ...SAMPLE_REPORT,
  leaderboard: [
    entry({ candidate_id: "opus", label: "Opus", recommended: true }),
    entry({ candidate_id: "haiku", label: "Haiku", privacy: "cloud" }),
  ],
  results: [
    row({ candidate_id: "opus", estimated_cost_usd: 0.06, judge_cost_usd: 0.02, input_tokens: 1000, output_tokens: 200 }),
    row({ candidate_id: "haiku", estimated_cost_usd: 0.02, judge_cost_usd: 0, input_tokens: 900, output_tokens: 150 }),
  ],
  cost_summary: { candidate_cost_usd: 0.08, judge_cost_usd: 0.02, total_cost_usd: 0.1 },
};

describe("CostLedger", () => {
  it("renders the Run cost section with a row per candidate", () => {
    render(<CostLedger report={PAID_REPORT} />);
    const section = screen.getByRole("region", { name: "Run cost" });
    expect(within(section).getByText("Opus")).toBeInTheDocument();
    expect(within(section).getByText("Haiku")).toBeInTheDocument();
  });

  it("INVARIANT: the run total matches the report's cost_summary total (the verdict line)", () => {
    render(<CostLedger report={PAID_REPORT} />);
    // $0.10 total to 4dp, matching DecisionSummary's "Run cost: … total $0.1000".
    expect(screen.getByTestId("run-cost-total")).toHaveTextContent("$0.1000");
  });

  it("shows judge $ where a judge ran and a dash where none did", () => {
    render(<CostLedger report={PAID_REPORT} />);
    // Opus judged ($0.0200) → that figure appears (once in the Opus row, once in the
    // run-total footer since it's the only judge spend); Haiku didn't → its row shows "—".
    expect(screen.getAllByText("$0.0200").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(1);
  });

  it("renders a calm Free state for a zero-cost (mock/local) run", () => {
    render(<CostLedger report={SAMPLE_REPORT} />);
    expect(screen.getByTestId("run-cost-total")).toHaveTextContent("Free");
    expect(screen.getByText(/No spend/i)).toBeInTheDocument();
  });

  it("returns nothing when the leaderboard is empty", () => {
    const { container } = render(
      <CostLedger report={{ ...SAMPLE_REPORT, leaderboard: [], results: [] }} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
