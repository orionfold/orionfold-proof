import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookText, Play } from "lucide-react";

import { getDatasets, updateDataset, type Dataset } from "../../lib/api";
import { ViewNotice, ViewShell } from "./ViewShell";
import { DatasetImportPanel } from "./DatasetImportPanel";
import { DatasetCoverage } from "./DatasetCoverage";
import { EvalTypeBadge } from "./EvalTypeBadge";
import { ExampleCard } from "./ExampleCard";
import { TagChips } from "./TagChips";
import { resolveDatasetKind } from "./scoring";

// A read-only reference: the frozen example sets a proof run scores candidates against. Seeing
// the exact inputs/expected answers is part of trusting the receipt — nothing is hidden. This is
// the product's golden surface: each example renders in the shape of its own contract, and a
// coverage strip up top shows the shape of the whole library at a glance.
// `focusId` deep-links from the Proof Run "View details" link (open + scroll + expand); `onRunDataset`
// is the reverse — "Run proof →" jumps to the Proof Run workspace with this dataset selected.
export function DatasetsView({
  focusId,
  onRunDataset,
  onOpenCorpus,
}: {
  focusId?: string | null;
  onRunDataset?: (id: string) => void;
  onOpenCorpus?: (id: string) => void;
} = {}) {
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
          <DatasetCoverage datasets={datasets.data} />
          {datasets.data.map((d) => (
            <DatasetCard
              key={d.id}
              d={d}
              focused={d.id === focusId}
              onRunDataset={onRunDataset}
              onOpenCorpus={onOpenCorpus}
            />
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

function DatasetCard({
  d,
  focused = false,
  onRunDataset,
  onOpenCorpus,
}: {
  d: Dataset;
  focused?: boolean;
  onRunDataset?: (id: string) => void;
  onOpenCorpus?: (id: string) => void;
}) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState((d.tags ?? []).join(", "));
  const kind = resolveDatasetKind(d);
  // When deep-linked from "View details", scroll this card into view and open its examples.
  const cardRef = useRef<HTMLElement>(null);
  useEffect(() => {
    if (focused) cardRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [focused]);
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
    <section
      ref={cardRef}
      className={
        "rounded-xl border bg-(--color-panel-card) p-5 " +
        (focused
          ? "border-(--color-accent) ring-1 ring-(--color-accent)/40"
          : "border-(--color-panel-line)")
      }
    >
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

      <div className="mt-3 flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <EvalTypeBadge dataset={d} />
          <TagChips tags={d.tags ?? []} />
          {d.corpus_id ? (
            onOpenCorpus ? (
              <button
                type="button"
                onClick={() => onOpenCorpus(d.corpus_id!)}
                className="of-tag of-tag--t7 inline-flex items-center gap-1 hover:brightness-110"
                title="Browse the governed corpus — citations are checked against this source set."
              >
                <BookText aria-hidden className="h-3 w-3 shrink-0" />
                corpus
              </button>
            ) : (
              <span
                className="of-tag of-tag--t7 inline-flex items-center gap-1"
                title="Bound to a governed corpus — citations are checked against a known source set."
              >
                <BookText aria-hidden className="h-3 w-3 shrink-0" />
                corpus
              </span>
            )
          ) : null}
          {d.system_prompt?.trim() ? (
            <span
              className="of-tag of-tag--t3"
              title="Ships a governance system prompt (e.g. a citation/refusal contract), auto-applied when you run it."
            >
              governance contract
            </span>
          ) : null}
          <button
            type="button"
            onClick={() => setEditing((v) => !v)}
            className="text-xs text-(--color-ink-faint) hover:text-(--color-accent)"
          >
            {editing ? "Cancel" : "Edit tags"}
          </button>
        </div>
        {onRunDataset ? (
          <button
            type="button"
            onClick={() => onRunDataset(d.id)}
            aria-label={`Run a proof on ${d.name}`}
            className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-(--color-accent) hover:underline"
          >
            <Play aria-hidden className="h-3 w-3 shrink-0" />
            Run proof →
          </button>
        ) : null}
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

      <details className="mt-3" open={focused}>
        <summary className="cursor-pointer text-sm text-(--color-ink-muted) hover:text-(--color-ink)">
          Examples
        </summary>
        <ol className="mt-3 grid gap-3">
          {d.examples.map((ex, i) => (
            <li key={i} className="border-t border-(--color-panel-line) pt-3 text-sm">
              <ExampleCard kind={kind} example={ex} />
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}
