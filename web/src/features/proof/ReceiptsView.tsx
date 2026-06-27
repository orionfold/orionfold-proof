import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getDatasets, getRuns, type ProofReport } from "../../lib/api";
import { ReceiptsBento } from "./ReceiptsBento";
import { RunsTable } from "./RunsTable";
import { SelectField } from "./SelectField";
import { TrackRecordCards } from "./TrackRecordCards";
import { ViewNotice, ViewShell } from "./ViewShell";

// The two view modes Receipts now folds together (Slice 4): the per-run archive (Runs) and the
// cross-run scoreboard (Track Record, formerly its own tab). A shared bento masthead sits above
// both; the segmented toggle swaps the body. The rail can deep-link into either mode.
export type ReceiptsMode = "runs" | "track-record";

const MODES: { id: ReceiptsMode; label: string }[] = [
  { id: "runs", label: "Runs" },
  { id: "track-record", label: "Track Record" },
];

// Receipts: every proof you've run, two ways to read them. Runs = the per-receipt archive (compact
// sortable table). Track Record = the pooled cross-run standings. The bento masthead summarizes
// both (latest proof, cost today/to-date, library counts, the pass-rate-vs-cost trend).
export function ReceiptsView({
  initialMode = "runs",
  onOpenReceipt,
}: {
  initialMode?: ReceiptsMode;
  onOpenReceipt: (report: ProofReport) => void;
}) {
  const [mode, setMode] = useState<ReceiptsMode>(initialMode);
  // A dataset filter shared by both modes — narrows the Runs table and the Track Record cards.
  const [datasetId, setDatasetId] = useState<string>("");

  const runs = useQuery({ queryKey: ["runs"], queryFn: getRuns });
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: getDatasets });

  // The bento + table emit a run id; resolve it back to the full report the detail view needs. The
  // runs query is already loaded for the table, so this is a local lookup (no extra fetch).
  const openRun = (runId: string) => {
    const report = runs.data?.find((r) => r.run.id === runId);
    if (report) onOpenReceipt(report);
  };

  const filteredRuns =
    datasetId && runs.data ? runs.data.filter((r) => r.run.dataset_id === datasetId) : runs.data;

  const filter =
    datasets.data && datasets.data.length > 0 ? (
      <label className="flex items-center gap-2 text-sm text-(--color-ink-muted)">
        <span className="text-(--color-ink-faint)">Dataset</span>
        <SelectField
          className="w-56"
          value={datasetId}
          onChange={(e) => setDatasetId(e.target.value)}
          aria-label="Filter receipts by dataset"
        >
          <option value="">All datasets</option>
          {datasets.data.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </SelectField>
      </label>
    ) : undefined;

  return (
    <ViewShell
      title="Receipts"
      subtitle="Every proof you've run. Runs is the per-receipt archive — open one to view its receipt or download it to share. Track Record pools the standings across comparable runs."
      action={filter}
    >
      <ReceiptsBento onOpenRun={openRun} />

      {/* Segmented mode toggle — a control, so the active segment takes the cyan accent (the one
          interactive color), inactive segments stay quiet ink. */}
      <div
        role="tablist"
        aria-label="Receipts view mode"
        className="inline-flex w-fit items-center gap-1 rounded-lg border border-(--color-panel-line) bg-(--color-panel-card) p-1"
      >
        {MODES.map((m) => {
          const active = m.id === mode;
          return (
            <button
              key={m.id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setMode(m.id)}
              className={
                "h-8 rounded-md px-4 text-sm font-medium transition-colors " +
                (active
                  ? "bg-(--color-accent) text-(--color-accent-ink)"
                  : "text-(--color-ink-muted) hover:bg-(--color-rail) hover:text-(--color-ink)")
              }
            >
              {m.label}
            </button>
          );
        })}
      </div>

      {mode === "runs" ? (
        runs.isLoading ? (
          <ViewNotice>Loading receipts…</ViewNotice>
        ) : runs.isError || !runs.data ? (
          <ViewNotice tone="error">
            Could not reach the local engine. Start it with <code>orionfold up</code>, then reload.
          </ViewNotice>
        ) : !filteredRuns || filteredRuns.length === 0 ? (
          <ViewNotice>
            {datasetId
              ? "No proof runs for this dataset yet."
              : "No proof runs yet. Head to Prove and press Run proof — your first receipt will appear here."}
          </ViewNotice>
        ) : (
          <RunsTable reports={filteredRuns} onOpenRun={openRun} />
        )
      ) : (
        <TrackRecordCards datasetId={datasetId || undefined} />
      )}
    </ViewShell>
  );
}
