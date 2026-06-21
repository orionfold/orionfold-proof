import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RunSetup } from "./RunSetup";
import type { Dataset, SelectionPanel } from "../../lib/api";
import { STARTER_VARIANTS } from "./promptVariantsHelpers";
import type { RunSetupProps } from "./RunSetup";

vi.mock("../../lib/api", async (orig) => ({
  ...(await orig<typeof import("../../lib/api")>()),
  getSelection: vi.fn(async () => ({ providers: [] })),
}));

const datasets: Dataset[] = [{ id: "d", name: "D", description: "", examples: [{ input_text: "i", expected_text: "e", keypoints: ["x"] }] }];
const panel: SelectionPanel = { providers: [] };

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

function renderRunSetup(overrides: Partial<RunSetupProps> = {}) {
  const defaults: RunSetupProps = {
    datasets,
    panel,
    datasetId: "d",
    onDatasetChange: () => {},
    selectedCandidates: ["mock_good"],
    onToggleCandidate: () => {},
    brief: { task_name: "T", decision_question: "Q", success_criteria: "" },
    onBriefChange: () => {},
    onRun: () => {},
    isRunning: false,
    hasRun: false,
    error: null,
    rubric: null,
    onRubricChange: () => {},
    compareBy: "models",
    onCompareByChange: () => {},
    promptVariants: STARTER_VARIANTS,
    onPromptVariantsChange: () => {},
    promptModel: "mock_good",
    onPromptModelChange: () => {},
  };
  return render(wrap(<RunSetup {...defaults} {...overrides} />));
}

describe("RunSetup", () => {
  it("renders the scoring method above the run button", () => {
    renderRunSetup();
    const scoring = screen.getByText(/Scoring method/i);
    const runBtn = screen.getByRole("button", { name: /Run proof/i });
    // Scoring method appears before the run button in document order.
    expect(scoring.compareDocumentPosition(runBtn) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("shows the prompt editor when Compare by Prompts is selected", () => {
    renderRunSetup({ compareBy: "prompts" }); // helper passes through to RunSetup props
    expect(screen.getByLabelText(/Prompt model/i)).toBeInTheDocument();
    // The model picker (Models mode) is hidden in Prompts mode.
    expect(screen.queryByText(/^Candidates$/)).not.toBeInTheDocument();
  });

  it("disables Run until two prompt variants are complete", () => {
    renderRunSetup({
      compareBy: "prompts",
      promptVariants: [{ name: "A", system_prompt: "x" }, { name: "B", system_prompt: "" }],
      brief: { task_name: "t", decision_question: "q", success_criteria: "" },
    });
    expect(screen.getByRole("button", { name: /Run proof/ })).toBeDisabled();
  });
});
