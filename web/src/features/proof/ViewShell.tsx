// Shared frame for the rail's secondary destinations (Datasets, Candidates, Receipts): the
// same padded main column and quiet header as the Proof Run workspace, minus the inspector.
// Keeps every view reading as one instrument panel rather than four separate pages.
export function ViewShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <main className="flex flex-col gap-8 px-6 py-8 lg:px-10">
      <header className="flex flex-col gap-1">
        <h2 className="text-xl font-semibold tracking-tight text-(--color-ink)">{title}</h2>
        <p className="max-w-prose text-sm text-(--color-ink-muted)">{subtitle}</p>
      </header>
      {children}
    </main>
  );
}

// Calm inline notice for a view's loading / error / empty states — never a spinner-y dashboard.
export function ViewNotice({ tone, children }: { tone?: "error"; children: React.ReactNode }) {
  return (
    <p
      className={
        "rounded-xl border border-dashed border-(--color-panel-line) p-6 text-sm " +
        (tone === "error" ? "text-rose-300" : "text-(--color-ink-muted)")
      }
    >
      {children}
    </p>
  );
}
