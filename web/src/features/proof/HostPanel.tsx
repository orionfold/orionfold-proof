import type { HostProfile, TelemetrySample } from "../../lib/api";

// Always-on base tenant of the inspector rail. Static host profile when idle; the live gauges
// (telemetry !== null) fill in during a run. Calm instrument — quiet rows, no spinners, no alert
// theater (UX north star). Every field is best-effort: a missing one reads honestly ("unavailable"
// / "cloud only"), never a fabricated value.
export function HostPanel({
  profile,
  telemetry,
}: {
  profile: HostProfile | undefined;
  telemetry: TelemetrySample | null;
}) {
  return (
    <section
      aria-label="Host"
      className="flex flex-col gap-3 border-t border-(--color-panel-line) px-5 py-4"
    >
      <h3 className="text-xs font-medium uppercase tracking-wider text-(--color-ink-faint)">Host</h3>
      {!profile ? (
        <p className="text-sm text-(--color-ink-muted)">Detecting host…</p>
      ) : (
        <dl className="flex flex-col gap-1 text-sm text-(--color-ink)">
          <Row label={profile.chip ?? profile.arch} value="" strong />
          <Row label="CPU" value={profile.cpu_cores ? `${profile.cpu_cores} cores` : "—"} />
          <Row label="Memory" value={profile.memory_gb ? `${profile.memory_gb} GB unified` : "—"} />
          <Row label="OS" value={profile.os_label ?? "—"} />
          <Row label="Runtime" value={profile.local_runtime ?? "cloud only"} />
          <Row label="GPU" value={profile.gpu_label ?? "unavailable"} />
        </dl>
      )}
      {telemetry && <LiveGauges sample={telemetry} />}
    </section>
  );
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className={strong ? "font-medium text-(--color-ink)" : "text-(--color-ink-muted)"}>
        {label}
      </dt>
      {value && <dd className="font-mono text-xs text-(--color-ink)">{value}</dd>}
    </div>
  );
}

// Live gauges, fleshed out in Task 9 — kept minimal here so the rail compiles and the type slot
// is real. A run that is sampling shows CPU now; mem / RSS / GPU bars land with the SSE wiring.
function LiveGauges({ sample }: { sample: TelemetrySample }) {
  return (
    <div className="flex flex-col gap-1 border-t border-(--color-panel-line) pt-2 text-xs text-(--color-ink-muted)">
      <span>CPU {Math.round(sample.cpu_util)}%</span>
    </div>
  );
}
