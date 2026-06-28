import { CircleCheck, LoaderCircle } from "lucide-react";

import type { RunStartEvent } from "../../lib/api";
import { ProviderTag } from "./badges";

// Live progress for a streaming run. Candidates run concurrently (cloud parallel, local
// serialized), so cells complete out of order — the server tags each progress event with its
// candidate, and this component keys everything on a per-candidate completed-count map rather than
// a positional cumulative count. Bars advance together, which is the truthful picture for the
// operator. Calm and honest, for long local runs.
export function RunProgress({
  start,
  completed,
  onStop,
}: {
  start: RunStartEvent;
  completed: Record<string, number>;
  onStop?: () => void;
}) {
  const { total, n_examples: n, candidates } = start;
  const done = candidates.reduce((sum, c) => sum + Math.min(completed[c.id] ?? 0, n), 0);
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  const finishing = done >= total;

  // Candidates still in flight (some examples left). Shown so the operator sees the parallel work.
  const running = candidates.filter((c) => (completed[c.id] ?? 0) < n);

  return (
    <section aria-label="Proof run progress" aria-busy="true" className="grid gap-4 motion-safe:animate-reveal">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-sm text-(--color-ink)">
          <LoaderCircle aria-hidden className="h-4 w-4 animate-spin text-(--color-accent)" />
          Running proof
        </span>
        <div className="flex items-center gap-3">
          <span className="tabular-nums text-sm text-(--color-ink-muted)">
            {done}/{total}
          </span>
          {onStop && !finishing && (
            <button
              type="button"
              onClick={onStop}
              className="rounded-md border border-(--color-panel-line) px-2.5 py-1 text-xs text-(--color-ink-muted) transition-colors hover:border-(--color-ink-muted) hover:text-(--color-ink)"
            >
              Stop run
            </button>
          )}
        </div>
      </div>

      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-(--color-panel-card)"
        role="progressbar"
        aria-valuenow={done}
        aria-valuemin={0}
        aria-valuemax={total}
      >
        <div
          className="h-full rounded-full bg-(--color-accent) transition-[width] duration-300 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>

      <p className="flex flex-wrap items-center gap-1.5 text-sm text-(--color-ink-muted)">
        {finishing ? (
          "Scoring outputs and assembling the receipt…"
        ) : running.length === 1 ? (
          <>
            Now running <span className="text-(--color-ink)">{running[0].label}</span>
            <ProviderTag candidate={running[0]} />
          </>
        ) : (
          <>
            Running <span className="text-(--color-ink)">{running.length}</span> candidates in
            parallel
          </>
        )}
      </p>

      <ul className="grid gap-1.5">
        {candidates.map((c) => {
          const cellsDone = Math.min(completed[c.id] ?? 0, n);
          const complete = cellsDone >= n;
          return (
            <li key={c.id} className="flex items-center gap-2 text-xs">
              {complete ? (
                <CircleCheck aria-hidden className="h-3.5 w-3.5 shrink-0 text-(--color-accent)" />
              ) : (
                <span aria-hidden className="h-3.5 w-3.5 shrink-0" />
              )}
              <span className="w-32 shrink-0 truncate text-(--color-ink-muted)">{c.label}</span>
              <div className="h-1 flex-1 overflow-hidden rounded-full bg-(--color-panel-card)">
                <div
                  className="h-full rounded-full bg-(--color-accent)/60 transition-[width] duration-300 ease-out"
                  style={{ width: `${(cellsDone / n) * 100}%` }}
                />
              </div>
              <span className="tabular-nums text-(--color-ink-faint)">
                {cellsDone}/{n}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
