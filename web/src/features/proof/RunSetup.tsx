import type { ReactNode } from "react";
import type { Dataset, ProofBrief, PromptVariant, SelectionPanel } from "../../lib/api";
import { CandidatePicker } from "./CandidatePicker";
import { PromptVariants } from "./PromptVariants.tsx";
import { ScoringMethod, type Rubric } from "./ScoringMethod";
import { SelectField } from "./SelectField";
import { Step, StepLine } from "./WorkflowStep";
import { inputCls } from "./formStyles";
import { validPromptVariants } from "./promptVariantsHelpers";

// The setup is deliberately small: pick a dataset, pick candidates, frame the decision, run.
// A Proof Brief (not a wizard in v0) keeps the receipt anchored to a real decision.
export interface RunSetupProps {
  datasets: Dataset[];
  panel: SelectionPanel;
  datasetId: string;
  onDatasetChange: (id: string) => void;
  selectedCandidates: string[];
  onToggleCandidate: (id: string) => void;
  brief: ProofBrief;
  onBriefChange: (brief: ProofBrief) => void;
  onRun: () => void;
  isRunning: boolean;
  hasRun: boolean;
  error: string | null;
  rubric: Rubric | null;
  onRubricChange: (next: Rubric | null) => void;
  compareBy: "models" | "prompts";
  onCompareByChange: (mode: "models" | "prompts") => void;
  promptVariants: PromptVariant[];
  onPromptVariantsChange: (next: PromptVariant[]) => void;
  promptModel: string;
  onPromptModelChange: (id: string) => void;
  // Slot for the decision-recipe accelerator, rendered inside the Models section (it pre-fills the
  // model panel, so it's irrelevant when comparing prompts).
  recipes?: ReactNode;
}

export function RunSetup(props: RunSetupProps) {
  const {
    datasets,
    panel,
    datasetId,
    onDatasetChange,
    selectedCandidates,
    onToggleCandidate,
    brief,
    onBriefChange,
    onRun,
    isRunning,
    hasRun,
    error,
    rubric,
    onRubricChange,
    compareBy,
    onCompareByChange,
    promptVariants,
    onPromptVariantsChange,
    promptModel,
    onPromptModelChange,
    recipes,
  } = props;

  const canRun =
    brief.task_name.trim().length > 0 &&
    (compareBy === "prompts"
      ? Boolean(promptModel) && validPromptVariants(promptVariants)
      : selectedCandidates.length > 0);
  // Before the very first run, give the primary action a gentle, one-glance affordance.
  const firstRun = !hasRun && !isRunning;

  return (
    <form
      aria-label="Proof setup"
      className="w-full rounded-xl border border-(--color-panel-line) bg-(--color-panel-card) p-6"
      onSubmit={(e) => {
        e.preventDefault();
        if (canRun && !isRunning) onRun();
      }}
    >
      <div className="grid gap-5">
        {/* Steps 1 + 2 of the run: pick the dataset, then choose what to compare. Inline numbered
            stepper — same badge + connector language as the top StageStepper and the judge picker. */}
        <div className="grid gap-2">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-3">
            <Step n={1} label="Select dataset">
              <SelectField
                aria-label="Dataset"
                className="w-full sm:w-[27rem]"
                value={datasetId}
                onChange={(e) => onDatasetChange(e.target.value)}
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.examples.length} examples)
                  </option>
                ))}
              </SelectField>
            </Step>

            <StepLine />

            <Step n={2} label="Compare by">
              <div role="group" aria-label="Compare by" className="inline-flex w-fit rounded-lg border border-(--color-panel-line) p-0.5 text-sm">
                {(["models", "prompts"] as const).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    aria-pressed={compareBy === mode}
                    onClick={() => onCompareByChange(mode)}
                    className={
                      "rounded-md px-3 py-1.5 capitalize transition-colors " +
                      (compareBy === mode
                        ? "bg-(--color-accent-strong) text-(--color-accent-ink)"
                        : "text-(--color-ink-muted) hover:text-(--color-ink)")
                    }
                  >
                    {mode}
                  </button>
                ))}
              </div>
            </Step>
          </div>

          <span className="text-xs text-(--color-ink-faint)">
            The frozen examples every candidate is scored on.
          </span>
        </div>

        <div>
          {compareBy === "prompts" ? (
            <PromptVariants
              variants={promptVariants}
              modelId={promptModel}
              panel={panel}
              onChangeVariants={onPromptVariantsChange}
              onChangeModel={onPromptModelChange}
            />
          ) : (
            // Decision recipes pre-fill the model panel below, so they live inside the Models
            // section (not above the whole form) and only when comparing models.
            <div className="grid gap-6">
              {recipes}
              <CandidatePicker panel={panel} selected={selectedCandidates} onToggle={onToggleCandidate} />
            </div>
          )}
        </div>

        <label className="grid gap-1.5 text-sm">
          <span className="text-(--color-ink-muted)">Task name</span>
          <input
            value={brief.task_name}
            onChange={(e) => onBriefChange({ ...brief, task_name: e.target.value })}
            className={inputCls}
          />
        </label>

        <label className="grid gap-1.5 text-sm">
          <span className="text-(--color-ink-muted)">Decision question</span>
          <input
            value={brief.decision_question}
            onChange={(e) => onBriefChange({ ...brief, decision_question: e.target.value })}
            className={inputCls}
          />
          <span className="text-xs text-(--color-ink-faint)">
            The question this proof should answer for you — it headlines the receipt.
          </span>
        </label>

        <ScoringMethod
          value={rubric}
          onChange={onRubricChange}
          dataset={datasets.find((d) => d.id === datasetId)}
        />

        {error && (
          <p role="alert" className="text-sm text-(--color-danger)">
            {error}
          </p>
        )}

        <div>
          <button
            type="submit"
            disabled={!canRun || isRunning}
            className={
              "rounded-lg bg-(--color-accent-strong) px-5 py-2.5 font-medium text-(--color-accent-ink) transition-opacity hover:opacity-90 disabled:opacity-40" +
              (firstRun && canRun ? " motion-safe:animate-breathe" : "")
            }
          >
            {isRunning ? "Running proof…" : hasRun ? "Rerun proof" : "Run proof"}
          </button>
        </div>
      </div>
    </form>
  );
}
