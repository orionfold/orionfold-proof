import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BadgeCheck, LoaderCircle } from "lucide-react";

import {
  createRunStream,
  getSelection,
  getDatasets,
  getRecipes,
  scoredByLabel,
  seedSampleData,
  type LeaderboardEntry,
  type ProofBrief,
  type PromptVariant,
  type ProofReport,
  type ResolvedRecipe,
  type ResultRow,
  type RunRequest,
  type RunStartEvent,
  type RunCostSummary,
} from "../../lib/api";
import { cheapCloudCandidates } from "./scoring";
import { effectiveDecisionQuestion, quickDecisionHeadline } from "./briefHelpers";
import { STARTER_VARIANTS, cleanVariants, defaultPromptModel } from "./promptVariantsHelpers";
import { type Rubric } from "./ScoringMethod";
import { ProviderTag } from "./badges";
import { CostLedger } from "./CostLedger";
import { FailureCases } from "./FailureCases";
import { FrontierScatter } from "./FrontierScatter";
import { Inspector } from "./Inspector";
import { Leaderboard } from "./Leaderboard";
import { QuickCompare } from "./QuickCompare";
import { RecipeRow } from "./RecipeRow";
import { RunProgress } from "./RunProgress";
import { RunSetup } from "./RunSetup";
import { StageStepper } from "./StageStepper";

const DEFAULT_BRIEF: ProofBrief = {
  task_name: "Investment memo summarization",
  decision_question: "Which model should I trust for client memo summaries?",
  success_criteria: "",
};

