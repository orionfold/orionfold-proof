import { useState } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

import type { LeaderboardEntry } from "../../lib/api";
import { buildScatterPoints, type ScatterPoint, type ScatterMetric } from "./paretoFrontier";
import { passRateTone, type PassRateTone } from "./leaderboardFormat";
import { deriveDecideInsight, type InsightTone } from "./decideInsights";

// Y-axis metric labels — the toggle flips between the headline pass rate and the
// raw avg score that rescues the ranking when the scorer is mismatched.
const METRIC_LABEL: Record<ScatterMetric, string> = {
  pass_rate: "Pass rate",
  avg_score: "Avg score",
};

// The cost-vs-quality trade-off, at a glance: spend on X (lower = better),
// pass rate on Y (higher = better). The Pareto frontier connects the
// non-dominated candidates; the recommended candidate is the ONLY accent.
//
// DS rule: --color-accent is reserved for the recommended point; other dots use
// status tokens (pass-rate tone) so pass/fail reads honestly without competing
// with the decision colour.

// Status token per pass-rate tone — same mapping as the leaderboard bars.
const TONE_VAR: Record<PassRateTone, string> = {
  ok: "var(--color-ok)",
  warn: "var(--color-warn)",
  danger: "var(--color-danger)",
};

const ACCENT = "var(--color-accent)";
const dotColor = (p: ScatterPoint) =>
  p.recommended ? ACCENT : TONE_VAR[passRateTone(p.quality)];

// Per-point dot (Recharts v3 `shape` callback — replaces the deprecated <Cell>).
// The recommended point is larger with an accent ring; others are plain status dots.
// Exported for unit tests: Recharts can't compute dot geometry under jsdom, so the
// accent invariant is verified by calling this directly with coordinates.
export function CandidateDot(props: { cx?: number; cy?: number; payload?: ScatterPoint }) {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null || !payload) return <g />;
  const fill = dotColor(payload);
  if (payload.recommended) {
    return (
      <g>
        <circle cx={cx} cy={cy} r={7} fill={fill} />
        <circle cx={cx} cy={cy} r={10} fill="none" stroke={ACCENT} strokeWidth={2} />
      </g>
    );
  }
  return <circle cx={cx} cy={cy} r={6} fill={fill} />;
}

