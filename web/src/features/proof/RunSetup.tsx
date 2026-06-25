import type { ReactNode } from "react";
import type {
  Dataset,
  ProofBrief,
  ProviderHealth,
  PromptVariant,
  SelectionPanel,
} from "../../lib/api";
import { CandidatePicker } from "./CandidatePicker";
import { RecheckHealthButton } from "./RecheckHealthButton";
import { PromptVariants } from "./PromptVariants.tsx";
import { ScoringMethod, type Rubric } from "./ScoringMethod";
import { SelectField } from "./SelectField";
import { Step, StepLine } from "./WorkflowStep";
import { EvalTypeBadge } from "./EvalTypeBadge";
import { TagChips } from "./TagChips";
import { inputCls } from "./formStyles";
import { validPromptVariants } from "./promptVariantsHelpers";

// The setup is deliberately small: pick a dataset, pick candidates, frame the decision, run.
// A Proof Brief (not a wizard in v0) keeps the receipt anchored to a real decision.
export interface RunSetupProps {
  datasets: Dataset[];
  panel: SelectionPanel;
  datasetId: string;
  onDatasetChange: (id: string) => void;
  // Open the Datasets view with the selected dataset expanded (the summary's "View details" link).
  onViewDataset: (id: string) => void;
  selectedCandidates: string[];
  onToggleCandidate: (id: string) => void;
  // Per-provider liveness map + recheck control (grays out failing providers in the picker).
  health?: Map<string, ProviderHealth>;
  isCheckingHealth?: boolean;
  onRecheckHealth?: () => void;
  brief: ProofBrief;
  onBriefChange: (brief: ProofBrief) => void;
  onRun: () => void;
  isRunning: boolean;
  hasRun: boolean;
  error: string | null;
  rubric: Rubric | null;
  onRubricChange: (next: Rubric | null) => void;
  compareBy: "models" | "prompts" | "quick";
  onCompareByChange: (mode: "models" | "prompts" | "quick") => void;
  promptVariants: PromptVariant[];
  onPromptVariantsChange: (next: PromptVariant[]) => void;
  promptModel: string;
  onPromptModelChange: (id: string) => void;
  quickPrompt: string;
  onQuickPromptChange: (s: string) => void;
  // Models-mode task instruction: one system prompt applied to every selected candidate.
  modelInstruction: string;
  onModelInstructionChange: (s: string) => void;
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
    onViewDataset,
    selectedCandidates,
    onToggleCandidate,
    health,
    isCheckingHealth,
    onRecheckHealth,
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
    quickPrompt,
    onQuickPromptChange,
    modelInstruction,
    onModelInstructionChange,
    recipes,
  } = props;

  const canRun =
    brief.task_name.trim().length > 0 &&
    (compareBy === "prompts"
      ? Boolean(promptModel) && validPromptVariants(promptVariants)
      : compareBy === "quick"
        ? quickPrompt.trim().length > 0 && selectedCandidates.length === 2
        : selectedCandidates.length > 0);
  // Before the very first run, give the primary action a gentle, one-glance affordance.
  const firstRun = !hasRun && !isRunning;

  // The dataset under test — surfaced as a summary so the operator knows what they're running on
  // before they run. Quick mode scores no dataset, so the summary only shows for models/prompts.
  const selectedDataset = datasets.find((d) => d.id === datasetId);

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
            {compareBy !== "quick" && (
              <>
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
              </>
            )}

            <Step n={compareBy === "quick" ? 1 : 2} label="Compare by">
              <div role="group" aria-label="Compare by" className="inline-flex w-fit rounded-lg border border-(--color-panel-line) p-0.5 text-sm">
                {(["models", "prompts", "quick"] as const).map((mode) => (
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
                    {mode === "quick" ? "Quick ⚡" : mode}
                  </button>
                ))}
              </div>
            </Step>
          </div>

          {compareBy === "quick" ? (
            <span className="text-xs text-(--color-ink-faint)">
              One prompt, two candidates, head-to-head — eyeball the outputs and pick a winner.
            </span>
          ) : selectedDataset ? (
            <DatasetSummary dataset={selectedDataset} onViewDetails={() => onViewDataset(selectedDataset.id)} />
          ) : (
            <span className="text-xs text-(--color-ink-faint)">
              The frozen examples every candidate is scored on.
            </span>
          )}
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
          ) : compareBy === "quick" ? (
            <div className="grid gap-4">
              <label className="grid gap-1.5 text-sm">
                <span className="text-(--color-ink-muted)">Prompt</span>
                <textarea
                  aria-label="Prompt"
                  value={quickPrompt}
                  onChange={(e) => onQuickPromptChange(e.target.value)}
                  rows={4}
                  placeholder="Paste one prompt — both candidates answer it."
                  className={inputCls + " resize-y"}
                />
              </label>
              <CandidatePicker
                panel={panel}
                selected={selectedCandidates}
                onToggle={onToggleCandidate}
                health={health}
              />
              {selectedCandidates.length !== 2 && (
                <p className="text-xs text-(--color-ink-faint)">Pick exactly 2 candidates to compare.</p>
              )}
            </div>
          ) : (
            // Decision recipes pre-fill the model panel below, so they live inside the Models
            // section (not above the whole form) and only when comparing models.
            <div className="grid gap-6">
              {recipes}
              <CandidatePicker
                panel={panel}
                selected={selectedCandidates}
                onToggle={onToggleCandidate}
                health={health}
                headerAction={
                  <RecheckHealthButton
                    isChecking={isCheckingHealth}
                    onRecheck={onRecheckHealth}
                  />
                }
              />
              <label className="grid gap-1.5 text-sm">
                <span className="text-(--color-ink-muted)">System prompt (optional)</span>
                <textarea
                  aria-label="System prompt"
                  value={modelInstruction}
                  onChange={(e) => onModelInstructionChange(e.target.value)}
                  rows={3}
                  placeholder="Classify the ticket into exactly one of: billing, bug, how-to, feature-request, account-access. Reply with only the label."
                  className={inputCls + " resize-y"}
                />
                <span className="text-xs text-(--color-ink-faint)">
                  One system instruction applied to every candidate — use it to make the models
                  classify, extract, or format rather than answer freely. Becomes part of the proof.
                </span>
              </label>
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

        {compareBy !== "quick" && (
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
        )}

        {compareBy !== "quick" && (
          <ScoringMethod
            value={rubric}
            onChange={onRubricChange}
            dataset={datasets.find((d) => d.id === datasetId)}
          />
        )}

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

// A one-glance summary of the dataset a run will score against: what it contains, how big it is,
// a peek at the first input's shape, and a deep-link into the full Datasets view. Shown below the
// dataset selector so the operator knows what they're running before they run it.
function DatasetSummary({
  dataset,
  onViewDetails,
}: {
  dataset: Dataset;
  onViewDetails: () => void;
}) {
  const count = dataset.examples.length;
  const tags = dataset.tags ?? [];
  // The shape of the data: the first row's input, trimmed to roughly two lines (clamped in CSS).
  const first = dataset.examples[0];
  const sample = first ? truncate(first.input_text, 280) : "";

  return (
    <div className="rounded-lg border border-(--color-panel-line) bg-(--color-panel)/40 px-3.5 py-3 text-sm">
      <p className="text-(--color-ink-muted)">
        {dataset.description?.trim()
          ? dataset.description
          : "The frozen examples every candidate is scored on."}
      </p>

      {/* Badges (what's in the set) left-aligned; View details right-aligned, same row. */}
      <div className="mt-2 flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5">
        <div className="flex flex-wrap items-center gap-1.5">
          <EvalTypeBadge dataset={dataset} />
          <span className="of-tag">
            {count} example{count === 1 ? "" : "s"}
          </span>
          <TagChips tags={tags} />
          {dataset.system_prompt?.trim() && (
            <span
              className="of-tag of-tag--t3"
              title="This dataset ships a system prompt (e.g. a citation/refusal contract), auto-applied to the System prompt field below."
            >
              system prompt
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={onViewDetails}
          className="shrink-0 text-xs font-medium text-(--color-accent) hover:underline"
        >
          View details →
        </button>
      </div>

      {sample && (
        <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-(--color-ink-faint)">
          <span className="text-(--color-ink-muted)">e.g.</span> {sample}
        </p>
      )}
    </div>
  );
}

function truncate(s: string, max: number): string {
  const flat = s.replace(/\s+/g, " ").trim();
  return flat.length > max ? flat.slice(0, max - 1) + "…" : flat;
}
