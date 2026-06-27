import { useQuery } from "@tanstack/react-query";
import { Trophy } from "lucide-react";

import { getTrackRecord, type TrackRecordEntry, type TrackRecordGroup } from "../../lib/api";
import { ProviderTag } from "./badges";
import { RUBRIC_KIND_LABEL } from "./scoring";
import { ViewNotice } from "./ViewShell";

// The Receipts Track Record mode (Slice 4): dense 2-up dataset cards — the cross-run scoreboard
// folded into Receipts (the standalone tab is gone). Each card is one comparable slice (same
// dataset, same rubric kind); pass-rate is pooled (Σpasses / Σexamples) so a larger run carries
// more weight. Quick checks don't count (excluded server-side). This reuses the same data + pooled
// semantics as the old TrackRecordView, recomposed denser to sit under the bento.
export function TrackRecordCards({ datasetId }: { datasetId?: string }) {
  const trackRecord = useQuery({
    queryKey: ["track-record", datasetId || null],
    queryFn: () => getTrackRecord(datasetId || undefined),
  });

  if (trackRecord.isLoading) return <ViewNotice>Loading track record…</ViewNotice>;
  if (trackRecord.isError || !trackRecord.data) {
    return (
      <ViewNotice tone="error">
        Could not reach the local engine. Start it with <code>orionfold up</code>, then reload.
      </ViewNotice>
    );
  }
  if (trackRecord.data.length === 0) {
    return (
      <ViewNotice>
        {datasetId
          ? "No scored runs for this dataset yet. Run a proof on it, then come back."
          : "No track record yet. Run the same proof a few times — once a dataset has been scored more than once, its standings build up here."}
      </ViewNotice>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {trackRecord.data.map((group) => (
        <GroupCard key={`${group.dataset_id}:${group.rubric_kind}`} group={group} />
      ))}
    </div>
  );
}

function GroupCard({ group }: { group: TrackRecordGroup }) {
  return (
    <section className="rounded-xl border border-(--color-panel-line) bg-(--color-panel-card)">
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b border-(--color-panel-line) px-4 py-2.5">
        <h3 className="font-medium text-(--color-ink)">{group.dataset_name}</h3>
        <span className="text-xs text-(--color-ink-faint)">
          {RUBRIC_KIND_LABEL[group.rubric_kind]} · {group.runs} {group.runs === 1 ? "run" : "runs"}
        </span>
      </header>
      <ul className="grid gap-px bg-(--color-panel-line)">
        {group.entries.map((entry) => (
          <li key={entry.candidate_id} className="bg-(--color-panel-card) px-4 py-2.5">
            <EntryRow entry={entry} />
          </li>
        ))}
      </ul>
    </section>
  );
}

function EntryRow({ entry }: { entry: TrackRecordEntry }) {
  const pct = Math.round(entry.pass_rate * 100);
  return (
    <div className="grid gap-1.5">
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
          {entry.avg_cost_usd > 0 && (
            <span className="font-mono tabular-nums text-(--color-ink-faint)">
              ${entry.avg_cost_usd < 10 ? entry.avg_cost_usd.toFixed(2) : Math.round(entry.avg_cost_usd)}/run
            </span>
          )}
          <span className="font-mono tabular-nums font-medium text-(--color-ink)">{pct}%</span>
        </span>
      </div>
      {/* Pooled pass-rate bar — a verified-quality measure, so it uses the status `ok` token, never
          the interactive accent (the DS accent/status split). */}
      <div className="h-1.5 overflow-hidden rounded-full bg-(--color-panel-line)">
        <div className="h-full rounded-full bg-(--color-ok)" style={{ width: `${pct}%` }} aria-hidden />
      </div>
      <span className="text-xs text-(--color-ink-faint)">
        {entry.total_passes}/{entry.total_examples} examples passed
      </span>
    </div>
  );
}