function FrontierTooltip({
  active,
  payload,
  metric,
}: {
  active?: boolean;
  payload?: Array<{ payload: ScatterPoint }>;
  metric: ScatterMetric;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const p = payload[0].payload;
  const yLabel = metric === "avg_score" ? "avg score" : "pass";
  return (
    <div className="rounded-lg border border-(--color-panel-line-strong) bg-(--color-panel-card) px-3 py-2 text-xs shadow-lg">
      <div className="font-medium text-(--color-ink)">{p.label}</div>
      <div className="mt-1 tabular-nums text-(--color-ink-muted)">
        ${p.cost.toFixed(4)} · {Math.round(p.quality * 100)}% {yLabel}
      </div>
      {p.recommended && <div className="mt-1 text-(--color-accent)">★ Recommended</div>}
      {!p.recommended && p.onFrontier && (
        <div className="mt-1 text-(--color-ink-faint)">◆ On the frontier</div>
      )}
    </div>
  );
}

// Explainer tone → status / ink tokens (NEVER the cyan accent — reserved for the
// recommended scatter point per the DS split).
const INSIGHT_TONE_VAR: Record<InsightTone, string> = {
  ok: "var(--color-ok)",
  warn: "var(--color-warn)",
  info: "var(--color-ink-muted)",
};

// Deterministic plain-English explainer beneath the chart. Reasons about the run
// (not the current Y view), so its text does not change when the toggle flips.
function DecideExplainer({ entries }: { entries: LeaderboardEntry[] }) {
  const insight = deriveDecideInsight(entries);
  if (!insight) return null;
  const tone = INSIGHT_TONE_VAR[insight.tone];
  return (
    <div
      data-testid="decide-explainer"
      data-tone={insight.tone}
      className="mt-4 flex gap-2.5 rounded-lg border border-(--color-panel-line) bg-(--color-panel-card) px-3.5 py-3 text-sm"
    >
      <span
        aria-hidden="true"
        className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
        style={{ backgroundColor: tone }}
      />
      <div>
        <div className="font-medium text-(--color-ink)" style={{ color: tone }}>
          {insight.headline}
        </div>
        <p className="mt-0.5 text-(--color-ink-muted)">{insight.detail}</p>
      </div>
    </div>
  );
}

export function FrontierScatter({ entries }: { entries: LeaderboardEntry[] }) {
  const [metric, setMetric] = useState<ScatterMetric>("pass_rate");
  const points = buildScatterPoints(entries, metric);
  // The trade-off only reads with at least two scored candidates to compare.
  const scored = points.filter((p) => Number.isFinite(p.cost) && Number.isFinite(p.quality));

  if (scored.length < 2) {
    return (
      <section aria-label="Cost vs quality" className="w-full">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-(--color-ink-muted)">
          Cost vs quality
        </h2>
        <div className="rounded-xl border border-(--color-panel-line) p-6 text-sm text-(--color-ink-faint)">
          Not enough candidates to plot a cost-vs-quality trade-off.
        </div>
      </section>
    );
  }

  const yLabel = METRIC_LABEL[metric];

  // Frontier polyline: just the frontier points, cost-ascending, so Recharts
  // draws the skyline through them. Layered under the full scatter.
  const frontierLine = scored
    .filter((p) => p.onFrontier)
    .slice()
    .sort((a, b) => a.cost - b.cost);

  return (
    <section aria-label="Cost vs quality" className="w-full">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-sm font-medium uppercase tracking-wide text-(--color-ink-muted)">
          Cost vs quality
        </h2>
        <div
          role="group"
          aria-label="Y axis metric"
          className="inline-flex w-fit rounded-lg border border-(--color-panel-line) p-0.5 text-xs"
        >
          {(["pass_rate", "avg_score"] as const).map((m) => (
            <button
              key={m}
              type="button"
              aria-pressed={metric === m}
              onClick={() => setMetric(m)}
              className={
                "rounded-md px-2.5 py-1 transition-colors " +
                (metric === m
                  ? "bg-(--color-accent-strong) text-(--color-accent-ink)"
                  : "text-(--color-ink-muted) hover:text-(--color-ink)")
              }
            >
              {METRIC_LABEL[m]}
            </button>
          ))}
        </div>
      </div>
      <div className="rounded-xl border border-(--color-panel-line) p-4">
        <div className="h-72 w-full text-(--color-ink-faint)" data-testid="frontier-scatter">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 12, right: 20, bottom: 28, left: 8 }}>
              <CartesianGrid stroke="var(--color-panel-line)" strokeDasharray="3 3" />
              <XAxis
                type="number"
                dataKey="cost"
                name="Est. cost"
                stroke="currentColor"
                tick={{ fontSize: 11, fill: "var(--color-ink-faint)" }}
                tickFormatter={(v: number) => (v === 0 ? "$0" : `$${v.toFixed(2)}`)}
                label={{
                  value: "Est. cost ($) — lower is better",
                  position: "bottom",
                  offset: 12,
                  fontSize: 11,
                  fill: "var(--color-ink-faint)",
                }}
              />
              <YAxis
                type="number"
                dataKey="quality"
                name={yLabel}
                domain={[0, 1]}
                stroke="currentColor"
                tick={{ fontSize: 11, fill: "var(--color-ink-faint)" }}
                tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                label={{
                  value: yLabel,
                  angle: -90,
                  position: "insideLeft",
                  fontSize: 11,
                  fill: "var(--color-ink-faint)",
                }}
              />
              <Tooltip
                cursor={{ stroke: "var(--color-panel-line-strong)" }}
                content={<FrontierTooltip metric={metric} />}
              />
              {/* Frontier skyline — neutral ink line, no dots (the scatter owns the dots). */}
              <Scatter
                data={frontierLine}
                line={{ stroke: "var(--color-ink-faint)", strokeWidth: 1.5 }}
                lineType="joint"
                shape={() => <g />}
                isAnimationActive={false}
                legendType="none"
              />
              {/* Candidate dots — recommended accents, others status-toned. */}
              <Scatter
                data={scored}
                isAnimationActive={false}
                shape={<CandidateDot />}
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
        <DecideExplainer entries={entries} />
      </div>
    </section>
  );
}
