import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Trophy } from "lucide-react";

import {
  getDatasets,
  getTrackRecord,
  type TrackRecordEntry,
  type TrackRecordGroup,
} from "../../lib/api";
import { ProviderTag } from "./badges";
import { RUBRIC_KIND_LABEL } from "./scoring";
import { SelectField } from "./SelectField";
import { ViewNotice, ViewShell } from "./ViewShell";

// The cross-run scoreboard: which candidate has earned trust over repeated comparable runs.
// "Comparable" = same dataset, same rubric kind (each becomes a section). Pass-rate is pooled
// (Σpasses / Σexamples), so a 100-example run legitimately outweighs a 5-example one — this is a
// credibility-weighted standing, not a naive average of run rates.
export function TrackRecordView() {
  const [datasetId, setDatasetId] = useState<string>("");
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: getDatasets });
  const trackRecord = useQuery({
    queryKey: ["track-record", datasetId || null],
    queryFn: () => getTrackRecord(datasetId || undefined),
  });

  const filter =
    datasets.data && datasets.data.length > 0 ? (
      <label className="flex items-center gap-2 text-sm text-(--color-ink-muted)">
        <span className="text-(--color-ink-faint)">Dataset</span>
        <SelectField
          className="w-56"
          value={datasetId}
          onChange={(e) => setDatasetId(e.target.value)}
          aria-label="Filter track record by dataset"
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
      title="Track Record"
      subtitle="Which candidate has earned trust across repeated runs. Each section is a comparable slice — the same dataset scored the same way — and pass-rate is pooled over every example, so a larger run carries more weight. Quick checks don't count."
      action={filter}
    >
      {trackRecord.isLoading ? (
        <ViewNotice>Loading track record…</ViewNotice>
      ) : trackRecord.isError || !trackRecord.data ? (
        <ViewNotice tone="error">
          Could not reach the local engine. Start it with <code>orionfold up</code>, then reload.
        </ViewNotice>
      ) : trackRecord.data.length === 0 ? (
        <ViewNotice>
          {datasetId
            ? "No scored runs for this dataset yet. Run a proof on it, then come back."
            : "No track record yet. Run the same proof a few times — once a dataset has been scored more than once, its standings build up here."}
        </ViewNotice>
      ) : (
        <div className="grid gap-6">
          {trackRecord.data.map((group) => (
            <TrackRecordGroupCard key={`${group.dataset_id}:${group.rubric_kind}`} group={group} />
          ))}
        </div>
      )}
    </ViewShell>
  );
}

function TrackRecordGroupCard({ group }: { group: TrackRecordGroup }) {
  return (
    <section className="rounded-xl border border-(--color-panel-line) bg-(--color-panel-card)">
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b border-(--color-panel-line) px-5 py-3">
        <h3 className="font-medium text-(--color-ink)">{group.dataset_name}</h3>
        <span className="text-xs text-(--color-ink-faint)">
          {RUBRIC_KIND_LABEL[group.rubric_kind]} · {group.runs}{" "}
          {group.runs === 1 ? "run" : "runs"}
        </span>
      </header>
      <ul className="grid gap-px bg-(--color-panel-line)">
        {group.entries.map((entry) => (
          <li key={entry.candidate_id} className="bg-(--color-panel-card) px-5 py-3">
            <TrackRecordRow entry={entry} />
          </li>
        ))}
      </ul>
    </section>
  );
}

function TrackRecordRow({ entry }: { entry: TrackRecordEntry }) {
  const pct = Math.round(entry.pass_rate * 100);
  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <span className="flex items-center gap-2">
          <span className="font-medium text-(--color-ink)">{entry.label}</span>
          <ProviderTag candidate={entry} />
        </span>
        <span className="flex items-center gap-3 text-sm text-(--color-ink-muted)">
          {entry.times_recommended > 0 && (
            <span className="flex items-center gap-1 text-(--color-ink-faint)">
              <Trophy aria-hidden className="h-3.5 w-3.5" />
              won {entry.times_recommended}×
            </span>
          )}
          <span className="tabular-nums text-(--color-ink-faint)">
            {entry.runs} {entry.runs === 1 ? "run" : "runs"}
          </span>
          <span className="tabular-nums font-medium text-(--color-ink)">{pct}%</span>
        </span>
      </div>
      {/* Pooled pass-rate bar — a verified-quality measure, so it uses the status `ok` token, never
          the interactive accent (the DS accent/status split). */}
      <div className="h-1.5 overflow-hidden rounded-full bg-(--color-panel-line)">
        <div
          className="h-full rounded-full bg-(--color-ok)"
          style={{ width: `${pct}%` }}
          aria-hidden
        />
      </div>
      <span className="text-xs text-(--color-ink-faint)">
        {entry.total_passes}/{entry.total_examples} examples passed
      </span>
    </div>
  );
}
