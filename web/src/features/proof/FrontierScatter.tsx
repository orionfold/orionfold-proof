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
import { buildScatterPoints, type ScatterPoint } from "./paretoFrontier";
import { passRateTone, type PassRateTone } from "./leaderboardFormat";

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
function CandidateDot(props: { cx?: number; cy?: number; payload?: ScatterPoint }) {
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

function FrontierTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: ScatterPoint }> }) {
  if (!active || !payload || payload.length === 0) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-lg border border-(--color-panel-line-strong) bg-(--color-panel-card) px-3 py-2 text-xs shadow-lg">
      <div className="font-medium text-(--color-ink)">{p.label}</div>
      <div className="mt-1 tabular-nums text-(--color-ink-muted)">
        ${p.cost.toFixed(4)} · {Math.round(p.quality * 100)}% pass
      </div>
      {p.recommended && <div className="mt-1 text-(--color-accent)">★ Recommended</div>}
      {!p.recommended && p.onFrontier && (
        <div className="mt-1 text-(--color-ink-faint)">◆ On the frontier</div>
      )}
    </div>
  );
}

export function FrontierScatter({ entries }: { entries: LeaderboardEntry[] }) {
  const points = buildScatterPoints(entries);
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

  // Frontier polyline: just the frontier points, cost-ascending, so Recharts
  // draws the skyline through them. Layered under the full scatter.
  const frontierLine = scored
    .filter((p) => p.onFrontier)
    .slice()
    .sort((a, b) => a.cost - b.cost);

  return (
    <section aria-label="Cost vs quality" className="w-full">
      <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-(--color-ink-muted)">
        Cost vs quality
      </h2>
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
                name="Pass rate"
                domain={[0, 1]}
                stroke="currentColor"
                tick={{ fontSize: 11, fill: "var(--color-ink-faint)" }}
                tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                label={{
                  value: "Pass rate",
                  angle: -90,
                  position: "insideLeft",
                  fontSize: 11,
                  fill: "var(--color-ink-faint)",
                }}
              />
              <Tooltip
                cursor={{ stroke: "var(--color-panel-line-strong)" }}
                content={<FrontierTooltip />}
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
      </div>
    </section>
  );
}
