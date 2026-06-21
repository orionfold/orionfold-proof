import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { NO_WINNER_REPORT, SAMPLE_REPORT } from "../../test/fixtures";
import { DecisionSummary } from "./ProofCockpit";

describe("DecisionSummary no-winner state", () => {
  it("shows a calm no-winner message when nothing is recommended", () => {
    render(<DecisionSummary brief={NO_WINNER_REPORT.run.brief} leaderboard={NO_WINNER_REPORT.leaderboard} />);
    expect(screen.getByText(/No clear winner/i)).toBeInTheDocument();
    expect(screen.queryByText(/^Recommended$/)).not.toBeInTheDocument();
  });

  it("shows the recommended winner when one passed", () => {
    render(<DecisionSummary brief={SAMPLE_REPORT.run.brief} leaderboard={SAMPLE_REPORT.leaderboard} />);
    expect(screen.getByText(/Recommended/)).toBeInTheDocument();
  });
});

it("shows the scoring method and run cost when provided", () => {
  render(
    <DecisionSummary
      brief={SAMPLE_REPORT.run.brief}
      leaderboard={SAMPLE_REPORT.leaderboard}
      scoredBy="Keypoint coverage"
      cost={{ candidate_cost_usd: 0.01, judge_cost_usd: 0.002, total_cost_usd: 0.012 }}
    />,
  );
  expect(screen.getByText(/Scored by/i)).toBeInTheDocument();
  expect(screen.getByText(/Keypoint coverage/i)).toBeInTheDocument();
  expect(screen.getByText(/Run cost/i)).toBeInTheDocument();
});
