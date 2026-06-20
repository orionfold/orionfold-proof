import { CircleCheck, LoaderCircle } from "lucide-react";

import type { RunStartEvent } from "../../lib/api";
import { ProviderTag } from "./badges";

// Live progress for a streaming run. The server sends only a cumulative `done` count; because
// cells run candidate-major, everything shown here — the current cell and each candidate's
// completion — is derived from `done` + the run plan. Calm and truthful, for long local runs.
export function RunProgress({ start, done }: { start: RunStartEvent; done: number }) {
  const { total, n_examples: n, candidates } = start;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  const finishing = done >= total;

  // The cell currently running is the next one not yet counted (0-based index === done).
  const current = finishing ? null : candidates[Math.floor(done / n)];
  const exampleNum = (done % n) + 1;

  return (
    <section aria-label="Proof run progress" aria-busy="true" className="grid gap-4 motion-safe:animate-reveal">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-sm text-(--color-ink)">
          <LoaderCircle aria-hidden className="h-4 w-4 animate-spin text-(--color-accent)" />
          Running proof
        </span>
        <span className="tabular-nums text-sm text-(--color-ink-muted)">
          {done}/{total}
        </span>
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
        {current ? (
          <>
            Now running <span className="text-(--color-ink)">{current.label}</span>
            <ProviderTag candidate={current} /> · example {exampleNum} of {n}
          </>
        ) : (
          "Scoring outputs and assembling the receipt…"
        )}
      </p>

      <ul className="grid gap-1.5">
        {candidates.map((c, k) => {
          const completed = Math.min(Math.max(done - k * n, 0), n);
          const complete = completed >= n;
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
                  style={{ width: `${(completed / n) * 100}%` }}
                />
              </div>
              <span className="tabular-nums text-(--color-ink-faint)">
                {completed}/{n}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
