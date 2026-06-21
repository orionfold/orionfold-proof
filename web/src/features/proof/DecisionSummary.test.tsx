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
