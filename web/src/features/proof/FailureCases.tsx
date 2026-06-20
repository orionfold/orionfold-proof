import { useState } from "react";

import type { ProofReport, ResultRow } from "../../lib/api";

// Failure cases are where trust is won or lost. The user picks a candidate and inspects the
// exact examples it got wrong — including provider errors, surfaced, never swallowed.
export function FailureCases({ report }: { report: ProofReport }) {
  const failures = report.results.filter((r) => !r.passed);
  const candidateIds = [...new Set(failures.map((f) => f.candidate_id))];
  const [selected, setSelected] = useState<string | null>(candidateIds[0] ?? null);

  const labelFor = (id: string) =>
    report.run.candidates.find((c) => c.id === id)?.label ?? id;

  if (failures.length === 0) {
    return (
      <section aria-label="Failure cases" className="w-full">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-[--color-ink-muted]">
          Failure cases
        </h2>
        <p className="text-[--color-ink-muted]">
          No failures — every candidate passed every example.
        </p>
      </section>
    );
  }

  const shown = failures.filter((f) => f.candidate_id === selected);

  return (
    <section aria-label="Failure cases" className="w-full">
      <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-[--color-ink-muted]">
        Failure cases ({failures.length})
      </h2>
      <div className="mb-4 flex flex-wrap gap-2">
        {candidateIds.map((id) => {
          const count = failures.filter((f) => f.candidate_id === id).length;
          const active = id === selected;
          return (
            <button
              key={id}
              type="button"
              onClick={() => setSelected(id)}
              aria-pressed={active}
              className={
                "rounded-full border px-3 py-1 text-sm transition-colors " +
                (active
                  ? "border-emerald-400 bg-emerald-500/15 text-[--color-ink]"
                  : "border-[--color-panel-line] text-[--color-ink-muted] hover:text-[--color-ink]")
              }
            >
              {labelFor(id)} · {count}
            </button>
          );
        })}
      </div>
      <ul className="flex flex-col gap-3">
        {shown.map((row) => (
          <FailureRow key={`${row.candidate_id}-${row.example_index}`} row={row} />
        ))}
      </ul>
    </section>
  );
}

function FailureRow({ row }: { row: ResultRow }) {
  return (
    <li className="rounded-xl border border-[--color-panel-line] bg-[--color-panel-card] p-4">
      <div className="mb-2 flex items-center gap-2 text-sm">
        <span className="text-[--color-ink-muted]">Example {row.example_index + 1}</span>
        {row.error ? (
          <span className="rounded-full bg-rose-500/15 px-2 py-0.5 text-xs text-rose-300">
            error: {row.error}
          </span>
        ) : (
          <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-xs text-amber-300">
            score {row.score.toFixed(2)}
          </span>
        )}
      </div>
      <dl className="grid grid-cols-[5rem_1fr] gap-x-3 gap-y-1 text-sm">
        <dt className="text-[--color-ink-muted]">Input</dt>
        <dd className="text-[--color-ink]">{row.input_text}</dd>
        <dt className="text-[--color-ink-muted]">Expected</dt>
        <dd className="text-[--color-ink]">{row.expected_text}</dd>
        <dt className="text-[--color-ink-muted]">Output</dt>
        <dd className="text-[--color-ink]">{row.output_text || "—"}</dd>
      </dl>
    </li>
  );
}
