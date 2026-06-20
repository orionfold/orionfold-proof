import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getDatasets } from "../../lib/api";
import { ViewNotice, ViewShell } from "./ViewShell";
import { DatasetImportPanel } from "./DatasetImportPanel";

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
            <section
              key={d.id}
              className="rounded-xl border border-(--color-panel-line) bg-(--color-panel-card) p-5"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-base font-medium text-(--color-ink)">{d.name}</h3>
                <span className="text-xs text-(--color-ink-faint)">
                  {d.examples.length} example{d.examples.length === 1 ? "" : "s"}
                </span>
              </div>
              {d.description && (
                <p className="mt-1 text-sm text-(--color-ink-muted)">{d.description}</p>
              )}
              <details className="mt-3">
                <summary className="cursor-pointer text-sm text-(--color-ink-muted) hover:text-(--color-ink)">
                  Examples
                </summary>
                <ol className="mt-3 grid gap-3">
                  {d.examples.map((ex, i) => (
                    <li
                      key={i}
                      className="grid gap-1 border-t border-(--color-panel-line) pt-3 text-sm"
                    >
                      <ExampleField label="Input" value={ex.input_text} />
                      <ExampleField label="Expected" value={ex.expected_text} />
                    </li>
                  ))}
                </ol>
              </details>
            </section>
          ))}
        </div>
      )}
    </ViewShell>
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
