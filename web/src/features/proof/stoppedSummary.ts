import type { RunStartEvent } from "../../lib/api";

/** A discarded (stopped) run, summarized for the calm "Run stopped" panel. Nothing is persisted —
 * these numbers are computed entirely from the progress frames already received. */
export interface StoppedSummary {
  /** Cells that finished before the stop (received progress frames). */
  completedCells: number;
  /** Total cells the run would have produced (0 if the start frame never arrived). */
  totalCells: number;
  /** Real spend incurred before the stop, Σ per-cell cost (candidate + judge). 0 for free runs. */
  incurredCost: number;
}

/** Roll received cells up into a StoppedSummary. Pure + total: a missing start frame or a missing
 * per-cell cost both degrade to 0 (never NaN) so the view can honestly omit the dollar line. */
export function buildStoppedSummary(
  start: RunStartEvent | null,
  cells: { cost?: number }[],
): StoppedSummary {
  return {
    completedCells: cells.length,
    totalCells: start?.total ?? 0,
    incurredCost: cells.reduce((sum, c) => sum + (c.cost ?? 0), 0),
  };
}

/** The error message to show in the run-setup form, or null to show none. A deliberate stop is NOT a
 * setup error — the calm Run-stopped panel is its canonical surface — so suppress both the
 * already-stopped case and a raw AbortError (the browser's "BodyStreamBuffer was aborted" text). */
export function setupRunError(
  isError: boolean,
  error: unknown,
  stopped: boolean,
): string | null {
  if (!isError || stopped) return null;
  if (error instanceof DOMException && error.name === "AbortError") return null;
  return error instanceof Error ? error.message : null;
}
