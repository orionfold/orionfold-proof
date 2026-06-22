// Shared inline "do this, then this" stepper primitives. A numbered accent badge + inline label +
// controls on one row, joined by hairline connectors — the badge and connector match the top
// StageStepper so every inline config flow in the cockpit (judge picker, run setup) reads as the
// same kind of calm stepper rather than a pile of unrelated controls.

// A numbered step — badge, label, and controls all inline on one row.
export function Step({ n, label, children }: { n: number; label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2">
      <span aria-hidden className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-(--color-accent) text-[10px] text-(--color-accent-ink)">
        {n}
      </span>
      <span className="text-sm text-(--color-ink-muted)">{label}</span>
      {children}
    </div>
  );
}

// Connector between steps — the same hairline the top StageStepper uses between Configure/Run/Decide.
// Hidden once the row wraps so it never points sideways into a stacked layout; the numbered badges
// still carry the ordering.
export function StepLine() {
  return <span aria-hidden className="hidden h-px w-5 shrink-0 bg-(--color-panel-line) sm:block" />;
}
