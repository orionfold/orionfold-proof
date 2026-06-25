// Re-runs the provider liveness probe on demand. Shared by the Proof Run candidates section and
// the Candidates view so both offer the same affordance. While a probe is in flight it shows a
// spinning indicator and disables itself; otherwise it's a quiet ghost button.
import { LoaderCircle, RefreshCw } from "lucide-react";

export function RecheckHealthButton({
  isChecking,
  onRecheck,
}: {
  isChecking?: boolean;
  onRecheck?: () => void;
}) {
  if (!onRecheck) return null;
  return (
    <button
      type="button"
      onClick={onRecheck}
      disabled={isChecking}
      className="inline-flex items-center gap-1.5 rounded-lg border border-(--color-panel-line) px-2.5 py-1 text-xs text-(--color-ink-muted) transition-colors hover:bg-(--color-panel-line)/40 disabled:opacity-60"
    >
      {isChecking ? (
        <LoaderCircle aria-hidden className="h-3 w-3 animate-spin" />
      ) : (
        <RefreshCw aria-hidden className="h-3 w-3" />
      )}
      {isChecking ? "Checking providers…" : "Recheck providers"}
    </button>
  );
}
