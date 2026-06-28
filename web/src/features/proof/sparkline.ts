// Live host-trend sparkline for the telemetry rail.
//
// DESIGN NOTE (operator-approved deviation from the redesign plan): the plan said "port Arena's
// canvas peak-bar renderer (peakbars.mjs / drawBars)". We instead keep Arena's *peak-over-bucket
// accumulator* idea (it smooths the ~500ms sample jitter nicely) but render with **declarative SVG**
// instead of canvas. Why SVG fits Proof better than canvas here:
//   • theme-token-native — stroke={var(--color-ok)} just works; canvas must read computed styles.
//   • crisp at any DPR for free; no manual devicePixelRatio scaling or redraw-on-resize.
//   • testable — the geometry (sparklinePath) is a pure function, unlike imperative canvas paint.
//   • Proof's rail is a *status instrument*, not a sustained-load monitor — one calm live trend
//     line reads better than a wall of FIFO bars, and the other six cells stay chart-free readouts.
// We stay siblings with Arena (same peak-bucket concept, FIFO ring, dimmed forming edge), just a
// calmer expression. See docs/superpowers/specs/2026-06-27-arena-shape-cockpit-redesign-design.md §5.

// Bars/points across the trend when full. The FIFO ring drops the oldest once exceeded.
export const SLOTS = 24;

export interface Trend {
  // Finalized peak values, oldest first. `null` marks a window with no valid sample (an honest
  // gap, never a fabricated zero).
  finalized: (number | null)[];
  // The in-progress bucket's running peak (drawn dimmed as the live edge), or null at rest.
  forming: number | null;
  // How many samples have landed in the current (unsealed) bucket.
  count: number;
}

export function emptyTrend(): Trend {
  return { finalized: [], forming: null, count: 0 };
}

// Fold one live sample into the trend. `bucket` = samples per finalized bar (peak-over-window). A
// bucket seals once `bucket` samples have landed; its peak FIFOs into `finalized`. `value` may be
// null (missing sample) — it's ignored for the peak but still advances the bucket so time keeps
// flowing. Pure: returns a new Trend, never mutates.
export function pushSample(trend: Trend, value: number | null, opts?: { bucket?: number }): Trend {
  const bucket = Math.max(1, opts?.bucket ?? 1);
  // Running peak of the forming bucket, treating null as "no contribution".
  const peak = value == null ? trend.forming : trend.forming == null ? value : Math.max(trend.forming, value);
  const count = trend.count + 1;

  if (count < bucket) {
    return { ...trend, forming: peak, count };
  }
  // Seal the bucket: push its peak (which may be null if every sample in the window was null).
  let finalized = [...trend.finalized, peak];
  if (finalized.length > SLOTS) finalized = finalized.slice(finalized.length - SLOTS);
  return { finalized, forming: null, count: 0 };
}

// Seed a Trend from a persisted per-bucket series (the stored last-run record). The series is
// already bucketed (peak-over-window, from the backend `_bucket_peaks` mirror of `pushSample`), so
// it loads straight as finalized bars with no forming edge — it renders dimmed (the run is over).
// FIFO-clamped to SLOTS so a long run's tail matches the live ring. Pure.
export function trendFromSeries(series: number[]): Trend {
  const finalized = series.length > SLOTS ? series.slice(series.length - SLOTS) : [...series];
  return { finalized, forming: null, count: 0 };
}

export interface SparkGeometry {
  // SVG path `d` for the trend line. Null when there's nothing to draw. Uses M…L… with the pen
  // lifted (a fresh M) across null gaps so no line is drawn through missing data.
  line: string | null;
  // The live edge point (the forming bucket), so the caller can render it dimmed. Null at rest.
  formingPoint: { x: number; y: number } | null;
}

// Pure SVG geometry for the trend. Values map into a w×h box: the data max sits at the top
// (y≈0), zero at the bottom (y≈h). `max` pins the scale (e.g. 100 for a percentage) so the line
// doesn't rescale every frame; omitted → auto-scale to the data. `forming: true` marks the last
// value as the in-progress edge.
export function sparklinePath(
  values: (number | null)[],
  opts: { w: number; h: number; max?: number; forming?: boolean },
): SparkGeometry {
  const present = values.filter((v): v is number => v != null);
  if (present.length === 0) return { line: null, formingPoint: null };

  const { w, h } = opts;
  const max = opts.max ?? Math.max(1e-9, ...present);
  const n = values.length;
  // x across the full slot count so the line "fills left→right" as samples arrive.
  const x = (i: number) => (n === 1 ? 0 : (i / (n - 1)) * w);
  // Inset the top by 1px so a max-height point isn't clipped at the very edge.
  const y = (v: number) => h - (Math.min(v, max) / max) * (h - 1);

  let line = "";
  let penDown = false;
  for (let i = 0; i < n; i++) {
    const v = values[i];
    if (v == null) {
      penDown = false; // lift the pen across the gap
      continue;
    }
    const cmd = penDown ? "L" : "M";
    line += `${line ? " " : ""}${cmd} ${x(i).toFixed(1)} ${y(v).toFixed(1)}`;
    penDown = true;
  }

  let formingPoint: SparkGeometry["formingPoint"] = null;
  if (opts.forming) {
    const last = values[n - 1];
    if (last != null) formingPoint = { x: x(n - 1), y: y(last) };
  }

  return { line: line || null, formingPoint };
}
