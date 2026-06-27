import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import {
  Cpu,
  CircuitBoard,
  MemoryStick,
  Server,
  Coins,
  Wallet,
  CircleCheck,
  ReceiptText,
  Activity,
  type LucideIcon,
} from "lucide-react";

import {
  getHostProfile,
  subscribeTelemetry,
  type ProofReport,
  type TelemetrySample,
} from "../lib/api";
import { type RunProgress } from "../features/proof/useRunProgress";
import { emptyTrend, pushSample, sparklinePath, type Trend } from "../features/proof/sparkline";

// The standing instrument cluster — a full-width, single-row horizontal rail on every screen
// (spec §4). At rest it shows host identity calmly; during a run the live cells light up (CPU
// sparkline, run progress), driven by the telemetry SSE + the lifted run-progress snapshot. Cost
// cells stay "—" until Slice 3 (the cost rollup endpoint). Honest throughout: missing data reads
// "unavailable" / "at rest" / "—", never a fabricated zero.
export function TelemetryRail({
  runActive,
  runProgress,
  lastReport,
  onOpenReceipts,
}: {
  runActive: boolean;
  runProgress: RunProgress | null;
  lastReport: ProofReport | null;
  onOpenReceipts: () => void;
}) {
  const { data: profile } = useQuery({
    queryKey: ["telemetry-host"],
    queryFn: getHostProfile,
    staleTime: Infinity,
  });

  const [sample, setSample] = useState<TelemetrySample | null>(null);
  // The live CPU trend, accumulated across the run's samples (peak-over-bucket → SVG sparkline).
  // A ref so the SSE callback always sees the latest without re-subscribing; mirrored to state so
  // the sparkline re-renders each frame.
  const cpuTrendRef = useRef<Trend>(emptyTrend());
  const [cpuTrend, setCpuTrend] = useState<Trend>(emptyTrend());

  useEffect(() => {
    if (!runActive) {
      setSample(null);
      cpuTrendRef.current = emptyTrend();
      setCpuTrend(emptyTrend());
      return;
    }
    const onSample = (s: TelemetrySample) => {
      setSample(s);
      // Bucket of 2 samples (~1s/bar at the ~500ms sample rate) keeps the trend lively but smooth.
      cpuTrendRef.current = pushSample(cpuTrendRef.current, s.cpu_util, { bucket: 2 });
      setCpuTrend(cpuTrendRef.current);
    };
    const unsubscribe = subscribeTelemetry(onSample, () => setSample(null));
    return () => {
      unsubscribe();
      setSample(null);
    };
  }, [runActive]);

  const live = sample != null;
  const cpu = live ? `${Math.round(sample!.cpu_util)}%` : profile ? "at rest" : "—";
  const gpu = sample?.gpu_util != null ? `${Math.round(sample.gpu_util)}%` : "unavailable";
  const mem =
    sample?.mem_used_gb != null
      ? `${sample.mem_used_gb} GB`
      : profile?.memory_gb
        ? `${profile.memory_gb} GB`
        : "—";

  // Last proof result, derived from the in-memory report (the run currently/last shown in the
  // cockpit). The recommended leaderboard entry is the headline; its pooled pass count is the
  // one-glance metric. A dedicated "latest stored receipt" fetch lands with the Receipts bento.
  const winner = lastReport?.leaderboard.find((e) => e.recommended) ?? lastReport?.leaderboard[0];
  const lastResult = winner
    ? `${winner.pass_count}/${winner.total}`
    : runActive
      ? "running…"
      : "—";
  const lastReceipt = winner ? winner.label : "—";

  // Live run progress overrides the last-result cell while a run streams.
  const progressValue = runProgress
    ? runProgress.passRateSoFar != null
      ? `${Math.round(runProgress.passRateSoFar * 100)}%`
      : "scoring…"
    : null;
  const progressSub = runProgress
    ? `${runProgress.candidatesDone}/${runProgress.candidatesTotal} cand`
    : null;

  return (
    <div
      aria-label="Telemetry"
      className="sticky top-(--bar-h) z-20 flex h-(--rail-h) shrink-0 items-stretch gap-px overflow-x-auto border-b border-(--color-panel-line) bg-(--color-rail)"
    >
      <Cell label="Host" value={profile?.chip ?? profile?.arch ?? "detecting…"} Icon={CircuitBoard} strong />
      {/* CPU is the showcase live cell: readout + SVG sparkline of the run's CPU trend. */}
      <Cell label="CPU" value={cpu} Icon={Cpu} live={live}>
        <Sparkline trend={cpuTrend} max={100} active={live} />
      </Cell>
      <Cell label="GPU" value={gpu} Icon={CircuitBoard} live={sample?.gpu_util != null} />
      <Cell label="Memory" value={mem} Icon={MemoryStick} live={sample?.mem_used_gb != null} />
      <Cell label="Runtime" value={profile?.local_runtime ?? "cloud only"} Icon={Server} />
      {/* Live run progress while streaming; otherwise the last proof result. */}
      {progressValue != null ? (
        <Cell label="Run" value={progressValue} sub={progressSub ?? undefined} Icon={Activity} live />
      ) : (
        <CellButton
          label="Last result"
          value={lastResult}
          Icon={CircleCheck}
          onClick={winner ? onOpenReceipts : undefined}
        />
      )}
      {/* Standing cost signals — filled in Slice 3 (cost rollup endpoint). */}
      <Cell label="Cost today" value="—" Icon={Coins} />
      <Cell label="Cost to date" value="—" Icon={Wallet} />
      <CellButton
        label="Last receipt"
        value={lastReceipt}
        Icon={ReceiptText}
        onClick={winner ? onOpenReceipts : undefined}
      />
      <div className="ml-auto flex items-center gap-1.5 px-4 text-xs text-(--color-ink-faint)">
        <span aria-hidden className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-(--color-ok)" />
        Private · on this machine
      </div>
    </div>
  );
}

