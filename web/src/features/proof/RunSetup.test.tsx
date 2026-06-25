import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
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
    onViewDataset: () => {},
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
    quickPrompt: "",
    onQuickPromptChange: () => {},
    modelInstruction: "",
    onModelInstructionChange: () => {},
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

  it("quick mode: disables Run until a prompt + exactly 2 candidates", () => {
    const { rerender } = renderRunSetup({ compareBy: "quick", selectedCandidates: [] });
    expect(screen.getByRole("button", { name: /Run proof/i })).toBeDisabled();
    rerender(
      wrap(
        <RunSetup
          {...({
            datasets, panel, datasetId: "d", onDatasetChange: () => {}, onViewDataset: () => {},
            selectedCandidates: ["mock_good", "mock_bad"], onToggleCandidate: () => {},
            brief: { task_name: "T", decision_question: "Q", success_criteria: "" },
            onBriefChange: () => {}, onRun: () => {}, isRunning: false, hasRun: false, error: null,
            rubric: null, onRubricChange: () => {}, compareBy: "quick", onCompareByChange: () => {},
            promptVariants: STARTER_VARIANTS, onPromptVariantsChange: () => {},
            promptModel: "mock_good", onPromptModelChange: () => {},
            quickPrompt: "Summarize this", onQuickPromptChange: () => {},
            modelInstruction: "", onModelInstructionChange: () => {},
          } satisfies RunSetupProps)}
        />,
      ),
    );
    expect(screen.getByRole("button", { name: /Run proof/i })).toBeEnabled();
  });

  it("models mode: edits the optional System prompt", () => {
    const onModelInstructionChange = vi.fn();
    renderRunSetup({ compareBy: "models", onModelInstructionChange });
    fireEvent.change(screen.getByLabelText(/System prompt/i), {
      target: { value: "Reply with only the label." },
    });
    expect(onModelInstructionChange).toHaveBeenCalledWith("Reply with only the label.");
  });

  it("hides the System prompt outside Models mode", () => {
    renderRunSetup({ compareBy: "prompts" });
    expect(screen.queryByLabelText(/System prompt/i)).not.toBeInTheDocument();
  });

  it("quick mode: shows a hint when not exactly 2 candidates and edits the prompt", () => {
    const onQuickPromptChange = vi.fn();
    renderRunSetup({ compareBy: "quick", selectedCandidates: ["mock_good"], onQuickPromptChange });
    expect(screen.getByText(/exactly 2/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/^Prompt$/i), { target: { value: "hello" } });
    expect(onQuickPromptChange).toHaveBeenCalledWith("hello");
  });
});
