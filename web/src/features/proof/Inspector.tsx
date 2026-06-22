import type { ProofReport, ResultRow } from "../../lib/api";
import { ProviderTag, StatusBadge } from "./badges";
import { ReceiptExport } from "./ReceiptExport";

// The right inspector: secondary context for the run in the main workspace — its config and
// repro metadata, the takeaway receipt, and the full detail of whichever failure case is
// selected. Quietly weighted; the main workspace always wins the eye.
export function Inspector({
  report,
  selected,
}: {
  report: ProofReport | null;
  selected: ResultRow | null;
}) {
  return (
    <aside
      aria-label="Inspector"
      className="flex flex-col gap-6 border-t border-(--color-panel-line) bg-(--color-inspector) px-5 py-6 lg:h-full lg:border-l lg:border-t-0"
    >
      <h2 className="text-xs font-medium uppercase tracking-wider text-(--color-ink-faint)">
        Inspector
      </h2>

      {report ? (
        <>
          <RunConfig report={report} />
          <ReceiptExport report={report} />
          <SelectedFailure selected={selected} />
        </>
      ) : (
        <p className="text-sm text-(--color-ink-muted)">
          Run a proof to populate its config, receipt, and failure-case detail here.
        </p>
      )}
    </aside>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-0.5">
      <dt className="text-xs text-(--color-ink-faint)">{label}</dt>
      <dd className="text-sm text-(--color-ink)">{children}</dd>
    </div>
  );
}

function RunConfig({ report }: { report: ProofReport }) {
  const { run } = report;
  return (
    <section className="grid gap-3">
      <h3 className="text-sm font-medium text-(--color-ink)">Run config</h3>
      <dl className="grid gap-3">
        <Field label="Dataset">{run.dataset_name}</Field>
        <Field label="Rubric">
          {run.rubric.kind} · threshold {run.rubric.threshold}
        </Field>
        <Field label="Candidates">
          <div className="flex flex-wrap gap-1.5">
            {run.candidates.map((c) => (
              <span key={c.id} className="flex items-center gap-1.5">
                <ProviderTag candidate={c} />
                <span className="text-(--color-ink-muted)">{c.label}</span>
              </span>
            ))}
          </div>
        </Field>
        <Field label="Config hash">
          <code className="break-all text-(--color-ink-muted)">{run.config_hash}</code>
        </Field>
        <Field label="Created">
          <span className="text-(--color-ink-muted)">{run.created_at}</span>
        </Field>
      </dl>
    </section>
  );
}

function SelectedFailure({ selected }: { selected: ResultRow | null }) {
  return (
    <section className="grid gap-3">
      <h3 className="text-sm font-medium text-(--color-ink)">Failure case</h3>
      {selected ? (
        <dl className="grid gap-2 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-(--color-ink-faint)">Example {selected.example_index + 1}</span>
            {selected.error ? (
              <StatusBadge kind="error">error</StatusBadge>
            ) : (
              <StatusBadge kind="fail">score {selected.score.toFixed(2)}</StatusBadge>
            )}
          </div>
          <Detail label="Input" value={selected.input_text} />
          <Detail label="Expected" value={selected.expected_text} />
          <Detail label="Output" value={selected.output_text || "—"} />
          {selected.error && <Detail label="Error" value={selected.error} tone="error" />}
        </dl>
      ) : (
        <p className="text-sm text-(--color-ink-muted)">
          Select a failure case in the workspace to inspect its input, expected, and output.
        </p>
      )}
    </section>
  );
}

function Detail({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "error";
}) {
  return (
    <div className="grid gap-0.5">
      <span className="text-xs text-(--color-ink-faint)">{label}</span>
      <span className={tone === "error" ? "text-(--color-danger)" : "text-(--color-ink)"}>{value}</span>
    </div>
  );
}