// A compact SVG sparkline of the live trend. Token-native (stroke=var(--color-*)); the forming
// edge renders as a dimmed dot so "live" reads without animation (reduced-motion-safe). Renders
// nothing until there's data, so an at-rest cell stays calm.
function Sparkline({ trend, max, active }: { trend: Trend; max: number; active: boolean }) {
  const w = 56;
  const h = 16;
  const values = trend.forming != null ? [...trend.finalized, trend.forming] : trend.finalized;
  const geo = sparklinePath(values, { w, h, max, forming: trend.forming != null });
  if (!geo.line) return null;
  // Cyan-neutral instrument line; the forming dot uses --color-ok (a live, healthy pulse).
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden className="mt-0.5">
      <path d={geo.line} fill="none" stroke="var(--color-accent)" strokeWidth="1.25" strokeLinejoin="round" strokeLinecap="round" opacity={active ? 0.9 : 0.4} />
      {geo.formingPoint && (
        <circle cx={geo.formingPoint.x} cy={geo.formingPoint.y} r="1.6" fill="var(--color-ok)" />
      )}
    </svg>
  );
}

// A compact bezel cell: icon + 0.58rem uppercase label, mono tabular-nums readout, optional sub
// line and an optional inline child (sparkline). Arena's instrument vocabulary in Proof tokens.
function Cell({
  label,
  value,
  sub,
  Icon,
  strong,
  live,
  children,
}: {
  label: string;
  value: string;
  sub?: string;
  Icon?: LucideIcon;
  strong?: boolean;
  live?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex min-w-[5.5rem] flex-col justify-center gap-0.5 border-r border-(--color-panel-line) px-4">
      <span className="flex items-center gap-1 text-[0.58rem] font-medium uppercase tracking-wider text-(--color-ink-faint)">
        {Icon && <Icon aria-hidden className="h-3 w-3 shrink-0" />}
        {label}
      </span>
      <span className="flex items-baseline gap-1.5">
        <span
          className={
            "font-mono text-sm tabular-nums " +
            (strong ? "font-semibold text-(--color-ink)" : live ? "text-(--color-ink)" : "text-(--color-ink-muted)")
          }
        >
          {value}
        </span>
        {sub && <span className="font-mono text-[0.65rem] tabular-nums text-(--color-ink-faint)">{sub}</span>}
      </span>
      {children}
    </div>
  );
}

// A drill-down cell: same bezel, but the whole cell is a button (a navigation verb, spec §4 — the
// signal is the headline of a deeper screen). Quiet hover; disabled (plain cell) when no target.
function CellButton({
  label,
  value,
  Icon,
  onClick,
}: {
  label: string;
  value: string;
  Icon?: LucideIcon;
  onClick?: () => void;
}) {
  if (!onClick) return <Cell label={label} value={value} Icon={Icon} />;
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex min-w-[5.5rem] flex-col justify-center gap-0.5 border-r border-(--color-panel-line) px-4 text-left transition-colors hover:bg-(--color-panel-card)"
      title={`Open Receipts — ${label.toLowerCase()}`}
    >
      <span className="flex items-center gap-1 text-[0.58rem] font-medium uppercase tracking-wider text-(--color-ink-faint)">
        {Icon && <Icon aria-hidden className="h-3 w-3 shrink-0" />}
        {label}
      </span>
      <span className="truncate font-mono text-sm tabular-nums text-(--color-ink)">{value}</span>
    </button>
  );
}
