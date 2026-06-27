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

// Live gauges during a run: quiet token-driven bars (--color-ok healthy, --color-warn under
// pressure). No spinners, no red alert theater — a calm instrument (UX north star).
function LiveGauges({ sample }: { sample: TelemetrySample }) {
  return (
    <div className="flex flex-col gap-2 border-t border-(--color-panel-line) pt-3">
      <Gauge label="CPU" pct={sample.cpu_util} value={`${Math.round(sample.cpu_util)}%`} />
      {sample.mem_used_gb != null && (
        <Row label="Memory (live)" value={`${sample.mem_used_gb} GB`} />
      )}
      {sample.process_rss_gb != null && (
        <Row label="Runtime RSS" value={`${sample.process_rss_gb} GB`} />
      )}
      <Row label="GPU" value={sample.gpu_util != null ? `${Math.round(sample.gpu_util)}%` : "unavailable"} />
    </div>
  );
}

// A thin horizontal bar (0–100%). Healthy fill uses --color-ok; >85% switches to --color-warn to
// signal pressure — never a hard red alarm.
function Gauge({ label, pct, value }: { label: string; pct: number; value: string }) {
  const clamped = Math.max(0, Math.min(100, pct));
  const color = clamped > 85 ? "--color-warn" : "--color-ok";
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="text-(--color-ink-muted)">{label}</span>
        <span className="font-mono text-xs text-(--color-ink)">{value}</span>
      </div>
      <div className="h-1 w-full overflow-hidden rounded-full bg-(--color-panel-line)">
        <div className="h-full rounded-full" style={{ width: `${clamped}%`, background: `var(${color})` }} />
      </div>
    </div>
  );
}
