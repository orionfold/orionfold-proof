import { useState } from "react";

import type { ProofReport, ResultRow } from "../../lib/api";
import { StatusBadge } from "./badges";

const rowKey = (r: ResultRow) => `${r.candidate_id}-${r.example_index}`;

// Failure cases are where trust is won or lost. The user picks a candidate, then a case; the
// full input/expected/output opens in the inspector. Provider errors are surfaced, never
// swallowed.
export function FailureCases({
  report,
  selected,
  onSelect,
}: {
  report: ProofReport;
  selected: ResultRow | null;
  onSelect: (row: ResultRow) => void;
}) {
  const failures = report.results.filter((r) => !r.passed);
  const candidateIds = [...new Set(failures.map((f) => f.candidate_id))];
  const [active, setActive] = useState<string | null>(candidateIds[0] ?? null);

  const labelFor = (id: string) => report.run.candidates.find((c) => c.id === id)?.label ?? id;

  if (failures.length === 0) {
    return (
      <section aria-label="Failure cases" className="w-full">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-(--color-ink-muted)">
          Failure cases
        </h2>
        <p className="text-(--color-ink-muted)">
          No failures — every candidate passed every example.
        </p>
      </section>
    );
  }

  const shown = failures.filter((f) => f.candidate_id === active);

  return (
    <section aria-label="Failure cases" className="w-full">
      <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-(--color-ink-muted)">
        Failure cases ({failures.length})
      </h2>
      <div className="mb-4 flex flex-wrap gap-2">
        {candidateIds.map((id) => {
          const count = failures.filter((f) => f.candidate_id === id).length;
          const isActive = id === active;
          return (
            <button
              key={id}
              type="button"
              onClick={() => setActive(id)}
              aria-pressed={isActive}
              className={
                "rounded-full border px-3 py-1 text-sm transition-colors " +
                (isActive
                  ? "border-(--color-accent)/50 bg-(--color-accent)/10 text-(--color-ink)"
                  : "border-(--color-panel-line) text-(--color-ink-muted) hover:text-(--color-ink)")
              }
            >
              {labelFor(id)} · {count}
            </button>
          );
        })}
      </div>
      <ul className="flex flex-col gap-2">
        {shown.map((row) => (
          <FailureRow
            key={rowKey(row)}
            row={row}
            isSelected={selected != null && rowKey(selected) === rowKey(row)}
            onSelect={() => onSelect(row)}
          />
        ))}
      </ul>
    </section>
  );
}

function FailureRow({
  row,
  isSelected,
  onSelect,
}: {
  row: ResultRow;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        aria-pressed={isSelected}
        className={
          "flex w-full items-center gap-3 rounded-lg border px-4 py-3 text-left text-sm transition-colors " +
          (isSelected
            ? "border-(--color-accent)/50 bg-(--color-panel-card)"
            : "border-(--color-panel-line) bg-(--color-panel-card) hover:border-(--color-panel-line-strong)")
        }
      >
        <span className="shrink-0 text-(--color-ink-faint)">Example {row.example_index + 1}</span>
        <span className="min-w-0 flex-1 truncate text-(--color-ink-muted)">{row.input_text}</span>
        {row.error ? (
          <StatusBadge kind="error">error: {row.error}</StatusBadge>
        ) : (
          <StatusBadge kind="fail">Fail · score {(row.score ?? 0).toFixed(2)}</StatusBadge>
        )}
      </button>
    </li>
  );
}
