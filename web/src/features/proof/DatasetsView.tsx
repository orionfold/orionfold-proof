import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getDatasets, updateDataset, type Dataset } from "../../lib/api";
import { ViewNotice, ViewShell } from "./ViewShell";
import { DatasetImportPanel } from "./DatasetImportPanel";
import { TagChips } from "./TagChips";
import { checkHintLabel } from "./tags";

// A read-only reference: the frozen example sets a proof run scores candidates against. Seeing
// the exact inputs/expected answers is part of trusting the receipt — nothing is hidden.
export function DatasetsView() {
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: getDatasets });
  const [importing, setImporting] = useState(false);

  return (
    <ViewShell
      title="Datasets"
      subtitle="The frozen example sets your candidates are proved against. Every candidate runs on the same inputs, so the comparison is fair and repeatable."
      action={
        <button
          type="button"
          onClick={() => setImporting((v) => !v)}
          className="rounded-lg border border-(--color-panel-line) px-3 py-1.5 text-sm text-(--color-ink) hover:bg-(--color-panel-line)/40"
        >
          {importing ? "Close import" : "Import dataset"}
        </button>
      }
    >
      {importing && <DatasetImportPanel onClose={() => setImporting(false)} />}
      {/* existing loading / error / empty / list block unchanged */}
      {datasets.isLoading ? (
        <ViewNotice>Loading datasets…</ViewNotice>
      ) : datasets.isError || !datasets.data ? (
        <ViewNotice tone="error">
          Could not reach the local engine. Start it with <code>orionfold up</code>, then reload.
        </ViewNotice>
      ) : datasets.data.length === 0 ? (
        <ViewNotice>No datasets yet. Import a JSONL, CSV, or Markdown set to get started.</ViewNotice>
      ) : (
        <div className="grid gap-4">
          {datasets.data.map((d) => (
            <DatasetCard key={d.id} d={d} />
          ))}
        </div>
      )}
    </ViewShell>
  );
}

function formatDate(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString();
}

function sourceLabel(source: string): string {
  if (!source) return ""; // legacy/seeded rows have no recorded source — omit it
  return source.startsWith("file:") ? source.slice(5) : source;
}

function DatasetCard({ d }: { d: Dataset }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState((d.tags ?? []).join(", "));
  const save = useMutation({
    mutationFn: () =>
      updateDataset(d.id, {
        tags: draft
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["datasets"] });
      setEditing(false);
    },
  });

  const created = formatDate(d.created_at ?? "");
  const metaBits = [
    `${d.examples.length} example${d.examples.length === 1 ? "" : "s"}`,
    created && `created ${created}`,
    sourceLabel(d.source ?? ""),
  ].filter(Boolean);

  return (
    <section className="rounded-xl border border-(--color-panel-line) bg-(--color-panel-card) p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="flex items-center gap-2 text-base font-medium text-(--color-ink)">
          {d.name}
          {d.is_sample ? (
            <span className="rounded border border-(--color-panel-line) bg-(--color-panel-card) px-2 py-0.5 text-[11px] font-medium text-(--color-ink-muted)">
              Sample
            </span>
          ) : null}
        </h3>
        <span className="text-xs text-(--color-ink-faint)">{metaBits.join(" · ")}</span>
      </div>

      {d.description && <p className="mt-1 text-sm text-(--color-ink-muted)">{d.description}</p>}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <TagChips tags={d.tags ?? []} />
        {d.check_hint ? (
          <span className="of-tag of-tag--t5">{checkHintLabel(d.check_hint)}</span>
        ) : null}
        <button
          type="button"
          onClick={() => setEditing((v) => !v)}
          className="text-xs text-(--color-ink-faint) hover:text-(--color-accent)"
        >
          {editing ? "Cancel" : "Edit tags"}
        </button>
      </div>

      {editing && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="comma-separated, e.g. Legal, Finance"
            aria-label="Edit tags"
            className="grow rounded-lg border border-(--color-panel-line) bg-(--color-panel-card) p-1.5 text-xs text-(--color-ink)"
          />
          <button
            type="button"
            onClick={() => save.mutate()}
            disabled={save.isPending}
            className="rounded-lg bg-(--color-accent-strong) px-3 py-1.5 text-xs font-medium text-(--color-accent-ink) disabled:opacity-50"
          >
            {save.isPending ? "Saving…" : "Save tags"}
          </button>
        </div>
      )}

      <details className="mt-3">
        <summary className="cursor-pointer text-sm text-(--color-ink-muted) hover:text-(--color-ink)">
          Examples
        </summary>
        <ol className="mt-3 grid gap-3">
          {d.examples.map((ex, i) => (
            <li key={i} className="grid gap-1 border-t border-(--color-panel-line) pt-3 text-sm">
              <ExampleField label="Input" value={ex.input_text} />
              <ExampleField label="Expected" value={ex.expected_text} />
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}

function ExampleField({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-0.5">
      <span className="text-xs text-(--color-ink-faint)">{label}</span>
      <span className="whitespace-pre-wrap text-(--color-ink)">{value || "—"}</span>
    </div>
  );
}
