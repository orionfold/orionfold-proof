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
  // SVG path `d` for the filled AREA under the line — each contiguous run is closed down to the
  // baseline (y=h) and back, so a light shade fills from the trend to the x-axis. This anchors the
  // line (a short 2-point trace would otherwise float at an unclear elevation). Null when empty;
  // a single point fills as a thin baseline rectangle so it's still visible.
  area: string | null;
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
  if (present.length === 0) return { line: null, area: null, formingPoint: null };

  const { w, h } = opts;
  const max = opts.max ?? Math.max(1e-9, ...present);
  const n = values.length;
  // x across the full slot count so the line "fills left→right" as samples arrive.
  const x = (i: number) => (n === 1 ? 0 : (i / (n - 1)) * w);
  // Inset the top by 1px so a max-height point isn't clipped at the very edge.
  const y = (v: number) => h - (Math.min(v, max) / max) * (h - 1);

  // Baseline (x-axis) y, inset 0.5px so a 1px fill edge isn't clipped at the very bottom.
  const base = h - 0.5;
  // A single point gives the area a hair of width so it fills as a thin baseline rectangle rather
  // than a zero-area sliver (an invisible vertical line).
  const HALF = 0.75;

  let line = "";
  let area = "";
  // A contiguous run of present samples (split by null gaps). Each run becomes one closed area:
  // baseline → up to the trace → along the trace → down to the baseline → Z.
  let run: { x: number; y: number }[] = [];
  const flushRun = () => {
    if (run.length === 0) return;
    const x0 = run.length === 1 ? run[0].x - HALF : run[0].x;
    const x1 = run.length === 1 ? run[0].x + HALF : run[run.length - 1].x;
    const seg =
      `M ${x0.toFixed(1)} ${base.toFixed(1)} ` + // start on the baseline at the run's left edge
      run.map((p) => `L ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ") +
      ` L ${x1.toFixed(1)} ${base.toFixed(1)} Z`; // drop back to the baseline and close
    area += (area ? " " : "") + seg;
    run = [];
  };

  let penDown = false;
  for (let i = 0; i < n; i++) {
    const v = values[i];
    if (v == null) {
      penDown = false; // lift the pen across the gap
      flushRun(); // close the area for the run that just ended
      continue;
    }
    const cmd = penDown ? "L" : "M";
    line += `${line ? " " : ""}${cmd} ${x(i).toFixed(1)} ${y(v).toFixed(1)}`;
    run.push({ x: x(i), y: y(v) });
    penDown = true;
  }
  flushRun(); // close the final run

  let formingPoint: SparkGeometry["formingPoint"] = null;
  if (opts.forming) {
    const last = values[n - 1];
    if (last != null) formingPoint = { x: x(n - 1), y: y(last) };
  }

  return { line: line || null, area: area || null, formingPoint };
}
