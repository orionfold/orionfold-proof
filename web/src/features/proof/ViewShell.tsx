// Shared frame for the rail's secondary destinations (Datasets, Candidates, Receipts): the
// same padded main column and quiet header as the Proof Run workspace, minus the inspector.
// Keeps every view reading as one instrument panel rather than four separate pages.
export function ViewShell({
  title,
  subtitle,
  action,
  children,
}: {
  title: string;
  subtitle: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  // After the Arena reshape the canvas is full-width (no left/right rails), so reading screens
  // would sprawl edge-to-edge. Cap the inner column to a calm wide reading measure (max-w-[96rem],
  // spec §3.1) and left-anchor it, so each screen still reads as one instrument panel — WS-F F5.
  return (
    <main className="flex flex-col px-6 py-8 lg:px-10">
      <div className="flex w-full max-w-[96rem] flex-col gap-8">
        <header className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-1">
            <h2 className="text-xl font-semibold tracking-tight text-(--color-ink)">{title}</h2>
            <p className="max-w-prose text-sm text-(--color-ink-muted)">{subtitle}</p>
          </div>
          {action}
        </header>
        {children}
      </div>
    </main>
  );
}

// Calm inline notice for a view's loading / error / empty states — never a spinner-y dashboard.
export function ViewNotice({ tone, children }: { tone?: "error"; children: React.ReactNode }) {
  return (
    <p
      className={
        "rounded-xl border border-dashed border-(--color-panel-line) p-6 text-sm " +
        (tone === "error" ? "text-(--color-danger)" : "text-(--color-ink-muted)")
      }
    >
      {children}
    </p>
  );
}