// Orchestrates the core loop across two panes: the main workspace (setup → decision →
// leaderboard → failure cases) and the right inspector (config, receipt, selected failure).
// Server state (datasets, candidates) comes through TanStack Query; the run is a mutation.
// `report` is controlled by App so a past run opened from Receipts hydrates the same cockpit.
export function ProofCockpit({
  report,
  onReport,
  onViewDataset,
}: {
  report: ProofReport | null;
  onReport: (report: ProofReport) => void;
  // Jump to the Datasets view with a given dataset expanded (the "View details" link on the
  // Proof Run dataset summary). App owns navigation, so the cockpit only forwards the request.
  onViewDataset: (id: string) => void;
}) {
  const queryClient = useQueryClient();
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: getDatasets });
  const selection = useQuery({ queryKey: ["selection"], queryFn: getSelection });
  const recipes = useQuery({ queryKey: ["recipes"], queryFn: getRecipes });

  const [datasetId, setDatasetId] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [brief, setBrief] = useState<ProofBrief>(DEFAULT_BRIEF);
  const [rubric, setRubric] = useState<Rubric | null>(null);
  const [compareBy, setCompareBy] = useState<"models" | "prompts" | "quick">("models");
  const [quickPrompt, setQuickPrompt] = useState("");
  // Models-mode task instruction: one system prompt applied to every selected candidate, so a
  // classification/extraction proof makes the models classify instead of "helping the user."
  const [modelInstruction, setModelInstruction] = useState("");
  const [promptVariants, setPromptVariants] = useState<PromptVariant[]>(STARTER_VARIANTS);
  const [promptModel, setPromptModel] = useState("");
  // The Task name headlines the receipt, so it should describe the dataset under test. Until the
  // user types their own, mirror it from the selected dataset — otherwise a receipt for an
  // imported set would inherit the bundled dataset's name. Editing the field locks it.
  const [taskNameTouched, setTaskNameTouched] = useState(false);
  // The decision question headlines the receipt. Like the task name it follows the dataset until
  // the user owns it — but with nothing to re-derive from, an untouched question CLEARS on dataset
  // change rather than carrying a question authored for a different dataset (WS-C).
  const [decisionQuestionTouched, setDecisionQuestionTouched] = useState(false);
  // Tracks the system prompt we auto-filled into the System prompt field. Holding the value (not just
  // a "filled?" flag) lets a dataset switch tell "still our auto-fill" from "operator edited it":
  // we replace the former, preserve the latter. Empty string = nothing auto-filled yet.
  const autoFilledPrompt = useRef<string>("");
  const [activeRecipeId, setActiveRecipeId] = useState<string | null>(null);
  const [openFailure, setOpenFailure] = useState<ResultRow | null>(null);
  // Live progress for the streaming run: the plan from the `start` frame + a per-candidate
  // completed-count map. Candidates run concurrently (cloud parallel, local serialized), so cells
  // arrive out of order — we key completion on candidate_id/example_index, never on arrival order.
  const [progress, setProgress] = useState<{
    start: RunStartEvent;
    completed: Record<string, number>;
  } | null>(null);
  // Guided first-run CTA (WS-E2): once the user clicks "Run the demo on real models" we preselect
  // the sample + two cheap cloud candidates, then ARM an auto-run. The judge default resolves
  // asynchronously inside ScoringMethod's effect (rubric goes null → judge), so we can't fire the run
  // in the same tick — the effect below waits until the sample is selected AND the judge rubric has
  // landed, then fires exactly once.
  const [demoArmed, setDemoArmed] = useState(false);

  // Whenever the shown run changes — a fresh run or one reopened from Receipts — clear any
  // failure-case selection so the inspector doesn't show a row from the previous report.
  useEffect(() => {
    setOpenFailure(null);
  }, [report?.run.id]);

  // Sensible defaults once the server data lands: first dataset, and only the keyless,
  // instant candidates (the mocks — no pinned model) pre-selected. Real providers cost money
  // / latency, so the user opts into them explicitly rather than having "Run proof" fire cloud
  // calls on first click. Falls back to all if there are no mocks.
  const resolvedDatasetId = datasetId || datasets.data?.[0]?.id || "";
  // Task name follows the selected dataset's name until the user overrides it.
  const selectedDataset = datasets.data?.find((d) => d.id === resolvedDatasetId);
  // A dataset can ship a system prompt (a bench's citation/refusal/route contract). On each dataset
  // change in Models mode, sync the System prompt field to the new dataset's prompt — UNLESS the
  // operator has edited the box (then we leave their text). "Edited" = the box differs from what we
  // last auto-filled; an empty box or our own prior auto-fill is fair game to replace. This makes a
  // dataset switch swap one bench's contract for the next instead of stranding the first one, while
  // still never clobbering hand-written text. The prompt lands in the receipt's config, so the
  // contract under test stays transparent.
  useEffect(() => {
    if (compareBy !== "models" || !selectedDataset) return;
    const untouched = modelInstruction === autoFilledPrompt.current;
    if (!untouched) return; // operator owns the field — don't touch it
    const next = selectedDataset.system_prompt ?? "";
    if (next !== modelInstruction) setModelInstruction(next);
    autoFilledPrompt.current = next;
  }, [selectedDataset?.id, compareBy]);
  const effectiveBrief: ProofBrief = {
    ...brief,
    task_name: taskNameTouched || !selectedDataset ? brief.task_name : selectedDataset.name,
    decision_question: effectiveDecisionQuestion(brief.decision_question, decisionQuestionTouched),
  };
  const handleBriefChange = (next: ProofBrief) => {
    if (next.task_name !== effectiveBrief.task_name) setTaskNameTouched(true);
    if (next.decision_question !== effectiveBrief.decision_question) {
      setActiveRecipeId(null);
      setDecisionQuestionTouched(true);
    }
    setBrief(next);
  };
  const resolvedSelected = useMemo(() => {
    if (selected.length > 0) return selected;
    // Mocks are now one "mock" provider group, present only when Sandbox is on. Pre-select its
    // models (mock_good / mock_bad) so a sandbox user keeps the one-click keyless run. Off → none.
    const mock = (selection.data?.providers ?? []).find((g) => g.provider_id === "mock");
    return mock ? mock.models.map((m) => m.candidate_id) : [];
  }, [selected, selection.data]);
  const resolvedPromptModel = promptModel || defaultPromptModel(selection.data);

  const runMutation = useMutation({
    mutationFn: (body: RunRequest) =>
      createRunStream(body, {
        onStart: (s) => setProgress({ start: s, completed: {} }),
        onProgress: (p) =>
          setProgress((prev) => {
            if (!prev) return prev;
            // Monotonic per-candidate count, order-independent: a cell at example_index k means at
            // least k+1 of that candidate's examples are done.
            const prior = prev.completed[p.candidate_id] ?? 0;
            const next = Math.max(prior, p.example_index + 1);
            return { ...prev, completed: { ...prev.completed, [p.candidate_id]: next } };
          }),
      }),
    onSuccess: (r) => {
      onReport(r);
      setProgress(null);
      // Keep the Receipts archive current without a manual refetch.
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
    },
    onError: () => setProgress(null),
  });

  // The guided demo targets the bundled sample (detected by `is_sample`, not a hardcoded id — the
  // sample-detection invariant) and two cheap, available cloud candidates. The CTA only shows when
  // both are reachable, so the one-click promise ("real-model clear winner in ~30s") stays honest.
  const sampleDataset = datasets.data?.find((d) => d.is_sample);
  const cheapCloud = useMemo(
    () => cheapCloudCandidates(selection.data),
    [selection.data],
  );
  const canRunDemo = cheapCloud.length === 2;

  // Seed the bundled sample if it isn't present, then refresh datasets and select the new row so the
  // armed auto-run can target it. `seededSampleId` from the counts isn't returned, so we re-find by
  // `is_sample` after the refetch settles (see the select effect below).
  const seedMutation = useMutation({
    mutationFn: seedSampleData,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["datasets"] }),
  });

  // CTA click: preselect the sample + cheap cloud candidates, leave the rubric null (so the sample's
  // judge auto-default fires), and arm the auto-run. Seeds first if the sample isn't loaded yet; the
  // arm effect picks up the freshly-seeded row once the datasets query refetches.
  const startGuidedDemo = () => {
    setCompareBy("models");
    setSelected(cheapCloud);
    setModelInstruction("");
    // Don't reset the rubric: selecting the sample makes ScoringMethod auto-apply the LLM judge, and
    // its latch fires only once per dataset — clearing the rubric here would leave it null forever.
    if (sampleDataset) setDatasetId(sampleDataset.id);
    else seedMutation.mutate();
    setDemoArmed(true);
  };

  // Once armed, make sure the sample dataset is the selected one — covers the seed-then-refetch case
  // where the sample row only appears after the CTA click.
  useEffect(() => {
    if (demoArmed && sampleDataset && resolvedDatasetId !== sampleDataset.id) {
      setDatasetId(sampleDataset.id);
    }
  }, [demoArmed, sampleDataset, resolvedDatasetId]);

  // Auto-run the armed demo once everything has settled: the sample dataset is selected AND the
  // judge rubric has resolved (the sample's FE-only default). Firing only when `rubric.kind` is
  // "judge" guarantees we never start with the keypoint fallback. One-shot: disarm before mutating.
  useEffect(() => {
    if (!demoArmed || runMutation.isPending) return;
    if (!sampleDataset || resolvedDatasetId !== sampleDataset.id) return;
    // The sample is selected. The judge default normally lands here as null → judge. But if the user
    // had already chosen a non-judge method (so the rubric is non-null and ScoringMethod's once-per-
    // dataset latch is spent), the judge will never arrive — disarm rather than spin "Preparing…"
    // forever. Safety holds either way: we never fire a run with the wrong rubric.
    if (rubric !== null && rubric.kind !== "judge") {
      setDemoArmed(false);
      return;
    }
    if (rubric?.kind !== "judge") return;
    setDemoArmed(false);
    runMutation.mutate({
      dataset_id: sampleDataset.id,
      candidate_ids: cheapCloud,
      brief: { ...effectiveBrief, task_name: sampleDataset.name },
      rubric,
    });
    // effectiveBrief/cheapCloud are derived; the guard fields drive the one-shot fire.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demoArmed, runMutation.isPending, sampleDataset?.id, resolvedDatasetId, rubric]);

  const toggleCandidate = (id: string) => {
    setActiveRecipeId(null);
    const base = resolvedSelected;
    if (base.includes(id)) {
      setSelected(base.filter((c) => c !== id));
      return;
    }
    // Quick-compare is strictly head-to-head: a third pick replaces the oldest.
    setSelected(compareBy === "quick" && base.length >= 2 ? [base[1], id] : [...base, id]);
  };

  const onSelectRecipe = (recipe: ResolvedRecipe) => {
    setSelected(recipe.candidate_ids);
    setBrief({ ...effectiveBrief, decision_question: recipe.decision_question });
    // A recipe is a deliberate question choice — keep it through dataset changes (don't clear it).
    setDecisionQuestionTouched(true);
    setActiveRecipeId(recipe.id);
  };

  if (datasets.isLoading || selection.isLoading) {
    return (
      <CenteredNotice>
        <p className="text-(--color-ink-muted)">Loading the local engine…</p>
      </CenteredNotice>
    );
  }
  if (datasets.isError || selection.isError || !datasets.data || !selection.data) {
    return (
      <CenteredNotice>
        <p className="text-(--color-danger)">Could not reach the local engine.</p>
        <p className="text-sm text-(--color-ink-muted)">
          Start it with <code>orionfold up</code>, then reload this page.
        </p>
      </CenteredNotice>
    );
  }

  return (
    <div className="grid min-h-full grid-rows-[auto_auto] lg:grid-cols-[minmax(0,1fr)_22rem] lg:grid-rows-1">
      {/* Skip-to-content target (App's skip link → #main-content). tabIndex -1 lets it receive
          programmatic focus without becoming a tab stop. */}
      <main id="main-content" tabIndex={-1} className="flex flex-col gap-8 px-6 py-8 lg:px-10 focus:outline-none">
        <header className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <h2 className="text-xl font-semibold tracking-tight text-(--color-ink)">Proof Run</h2>
            <p className="text-sm text-(--color-ink-muted)">
              Prove which AI model, prompt, or workflow is worth trusting — privately, with a
              repeatable receipt.
            </p>
          </div>
          <StageStepper stage={report ? "decide" : runMutation.isPending ? "run" : "configure"} />
        </header>

        <RunSetup
          datasets={datasets.data}
          panel={selection.data}
          datasetId={resolvedDatasetId}
          onDatasetChange={setDatasetId}
          onViewDataset={onViewDataset}
          selectedCandidates={resolvedSelected}
          onToggleCandidate={toggleCandidate}
          brief={effectiveBrief}
          onBriefChange={handleBriefChange}
          isRunning={runMutation.isPending}
          error={runMutation.isError ? (runMutation.error as Error).message : null}
          hasRun={report !== null}
          rubric={rubric}
          onRubricChange={setRubric}
          compareBy={compareBy}
          onCompareByChange={setCompareBy}
          promptVariants={promptVariants}
          onPromptVariantsChange={setPromptVariants}
          promptModel={resolvedPromptModel}
          onPromptModelChange={setPromptModel}
          quickPrompt={quickPrompt}
          onQuickPromptChange={setQuickPrompt}
          modelInstruction={modelInstruction}
          onModelInstructionChange={setModelInstruction}
          recipes={
            recipes.data ? (
              <RecipeRow
                panel={recipes.data}
                activeRecipeId={activeRecipeId}
                onSelectRecipe={onSelectRecipe}
              />
            ) : null
          }
          onRun={() =>
            runMutation.mutate(
              compareBy === "prompts"
                ? {
                    dataset_id: resolvedDatasetId,
                    candidate_ids: [resolvedPromptModel],
                    prompt_variants: cleanVariants(promptVariants),
                    brief: effectiveBrief,
                    ...(rubric ? { rubric } : {}),
                  }
                : compareBy === "quick"
                  ? {
                      candidate_ids: resolvedSelected,
                      examples: [{ input_text: quickPrompt, expected_text: "" }],
                      rubric: { kind: "none", threshold: 0, case_sensitive: false },
                      mode: "quick",
                      // Quick mode has no dataset to anchor a title — headline the receipt with the
                      // ad-hoc prompt, never a stale question carried from Models mode (WS-C).
                      brief: {
                        ...effectiveBrief,
                        decision_question: quickDecisionHeadline(quickPrompt),
                      },
                    }
                  : {
                      dataset_id: resolvedDatasetId,
                      candidate_ids: resolvedSelected,
                      brief: effectiveBrief,
                      ...(rubric ? { rubric } : {}),
                      ...(modelInstruction.trim()
                        ? { system_prompt: modelInstruction.trim() }
                        : {}),
                    },
            )
          }
        />

        {runMutation.isPending ? (
          progress ? (
            <RunProgress start={progress.start} completed={progress.completed} />
          ) : (
            <StartingNotice />
          )
        ) : report ? (
          report.run.mode === "quick" ? (
            <div className="motion-safe:animate-reveal">
              <QuickCompare
                report={report}
                onReport={(r) => {
                  onReport(r);
                  void queryClient.invalidateQueries({ queryKey: ["runs"] });
                }}
                onPromote={() => {
                  setCompareBy("models");
                  setSelected(report.run.candidates.map((c) => c.id));
                }}
              />
            </div>
          ) : (
            <div className="flex flex-col gap-8 motion-safe:animate-reveal">
              <DecisionSummary
                brief={report.run.brief}
                leaderboard={report.leaderboard}
                scoredBy={scoredByLabel(report.run.rubric)}
                cost={report.cost_summary}
              />
              <Leaderboard entries={report.leaderboard} />
              <FrontierScatter entries={report.leaderboard} />
              <CostLedger report={report} />
              <FailureCases report={report} selected={openFailure} onSelect={setOpenFailure} />
            </div>
          )
        ) : (
          <EmptyResults
            onRunDemo={canRunDemo ? startGuidedDemo : undefined}
            preparing={demoArmed || seedMutation.isPending}
          />
        )}
      </main>

      <Inspector report={report} selected={openFailure} />
    </div>
  );
}

// A full-height padded block for engine loading/error notices, so they sit calmly in the
// workspace rather than crowding the top-left corner.
function CenteredNotice({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-full items-center justify-center px-6 py-12">
      <div className="grid max-w-sm gap-2 text-center">{children}</div>
    </div>
  );
}

// Top of every results view: the decision, then the recommendation — readable before any
// table. The winner is the one place besides the primary CTA that earns the accent.
export function DecisionSummary({
  brief,
  leaderboard,
  scoredBy,
  cost,
}: {
  brief: ProofBrief;
  leaderboard: LeaderboardEntry[];
  scoredBy?: string;
  cost?: RunCostSummary;
}) {
  const winner = leaderboard.find((e) => e.recommended) ?? null;
  if (leaderboard.length === 0) return null;
  if (!winner) {
    return (
      <section aria-label="Decision" className="grid gap-3">
        <p className="text-sm text-(--color-ink-muted)">
          {brief.decision_question || brief.task_name}
        </p>
        <div className="rounded-xl border border-(--color-panel-line) bg-(--color-panel-card) p-5">
          <span className="text-xs uppercase tracking-wide text-(--color-ink-faint)">
            No clear winner
          </span>
          <p className="mt-2 text-sm text-(--color-ink-muted)">
            No candidate passed the rubric. See the standings below — least-bad first; an
            errored candidate produced no output.
          </p>
          {scoredBy && (
            <p className="mt-1 text-sm text-(--color-ink-faint)">
              Scored by {scoredBy}
              {cost && ` · Run cost: candidate $${cost.candidate_cost_usd.toFixed(4)} · judge $${cost.judge_cost_usd.toFixed(4)} · total $${cost.total_cost_usd.toFixed(4)}`}
            </p>
          )}
        </div>
      </section>
    );
  }
  return (
    <section aria-label="Decision" className="grid gap-3">
      <p className="text-sm text-(--color-ink-muted)">
        {brief.decision_question || brief.task_name}
      </p>
      <div className="rounded-xl border border-(--color-accent)/40 bg-(--color-accent)/[0.08] p-5 motion-safe:animate-emphasis">
        <div className="flex flex-wrap items-center gap-2">
          <span className="flex items-center gap-1 text-xs uppercase tracking-wide text-(--color-accent)">
            <BadgeCheck aria-hidden className="h-3.5 w-3.5" />
            Recommended
          </span>
          <span className="text-lg font-semibold text-(--color-ink)">{winner.label}</span>
          <ProviderTag candidate={winner} />
        </div>
        <p className="mt-2 text-sm tabular-nums text-(--color-ink-muted)">
          Passed {winner.pass_count}/{winner.total} examples ({Math.round(winner.pass_rate * 100)}
          %) · avg score {winner.avg_score.toFixed(2)} · {winner.avg_latency_ms}ms avg · $
          {winner.total_estimated_cost_usd.toFixed(2)} est.
        </p>
        {scoredBy && (
          <p className="mt-1 text-sm tabular-nums text-(--color-ink-faint)">
            Scored by {scoredBy}
            {cost && ` · Run cost: candidate $${cost.candidate_cost_usd.toFixed(4)} · judge $${cost.judge_cost_usd.toFixed(4)} · total $${cost.total_cost_usd.toFixed(4)}`}
          </p>
        )}
      </div>
    </section>
  );
}

// Shown for the brief moment between pressing Run and the first streamed `start` frame.
function StartingNotice() {
  return (
    <section
      aria-label="Proof run progress"
      aria-busy="true"
      className="flex items-center gap-2 text-sm text-(--color-ink-muted)"
    >
      <LoaderCircle aria-hidden className="h-4 w-4 animate-spin text-(--color-accent)" />
      Starting the run…
    </section>
  );
}

function EmptyResults({
  onRunDemo,
  preparing,
}: {
  onRunDemo?: () => void;
  preparing: boolean;
}) {
  return (
    <section aria-label="Results" className="rounded-xl border border-dashed border-(--color-panel-line) p-6">
      <h3 className="text-sm font-medium text-(--color-ink)">No proof run yet</h3>
      <p className="mt-1 max-w-prose text-sm text-(--color-ink-muted)">
        A Proof Run compares your candidates on the same frozen examples so you can decide what to
        trust. No keys yet? Add a provider key, enable{" "}
        <span className="text-(--color-ink)">Sandbox</span> in Settings to try the simulated mocks,
        or seed sample data to explore a finished receipt.
      </p>
      {onRunDemo ? (
        <div className="mt-5 flex flex-col gap-2 border-t border-(--color-panel-line) pt-5">
          <p className="max-w-prose text-sm text-(--color-ink-muted)">
            Or skip the setup: run the bundled investment-memo demo on two cheap cloud models and
            get a scored, client-shareable receipt in about 30 seconds.
          </p>
          <button
            type="button"
            onClick={onRunDemo}
            disabled={preparing}
            className={
              "inline-flex w-fit items-center gap-2 rounded-lg bg-(--color-accent-strong) px-4 py-2 text-sm font-medium text-(--color-accent-ink) transition-opacity hover:opacity-90 disabled:opacity-60" +
              (preparing ? "" : " motion-safe:animate-breathe")
            }
          >
            {preparing ? (
              <LoaderCircle aria-hidden className="h-4 w-4 animate-spin" />
            ) : (
              <BadgeCheck aria-hidden className="h-4 w-4" />
            )}
            {preparing ? "Preparing the demo…" : "Run the demo proof on real models"}
          </button>
        </div>
      ) : null}
    </section>
  );
}
