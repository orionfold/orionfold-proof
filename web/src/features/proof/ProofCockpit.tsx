import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BadgeCheck, LoaderCircle } from "lucide-react";

import {
  createRunStream,
  getCandidates,
  getDatasets,
  type LeaderboardEntry,
  type ProofBrief,
  type ProofReport,
  type ResultRow,
  type RunRequest,
  type RunStartEvent,
} from "../../lib/api";
import { ProviderTag } from "./badges";
import { FailureCases } from "./FailureCases";
import { Inspector } from "./Inspector";
import { Leaderboard } from "./Leaderboard";
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
}: {
  report: ProofReport | null;
  onReport: (report: ProofReport) => void;
}) {
  const queryClient = useQueryClient();
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: getDatasets });
  const candidates = useQuery({ queryKey: ["candidates"], queryFn: getCandidates });

  const [datasetId, setDatasetId] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [brief, setBrief] = useState<ProofBrief>(DEFAULT_BRIEF);
  // The Task name headlines the receipt, so it should describe the dataset under test. Until the
  // user types their own, mirror it from the selected dataset — otherwise a receipt for an
  // imported set would inherit the bundled dataset's name. Editing the field locks it.
  const [taskNameTouched, setTaskNameTouched] = useState(false);
  const [openFailure, setOpenFailure] = useState<ResultRow | null>(null);
  // Live progress for the streaming run: the plan from the `start` frame + a cumulative count.
  const [progress, setProgress] = useState<{ start: RunStartEvent; done: number } | null>(null);

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
  const effectiveBrief: ProofBrief =
    taskNameTouched || !selectedDataset
      ? brief
      : { ...brief, task_name: selectedDataset.name };
  const handleBriefChange = (next: ProofBrief) => {
    if (next.task_name !== effectiveBrief.task_name) setTaskNameTouched(true);
    setBrief(next);
  };
  const resolvedSelected = useMemo(() => {
    if (selected.length > 0) return selected;
    const all = candidates.data ?? [];
    const keyless = all.filter((c) => !c.model).map((c) => c.id);
    return keyless.length > 0 ? keyless : all.map((c) => c.id);
  }, [selected, candidates.data]);

  const runMutation = useMutation({
    mutationFn: (body: RunRequest) =>
      createRunStream(body, {
        onStart: (s) => setProgress({ start: s, done: 0 }),
        onProgress: (p) => setProgress((prev) => (prev ? { ...prev, done: p.done } : prev)),
      }),
    onSuccess: (r) => {
      onReport(r);
      setProgress(null);
      // Keep the Receipts archive current without a manual refetch.
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
    },
    onError: () => setProgress(null),
  });

  const toggleCandidate = (id: string) => {
    const base = resolvedSelected;
    setSelected(base.includes(id) ? base.filter((c) => c !== id) : [...base, id]);
  };

  if (datasets.isLoading || candidates.isLoading) {
    return (
      <CenteredNotice>
        <p className="text-(--color-ink-muted)">Loading the local engine…</p>
      </CenteredNotice>
    );
  }
  if (datasets.isError || candidates.isError || !datasets.data || !candidates.data) {
    return (
      <CenteredNotice>
        <p className="text-rose-300">Could not reach the local engine.</p>
        <p className="text-sm text-(--color-ink-muted)">
          Start it with <code>orionfold up</code>, then reload this page.
        </p>
      </CenteredNotice>
    );
  }

  return (
    <div className="grid min-h-full grid-rows-[auto_auto] lg:grid-cols-[minmax(0,1fr)_22rem] lg:grid-rows-1">
      <main className="flex flex-col gap-8 px-6 py-8 lg:px-10">
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
          candidates={candidates.data}
          datasetId={resolvedDatasetId}
          onDatasetChange={setDatasetId}
          selectedCandidates={resolvedSelected}
          onToggleCandidate={toggleCandidate}
          brief={effectiveBrief}
          onBriefChange={handleBriefChange}
          isRunning={runMutation.isPending}
          error={runMutation.isError ? (runMutation.error as Error).message : null}
          hasRun={report !== null}
          onRun={() =>
            runMutation.mutate({
              dataset_id: resolvedDatasetId,
              candidate_ids: resolvedSelected,
              brief: effectiveBrief,
            })
          }
        />

        {runMutation.isPending ? (
          progress ? (
            <RunProgress start={progress.start} done={progress.done} />
          ) : (
            <StartingNotice />
          )
        ) : report ? (
          <div className="flex flex-col gap-8 motion-safe:animate-reveal">
            <DecisionSummary brief={report.run.brief} leaderboard={report.leaderboard} />
            <Leaderboard entries={report.leaderboard} />
            <FailureCases report={report} selected={openFailure} onSelect={setOpenFailure} />
          </div>
        ) : (
          <EmptyResults />
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
function DecisionSummary({
  brief,
  leaderboard,
}: {
  brief: ProofBrief;
  leaderboard: LeaderboardEntry[];
}) {
  const winner = leaderboard.find((e) => e.recommended) ?? leaderboard[0];
  if (!winner) return null;
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
        <p className="mt-2 text-sm text-(--color-ink-muted)">
          Passed {winner.pass_count}/{winner.total} examples ({Math.round(winner.pass_rate * 100)}
          %) · avg score {winner.avg_score.toFixed(2)} · {winner.avg_latency_ms}ms avg · $
          {winner.total_estimated_cost_usd.toFixed(2)} est.
        </p>
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

function EmptyResults() {
  return (
    <section aria-label="Results" className="rounded-xl border border-dashed border-(--color-panel-line) p-6">
      <h3 className="text-sm font-medium text-(--color-ink)">No proof run yet</h3>
      <p className="mt-1 max-w-prose text-sm text-(--color-ink-muted)">
        A Proof Run compares your candidates on the same frozen examples so you can decide what
        to trust. The sample dataset and both mock providers are pre-selected — press{" "}
        <span className="text-(--color-ink)">Run proof</span> to get a leaderboard, failure
        cases, and a shareable receipt without any API keys.
      </p>
    </section>
  );
}
