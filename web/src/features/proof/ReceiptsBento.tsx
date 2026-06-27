import { useQuery } from "@tanstack/react-query";
import { Coins, Database, ReceiptText, Wallet } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  getCostSummary,
  getDatasets,
  getRuns,
  type CostRollup,
} from "../../lib/api";
import { ProviderTag } from "./badges";
import {
  costSplitLine,
  formatUsd,
  latestProof,
  trendChartData,
  type TrendChartPoint,
} from "./bentoMath";

// The Receipts masthead (Slice 4): a dense above-the-fold bento shared by both view modes. Four
// metric tiles (Latest proof · Cost today split · Cost to date · Runs·Datasets) plus a wide
// dual-axis trend tile (pass-rate vs cost-per-run over time). Everything is a presentation-only
// projection of getRuns + the two cost rollups + getDatasets — no new source of truth.
//
// DS: status lives in the `ok` token (pass-rate trend line, verdict tone); `--color-accent` (cyan)
// stays the interactive accent and is NOT used for data ink here, only the cost line keeps a quiet
// neutral so the two trend lines read as quality (ok) vs spend (faint).
export function ReceiptsBento({ onOpenRun }: { onOpenRun?: (runId: string) => void }) {
  const runs = useQuery({ queryKey: ["runs"], queryFn: getRuns });
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: getDatasets });
  const costToday = useQuery({ queryKey: ["cost-summary", "today"], queryFn: () => getCostSummary("today") });
  const costAll = useQuery({ queryKey: ["cost-summary", "all"], queryFn: () => getCostSummary("all") });

  const latest = runs.data ? latestProof(runs.data) : null;
  const trend = costAll.data ? trendChartData(costAll.data.trend) : [];

  return (
    <section aria-label="Receipts summary" className="grid gap-3">
      {/* Four metric tiles + a wide trend tile. On a wide canvas the trend spans two columns so the
          four metric tiles sit left, the chart right — above-fold density without crowding. */}
      <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-4">
        <LatestProofTile latest={latest} loading={runs.isLoading} onOpenRun={onOpenRun} />
        <CostTile
          label="Cost today"
          Icon={Coins}
          rollup={costToday.data}
          loading={costToday.isLoading}
          split
        />
        <CostTile label="Cost to date" Icon={Wallet} rollup={costAll.data} loading={costAll.isLoading} />
        <CountTile
          runs={runs.data?.length ?? null}
          datasets={datasets.data?.length ?? null}
        />
      </div>
      <TrendTile data={trend} loading={costAll.isLoading} />
    </section>
  );
}

// A shared tile shell — quiet panel, an icon+label header, then the tile's body.
function Tile({
  label,
  Icon,
  children,
}: {
  label: string;
  Icon: typeof Coins;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-(--color-panel-line) bg-(--color-panel-card) px-4 py-3">
      <span className="flex items-center gap-1.5 text-[0.62rem] font-medium uppercase tracking-wider text-(--color-ink-faint)">
        <Icon aria-hidden className="h-3.5 w-3.5 shrink-0" />
        {label}
      </span>
      {children}
    </div>
  );
}

function LatestProofTile({
  latest,
  loading,
  onOpenRun,
}: {
  latest: ReturnType<typeof latestProof>;
  loading: boolean;
  onOpenRun?: (runId: string) => void;
}) {
  const body = (() => {
    if (loading) return <span className="text-sm text-(--color-ink-faint)">Loading…</span>;
    if (!latest) return <span className="text-sm text-(--color-ink-faint)">No proofs yet</span>;
    const { row } = latest;
    return (
      <>
        <span className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <span className="text-(--color-ink-faint)">{row.verb}</span>
          <span className="font-medium text-(--color-ink)">{row.winnerLabel ?? "—"}</span>
          {row.winnerProviderId && row.winnerPrivacy && (
            <ProviderTag candidate={{ provider_id: row.winnerProviderId, privacy: row.winnerPrivacy }} />
          )}
        </span>
        {row.passText && (
          <span className="font-mono text-sm tabular-nums text-(--color-ink-muted)">
            {Math.round((row.passRate ?? 0) * 100)}% ({row.passText})
          </span>
        )}
      </>
    );
  })();

  return (
    <Tile label="Latest proof" Icon={ReceiptText}>
      {/* The tile drills into the latest run's detail when there is one — the rail's "Last receipt"
          equivalent at the masthead. */}
      {latest && onOpenRun ? (
        <button
          type="button"
          onClick={() => onOpenRun(latest.row.runId)}
          className="flex flex-col items-start gap-1 text-left transition-colors hover:opacity-80"
          title="Open this receipt"
        >
          {body}
        </button>
      ) : (
        <div className="flex flex-col gap-1">{body}</div>
      )}
    </Tile>
  );
}

