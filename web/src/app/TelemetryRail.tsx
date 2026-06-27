import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  Cpu,
  CircuitBoard,
  MemoryStick,
  Layers,
  Server,
  Coins,
  Wallet,
  CircleCheck,
  ReceiptText,
  type LucideIcon,
} from "lucide-react";

import { getHostProfile, subscribeTelemetry, type TelemetrySample } from "../lib/api";

// The standing instrument cluster — a full-width, single-row horizontal rail present on EVERY
// screen (spec §4). It replaces the old 22rem right inspector. Slice 1 wires the host-at-rest
// cells (chip / cores / mem / runtime / GPU live %); the remaining standing signals (host-trend
// peak-bars, cost split, last-run/last-receipt digests) land as real readouts in Slice 2 — here
// they render honest "—" placeholders so the layout and SSE plumbing are proven now.
//
// `runActive` is the live-run signal (lifted to App): true DURING a run, when the finished report
// doesn't yet exist. While active we subscribe to the telemetry SSE so the live cells light up
// exactly while the hardware is under load; the stream self-closes at run end and we clear.
export function TelemetryRail({ runActive }: { runActive: boolean }) {
  const { data: profile } = useQuery({
    queryKey: ["telemetry-host"],
    queryFn: getHostProfile,
    staleTime: Infinity,
  });

  const [sample, setSample] = useState<TelemetrySample | null>(null);
  useEffect(() => {
    if (!runActive) {
      setSample(null);
      return;
    }
    const unsubscribe = subscribeTelemetry(setSample, () => setSample(null));
    return () => {
      unsubscribe();
      setSample(null);
    };
  }, [runActive]);

  const cpu = sample ? `${Math.round(sample.cpu_util)}%` : profile ? "at rest" : "—";
  const gpu = sample?.gpu_util != null ? `${Math.round(sample.gpu_util)}%` : "unavailable";
  const mem =
    sample?.mem_used_gb != null
      ? `${sample.mem_used_gb} GB`
      : profile?.memory_gb
        ? `${profile.memory_gb} GB`
        : "—";

  return (
    <div
      aria-label="Telemetry"
      // Sticky directly beneath the app bar; together they are the total chrome (≤ ~135px,
      // spec §3.1). Single dense row, horizontally scrollable on narrow widths rather than
      // wrapping to a second row. Cyan = controls only, so the rail carries none — instrument ink.
      className="sticky top-(--bar-h) z-20 flex h-(--rail-h) shrink-0 items-stretch gap-px overflow-x-auto border-b border-(--color-panel-line) bg-(--color-rail)"
    >
      <Cell label="Host" value={profile?.chip ?? profile?.arch ?? "detecting…"} Icon={CircuitBoard} strong />
      <Cell label="CPU" value={cpu} Icon={Cpu} live={sample != null} />
      <Cell label="GPU" value={gpu} Icon={CircuitBoard} live={sample != null} />
      <Cell label="Memory" value={mem} Icon={MemoryStick} live={sample?.mem_used_gb != null} />
      <Cell label="Cores" value={profile?.cpu_cores ? `${profile.cpu_cores}` : "—"} Icon={Layers} />
      <Cell label="Runtime" value={profile?.local_runtime ?? "cloud only"} Icon={Server} />
      {/* Standing signals filled in Slice 2 — honest placeholders, never a fake zero. */}
      <Cell label="Cost today" value="—" Icon={Coins} />
      <Cell label="Cost to date" value="—" Icon={Wallet} />
      <Cell label="Last result" value="—" Icon={CircleCheck} />
      <Cell label="Last receipt" value="—" Icon={ReceiptText} />
      <div className="ml-auto flex items-center gap-1.5 px-4 text-xs text-(--color-ink-faint)">
        <span aria-hidden className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-(--color-ok)" />
        Private · on this machine
      </div>
    </div>
  );
}

// A compact bezel cell: 0.58rem uppercase label over a mono tabular-nums readout (Arena's
// instrument vocabulary in Proof tokens). `live` tints the readout cyan-neutral while a run feeds
// it; at rest it's calm ink.
function Cell({
  label,
  value,
  Icon,
  strong,
  live,
}: {
  label: string;
  value: string;
  Icon?: LucideIcon;
  strong?: boolean;
  live?: boolean;
}) {
  return (
    <div className="flex min-w-[5.5rem] flex-col justify-center gap-0.5 border-r border-(--color-panel-line) px-4">
      <span className="flex items-center gap-1 text-[0.58rem] font-medium uppercase tracking-wider text-(--color-ink-faint)">
        {Icon && <Icon aria-hidden className="h-3 w-3 shrink-0" />}
        {label}
      </span>
      <span
        className={
          "font-mono text-sm tabular-nums " +
          (strong
            ? "font-semibold text-(--color-ink)"
            : live
              ? "text-(--color-ink)"
              : "text-(--color-ink-muted)")
        }
      >
        {value}
      </span>
    </div>
  );
}
