import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import {
  createRun,
  getCandidates,
  getDatasets,
  type ProofBrief,
  type ProofReport,
} from "../../lib/api";
import { FailureCases } from "./FailureCases";
import { Leaderboard } from "./Leaderboard";
import { ReceiptExport } from "./ReceiptExport";
import { RunSetup } from "./RunSetup";

const DEFAULT_BRIEF: ProofBrief = {
  task_name: "Investment memo summarization",
  decision_question: "Which model should I trust for client memo summaries?",
  success_criteria: "",
};

// Orchestrates the one core loop: setup → run → leaderboard → failure cases → receipt.
// Server state (datasets, candidates) comes through TanStack Query; the run is a mutation.
export function ProofCockpit() {
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: getDatasets });
  const candidates = useQuery({ queryKey: ["candidates"], queryFn: getCandidates });

  const [datasetId, setDatasetId] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [brief, setBrief] = useState<ProofBrief>(DEFAULT_BRIEF);
  const [report, setReport] = useState<ProofReport | null>(null);

  // Sensible defaults once the server data lands: first dataset, all candidates selected.
  const resolvedDatasetId = datasetId || datasets.data?.[0]?.id || "";
  const resolvedSelected = useMemo(() => {
    if (selected.length > 0) return selected;
    return candidates.data?.map((c) => c.id) ?? [];
  }, [selected, candidates.data]);

  const runMutation = useMutation({
    mutationFn: createRun,
    onSuccess: setReport,
  });

  const toggleCandidate = (id: string) => {
    const base = resolvedSelected;
    setSelected(base.includes(id) ? base.filter((c) => c !== id) : [...base, id]);
  };

  if (datasets.isLoading || candidates.isLoading) {
    return <p className="text-[--color-ink-muted]">Loading the local engine…</p>;
  }
  if (datasets.isError || candidates.isError || !datasets.data || !candidates.data) {
    return <p className="text-rose-300">Could not reach the local engine.</p>;
  }

  return (
    <div className="flex w-full max-w-3xl flex-col gap-8">
      <RunSetup
        datasets={datasets.data}
        candidates={candidates.data}
        datasetId={resolvedDatasetId}
        onDatasetChange={setDatasetId}
        selectedCandidates={resolvedSelected}
        onToggleCandidate={toggleCandidate}
        brief={brief}
        onBriefChange={setBrief}
        isRunning={runMutation.isPending}
        error={runMutation.isError ? (runMutation.error as Error).message : null}
        onRun={() =>
          runMutation.mutate({
            dataset_id: resolvedDatasetId,
            candidate_ids: resolvedSelected,
            brief,
          })
        }
      />

      {report && (
        <>
          <Leaderboard entries={report.leaderboard} />
          <FailureCases report={report} />
          <ReceiptExport report={report} />
        </>
      )}
    </div>
  );
}
