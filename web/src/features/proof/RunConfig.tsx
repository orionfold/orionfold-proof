import type { ProofReport } from "../../lib/api";
import { ProviderTag } from "./badges";

// The run's config and repro metadata: what was compared, how it was scored, the config hash that
// makes it reproducible, and the hardware it ran on. Extracted from the old right Inspector so the
// L3 receipt-detail view can carry the same provenance the side panel used to.
export function RunConfig({ report }: { report: ProofReport }) {
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
        <HardwareField report={report} />
      </dl>
    </section>
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

// Compact hardware provenance, inline with the run config — so the machine a proof ran on is
// visible with the rest of the config. Renders nothing for older runs that carry no host profile
// (honest absence), and omits the peaks line for a run that wasn't sampled.
function HardwareField({ report }: { report: ProofReport }) {
  const { host, telemetry } = report;
  if (!host) return null;
  // One identity line (chip · runtime) + a quiet peaks line when the run was sampled. Mirrors the
  // receipt's "reproduced on hardware like X" without restating the whole spec sheet.
  const identity = [host.chip ?? host.arch, host.local_runtime].filter(Boolean).join(" · ");
  const peaks: string[] = [];
  if (telemetry?.sampled) {
    if (telemetry.cpu_util_max != null) peaks.push(`CPU peak ${Math.round(telemetry.cpu_util_max)}%`);
    if (telemetry.process_rss_gb_max != null) peaks.push(`${telemetry.process_rss_gb_max} GB RSS`);
    if (telemetry.gpu_util_max != null) peaks.push(`GPU peak ${Math.round(telemetry.gpu_util_max)}%`);
  }
  return (
    <Field label="Hardware">
      <span className="text-(--color-ink)">{identity}</span>
      {peaks.length > 0 && (
        <span className="mt-0.5 block font-mono text-xs text-(--color-ink-muted)">
          {peaks.join(" · ")}
        </span>
      )}
    </Field>
  );
}
