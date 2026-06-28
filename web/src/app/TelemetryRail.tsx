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
  getCostSummary,
  getGpuIdle,
  getHostProfile,
  getLatestRun,
  getSettings,
  subscribeTelemetry,
  type CostRollup,
  type ProofReport,
  type TelemetrySample,
} from "../lib/api";
import { type RunProgress } from "../features/proof/useRunProgress";
import { type ReceiptsMode } from "../features/proof/ReceiptsView";
import {
  emptyTrend,
  pushSample,
  sparklinePath,
  trendFromSeries,
  type Trend,
} from "../features/proof/sparkline";

// The three live host trends shown as sparklines. Bundled so they reset/accumulate together.
interface Trends {
  cpu: Trend;
  gpu: Trend;
  mem: Trend;
}
function emptyTrends(): Trends {
  return { cpu: emptyTrend(), gpu: emptyTrend(), mem: emptyTrend() };
}

// The standing instrument cluster — a full-width, single-row horizontal rail on every screen
// (spec §4). At rest it shows host identity calmly; during a run the live cells light up (CPU
// sparkline, run progress), driven by the telemetry SSE + the lifted run-progress snapshot. Cost
// cells read from the cost-summary rollup (today split eval+judge, cumulative to-date). Honest
// throughout: missing data reads "unavailable" / "at rest" / "—", never a fabricated zero — but a
// loaded $0.00 is shown as $0.00 (a real all-local spend), distinct from "—" while loading.
export function TelemetryRail({
  runActive,
  runProgress,
  lastReport,
  onOpenReceipts,
}: {
  runActive: boolean;
  runProgress: RunProgress | null;
  lastReport: ProofReport | null;
  // Drill into Receipts on a specific mode: result/receipt cells → "runs" (that archive); cost
  // cells → "track-record" (the standings, where the cost/pass-rate trend lives, spec §4).
  onOpenReceipts: (mode: ReceiptsMode) => void;
}) {
  const { data: profile } = useQuery({
    queryKey: ["telemetry-host"],
    queryFn: getHostProfile,
    staleTime: Infinity,
  });

  // Cumulative spend rollups (today / to-date) — a read-only aggregate over stored runs. Refetched
  // when a run finishes (the runActive→false transition below), since a new stored run is the only
  // thing that moves these numbers.
  const costToday = useQuery({
    queryKey: ["cost-summary", "today"],
    queryFn: () => getCostSummary("today"),
  });
  const costAll = useQuery({
    queryKey: ["cost-summary", "all"],
    queryFn: () => getCostSummary("all"),
  });

  // The latest STORED run — the rail's at-rest hydrate for Last result/receipt when nothing is open
  // in the cockpit this session. Like the cost rollups, a finished run is the only thing that moves
  // it, so it refetches on the runActive→false transition below.
  const latestRun = useQuery({ queryKey: ["latest-run"], queryFn: getLatestRun });

  // Settings — only the GPU opt-in matters here: it gates whether we poll the privileged at-rest
  // GPU read at all. (The server gates it too; this is the courtesy front so we never even ask.)
  const settings = useQuery({ queryKey: ["settings"], queryFn: getSettings, staleTime: Infinity });
  const gpuOptIn = settings.data?.powermetrics_gpu_optin === true;

  // At-rest GPU idle reading. Enabled ONLY when the operator opted in AND no run is active (the live
  // SSE owns the GPU cell during a run). Throttled to ~30s and paused while the tab is hidden, so the
  // privileged powermetrics shell-out stays calm. The server also refuses to shell out without the
  // opt-in, so this is throttle + courtesy, not the guarantee. `refetchOnWindowFocus` refreshes the
  // reading when the operator returns to the tab.
  const GPU_IDLE_POLL_MS = 30_000;
  const gpuIdle = useQuery({
    queryKey: ["gpu-idle"],
    queryFn: getGpuIdle,
    enabled: gpuOptIn && !runActive,
    refetchInterval: gpuOptIn && !runActive ? GPU_IDLE_POLL_MS : false,
    refetchIntervalInBackground: false, // don't poll a hidden tab — pauses the privileged read
    staleTime: GPU_IDLE_POLL_MS,
  });

  const [sample, setSample] = useState<TelemetrySample | null>(null);
  // Per-metric trends (CPU / GPU / memory), accumulated across a run's samples (peak-over-bucket →
  // SVG sparkline). Refs so the SSE callback always sees the latest without re-subscribing;
  // mirrored to state so the sparklines re-render each frame. The LAST completed run's trends are
  // KEPT after the run ends (rendered dimmed, an at-rest record) so the rail shows "this run vs
  // last run" (spec §4); they reset only when a NEW run starts. Bucket of 2 samples (~1s/bar at
  // the ~500ms rate) keeps the line lively but smooth.
  const trendsRef = useRef<Trends>(emptyTrends());
  const [trends, setTrends] = useState<Trends>(emptyTrends());

  const refetchCostToday = costToday.refetch;
  const refetchCostAll = costAll.refetch;
  const refetchLatestRun = latestRun.refetch;
  useEffect(() => {
    if (!runActive) {
      // Run ended (or never started): drop the live sample so readouts return to "at rest", but
      // LEAVE the trends frozen as the last-run record. The Sparkline renders them dimmed.
      setSample(null);
      // A finished run is now stored — refresh the cost rollups + latest-run so the rail reflects
      // the new spend and the freshly-stored receipt.
      void refetchCostToday();
      void refetchCostAll();
      void refetchLatestRun();
      return;
    }
    // A new run starts: clear the prior run's trends so the fresh line draws from empty.
    trendsRef.current = emptyTrends();
    setTrends(trendsRef.current);
    const onSample = (s: TelemetrySample) => {
      setSample(s);
      trendsRef.current = {
        cpu: pushSample(trendsRef.current.cpu, s.cpu_util, { bucket: 2 }),
        gpu: pushSample(trendsRef.current.gpu, s.gpu_util, { bucket: 2 }),
        mem: pushSample(trendsRef.current.mem, s.mem_used_gb, { bucket: 2 }),
      };
      setTrends(trendsRef.current);
    };
    const unsubscribe = subscribeTelemetry(onSample, () => setSample(null));
    return () => {
      unsubscribe();
      setSample(null);
    };
  }, [runActive, refetchCostToday, refetchCostAll, refetchLatestRun]);

  // Seed the dimmed "last run" sparkline from the latest STORED run's persisted trend series, so a
  // fresh page/server still shows a historical trace (not a blank line). Only at rest, and only
  // before this session has captured a live run (a live or just-finished run's in-session trends
  // take precedence — they're the freshest record). Keyed on the fetched telemetry so it re-seeds
  // when the latest run changes (e.g. after a run finishes and the refetch above resolves).
  const latestTelemetry = latestRun.data?.telemetry;
  useEffect(() => {
    if (runActive) return; // a live run owns the trends
    if (trendsRef.current.cpu.finalized.length > 0) return; // this session already has a record
    if (!latestTelemetry) return;
    const seeded: Trends = {
      cpu: trendFromSeries(latestTelemetry.cpu_series),
      gpu: trendFromSeries(latestTelemetry.gpu_series),
      mem: trendFromSeries(latestTelemetry.mem_series),
    };
    trendsRef.current = seeded;
    setTrends(seeded);
  }, [latestTelemetry, runActive]);

  const live = sample != null;
  const cpu = live ? `${Math.round(sample!.cpu_util)}%` : profile ? "at rest" : "—";
  // GPU readout precedence: a live run sample → the at-rest idle poll → a label. With the opt-in on
  // (so we're polling) an absent/null reading reads "at rest" like CPU; with the opt-in off the
  // privileged read is genuinely not available → "unavailable".
  const gpuIdleVal = gpuIdle.data?.gpu_util ?? null;
  const gpu =
    sample?.gpu_util != null
      ? `${Math.round(sample.gpu_util)}%`
      : gpuIdleVal != null
        ? `${Math.round(gpuIdleVal)}%`
        : gpuOptIn
          ? "at rest"
          : "unavailable";
  const mem =
    sample?.mem_used_gb != null
      ? `${sample.mem_used_gb} GB`
      : profile?.memory_gb
        ? `${profile.memory_gb} GB`
        : "—";

  // Last proof result. The in-memory report (the run currently/last open in the cockpit this
  // session) wins; at rest, with nothing open, we fall back to the latest STORED run so the cell
  // shows the real last receipt instead of "—". The recommended leaderboard entry is the headline;
  // its pooled pass count is the one-glance metric.
  const atRestReport = lastReport ?? latestRun.data ?? null;
  const winner = atRestReport?.leaderboard.find((e) => e.recommended) ?? atRestReport?.leaderboard[0];
  const lastResult = winner
    ? `${winner.pass_count}/${winner.total}`
    : runActive
      ? "running…"
      : "—";
  const lastReceipt = winner ? winner.label : "—";

  // Cost rollups → cell readouts. A loaded-but-zero rollup honestly reads $0.00 (a real,
  // all-local spend), distinct from "—" while the fetch is still in flight. Today's cell carries
  // the eval+judge split underneath the total.
  const todayValue = costToday.data ? formatUsd(costToday.data.total_cost_usd) : "—";
  const todaySub = costToday.data ? costSplitSub(costToday.data) : undefined;
  const toDateValue = costAll.data ? formatUsd(costAll.data.total_cost_usd) : "—";
  const toDateSub = costAll.data
    ? `${costAll.data.run_count} run${costAll.data.run_count === 1 ? "" : "s"}`
    : undefined;

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
      {/* Live host cells: readout + SVG sparkline of the run's trend. The line stays after the run
          (dimmed) as the last-run record; a new run draws a fresh bright line over it. CPU/GPU are
          percentages (max 100); memory auto-scales to its own range. */}
      <Cell label="CPU" value={cpu} Icon={Cpu} live={live}>
        <Sparkline trend={trends.cpu} max={100} active={live} />
      </Cell>
      <Cell label="GPU" value={gpu} Icon={CircuitBoard} live={sample?.gpu_util != null}>
        <Sparkline trend={trends.gpu} max={100} active={sample?.gpu_util != null} />
      </Cell>
      <Cell label="Memory" value={mem} Icon={MemoryStick} live={sample?.mem_used_gb != null}>
        <Sparkline trend={trends.mem} active={sample?.mem_used_gb != null} />
      </Cell>
      <Cell label="Runtime" value={profile?.local_runtime ?? "cloud only"} Icon={Server} />
      {/* Live run progress while streaming; otherwise the last proof result. */}
      {progressValue != null ? (
        <Cell label="Run" value={progressValue} sub={progressSub ?? undefined} Icon={Activity} live />
      ) : (
        <CellButton
          label="Last result"
          value={lastResult}
          Icon={CircleCheck}
          onClick={winner ? () => onOpenReceipts("runs") : undefined}
        />
      )}
      {/* Standing cost signals — read-only rollups over stored runs. The cells drill into Receipts
          (where the cost/pass-rate trend tiles live, spec §4). Today's cell splits eval+judge. */}
      <CellButton
        label="Cost today"
        value={todayValue}
        sub={todaySub}
        Icon={Coins}
        onClick={costToday.data ? () => onOpenReceipts("track-record") : undefined}
      />
      <CellButton
        label="Cost to date"
        value={toDateValue}
        sub={toDateSub}
        Icon={Wallet}
        onClick={costAll.data ? () => onOpenReceipts("track-record") : undefined}
      />
      <CellButton
        label="Last receipt"
        value={lastReceipt}
        Icon={ReceiptText}
        onClick={winner ? () => onOpenReceipts("runs") : undefined}
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
function Sparkline({ trend, max, active }: { trend: Trend; max?: number; active: boolean }) {
  const w = 56;
  const h = 16;
  const values = trend.forming != null ? [...trend.finalized, trend.forming] : trend.finalized;
  const geo = sparklinePath(values, { w, h, max, forming: trend.forming != null });
  if (!geo.line) return null;
  // Cyan-neutral instrument line over a light fill that anchors it to the baseline; the forming dot
  // uses --color-ok (a live, healthy pulse). The area fill makes a sparse 2-point trace read as a
  // small mound rising from the x-axis instead of a line floating at an unclear elevation.
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden className="mt-0.5">
      {geo.area && (
        <path d={geo.area} fill="var(--color-accent)" stroke="none" opacity={active ? 0.16 : 0.08} />
      )}
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
    // Top-aligned (justify-start + a fixed top inset) so every cell's LABEL pins to the same y
    // across the row whether or not a sparkline follows — centering drifted the taller (sparkline)
    // cells' labels upward. The sparkline simply hangs below the readout.
    <div className="flex min-w-[5.5rem] flex-col justify-start gap-0.5 border-r border-(--color-panel-line) px-4 pt-2.5">
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
  sub,
  Icon,
  onClick,
}: {
  label: string;
  value: string;
  sub?: string;
  Icon?: LucideIcon;
  onClick?: () => void;
}) {
  if (!onClick) return <Cell label={label} value={value} sub={sub} Icon={Icon} />;
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex min-w-[5.5rem] flex-col justify-start gap-0.5 border-r border-(--color-panel-line) px-4 pt-2.5 text-left transition-colors hover:bg-(--color-panel-card)"
      title={`Open Receipts — ${label.toLowerCase()}`}
    >
      <span className="flex items-center gap-1 text-[0.58rem] font-medium uppercase tracking-wider text-(--color-ink-faint)">
        {Icon && <Icon aria-hidden className="h-3 w-3 shrink-0" />}
        {label}
      </span>
      <span className="flex items-baseline gap-1.5">
        <span className="truncate font-mono text-sm tabular-nums text-(--color-ink)">{value}</span>
        {sub && <span className="font-mono text-[0.65rem] tabular-nums text-(--color-ink-faint)">{sub}</span>}
      </span>
    </button>
  );
}

// USD formatting for the rail's cost cells. Small spends ($0–$10) get cents (a $0.02 judge cost
// must not round to $0); larger spends drop to whole dollars to stay compact in the bezel.
function formatUsd(usd: number): string {
  if (usd === 0) return "$0.00";
  if (usd < 10) return `$${usd.toFixed(2)}`;
  return `$${Math.round(usd)}`;
}

// The eval+judge split shown beneath today's total — e.g. "0.34 + 0.02". Omitted when there's no
// judge spend (deterministic scoring), keeping the common case calm.
function costSplitSub(roll: CostRollup): string | undefined {
  if (roll.judge_cost_usd === 0) return undefined;
  return `${roll.eval_cost_usd.toFixed(2)} + ${roll.judge_cost_usd.toFixed(2)}`;
}
