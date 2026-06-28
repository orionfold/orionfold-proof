import type { StoppedSummary } from "./stoppedSummary";

/** Calm panel shown after the operator stops a run. A stopped run is discarded — never saved, never
 * leaderboarded — so this presents no receipt: only how far it got and any real spend it incurred.
 * Cost is neither a verdict nor a PASS, so it stays in neutral ink (never accent/ok). */
export function RunStopped({
  summary,
  onStartOver,
}: {
  summary: StoppedSummary;
  onStartOver: () => void;
}) {
  const { completedCells, totalCells, incurredCost } = summary;
  // Sub-cent runs read better at 4dp; anything larger at 2dp. Never a verdict — just an honest number.
  const costLabel = incurredCost.toFixed(incurredCost > 0 && incurredCost < 0.01 ? 4 : 2);

  return (
    <section
      aria-label="Run stopped"
      className="grid gap-3 rounded-xl border border-(--color-panel-line) bg-(--color-panel-card) p-6 motion-safe:animate-reveal"
    >
      <h3 className="text-base font-medium text-(--color-ink)">Run stopped</h3>
      <p className="text-sm text-(--color-ink-muted)">Partial results not saved.</p>

      <p className="tabular-nums text-sm text-(--color-ink)">
        {completedCells} of {totalCells} checks completed
      </p>
      {incurredCost > 0 && (
        <p className="tabular-nums text-sm text-(--color-ink-muted)">
          This stopped run already spent ~${costLabel}
        </p>
      )}

      <div>
        <button
          type="button"
          onClick={onStartOver}
          className="mt-1 rounded-md border border-(--color-panel-line) px-3 py-1.5 text-sm text-(--color-ink-muted) transition-colors hover:border-(--color-ink-muted) hover:text-(--color-ink)"
        >
          Start over
        </button>
      </div>
    </section>
  );
}
