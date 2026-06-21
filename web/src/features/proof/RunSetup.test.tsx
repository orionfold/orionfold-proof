import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RunSetup } from "./RunSetup";
import type { Dataset, SelectionPanel } from "../../lib/api";

vi.mock("../../lib/api", async (orig) => ({
  ...(await orig<typeof import("../../lib/api")>()),
  getSelection: vi.fn(async () => ({ providers: [] })),
}));

const datasets: Dataset[] = [{ id: "d", name: "D", description: "", examples: [{ input_text: "i", expected_text: "e", keypoints: ["x"] }] }];
const panel: SelectionPanel = { providers: [] };

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

describe("RunSetup", () => {
  it("renders the scoring method above the run button", () => {
    render(wrap(
      <RunSetup
        datasets={datasets} panel={panel} datasetId="d" onDatasetChange={() => {}}
        selectedCandidates={["mock_good"]} onToggleCandidate={() => {}}
        brief={{ task_name: "T", decision_question: "Q", success_criteria: "" }} onBriefChange={() => {}}
        onRun={() => {}} isRunning={false} hasRun={false} error={null}
        rubric={null} onRubricChange={() => {}}
      />,
    ));
    const scoring = screen.getByText(/Scoring method/i);
    const runBtn = screen.getByRole("button", { name: /Run proof/i });
    // Scoring method appears before the run button in document order.
    expect(scoring.compareDocumentPosition(runBtn) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