function CostTile({
  label,
  Icon,
  rollup,
  loading,
  split,
}: {
  label: string;
  Icon: typeof Coins;
  rollup: CostRollup | undefined;
  loading: boolean;
  split?: boolean;
}) {
  const value = rollup ? formatUsd(rollup.total_cost_usd) : loading ? "…" : "—";
  // Today's tile carries the eval+judge split (omitted when no judge ran). To-date carries its run
  // count instead.
  const sub = rollup
    ? split
      ? costSplitLine(rollup) ?? `${rollup.run_count} run${rollup.run_count === 1 ? "" : "s"} today`
      : `${rollup.run_count} run${rollup.run_count === 1 ? "" : "s"}`
    : undefined;
  return (
    <Tile label={label} Icon={Icon}>
      <span className="font-mono text-2xl font-semibold tabular-nums text-(--color-ink)">{value}</span>
      {sub && <span className="font-mono text-xs tabular-nums text-(--color-ink-faint)">{sub}</span>}
    </Tile>
  );
}

function CountTile({ runs, datasets }: { runs: number | null; datasets: number | null }) {
  return (
    <Tile label="Library" Icon={Database}>
      <div className="flex items-baseline gap-4">
        <span className="flex items-baseline gap-1.5">
          <span className="font-mono text-2xl font-semibold tabular-nums text-(--color-ink)">
            {runs ?? "—"}
          </span>
          <span className="text-xs text-(--color-ink-faint)">runs</span>
        </span>
        <span className="flex items-baseline gap-1.5">
          <span className="font-mono text-2xl font-semibold tabular-nums text-(--color-ink)">
            {datasets ?? "—"}
          </span>
          <span className="text-xs text-(--color-ink-faint)">datasets</span>
        </span>
      </div>
    </Tile>
  );
}

// The wide dual-axis trend tile: pass-rate (left, quality, --color-ok) and cost-per-run (right,
// spend, a quiet neutral). Animation on data update is fine — Recharts handles the transition. The
// chart reads left→right chronologically (the rollup trend is oldest-first).
function TrendTile({ data, loading }: { data: TrendChartPoint[]; loading: boolean }) {
  return (
    <Tile label="Pass-rate vs cost over time" Icon={Coins}>
      {loading ? (
        <span className="text-sm text-(--color-ink-faint)">Loading trend…</span>
      ) : data.length < 2 ? (
        <span className="text-sm text-(--color-ink-faint)">
          Run a few proofs to see the trend — one point isn't a line yet.
        </span>
      ) : (
        <div className="h-40 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: -8 }}>
              <CartesianGrid stroke="var(--color-panel-line)" strokeDasharray="2 4" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fill: "var(--color-ink-faint)", fontSize: 11 }}
                stroke="var(--color-panel-line)"
                tickLine={false}
              />
              <YAxis
                yAxisId="quality"
                domain={[0, 100]}
                tick={{ fill: "var(--color-ink-faint)", fontSize: 11 }}
                stroke="var(--color-panel-line)"
                tickLine={false}
                width={36}
                tickFormatter={(v: number) => `${v}%`}
              />
              <YAxis
                yAxisId="cost"
                orientation="right"
                tick={{ fill: "var(--color-ink-faint)", fontSize: 11 }}
                stroke="var(--color-panel-line)"
                tickLine={false}
                width={44}
                tickFormatter={(v: number) => formatUsd(v)}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--color-panel-card)",
                  border: "1px solid var(--color-panel-line)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelStyle={{ color: "var(--color-ink-muted)" }}
                formatter={(value, name) => {
                  const n = typeof value === "number" ? value : Number(value);
                  return name === "Pass rate" ? [`${n}%`, name] : [formatUsd(n), name];
                }}
              />
              <Line
                yAxisId="quality"
                type="monotone"
                dataKey="passRatePct"
                name="Pass rate"
                stroke="var(--color-ok)"
                strokeWidth={2}
                dot={{ r: 2, fill: "var(--color-ok)" }}
                isAnimationActive={false}
              />
              <Line
                yAxisId="cost"
                type="monotone"
                dataKey="costUsd"
                name="Cost"
                stroke="var(--color-ink-faint)"
                strokeWidth={1.5}
                strokeDasharray="4 3"
                dot={{ r: 2, fill: "var(--color-ink-faint)" }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </Tile>
  );
}
