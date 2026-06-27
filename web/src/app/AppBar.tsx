import { useEffect, useState } from "react";
import {
  Database,
  Gauge,
  ReceiptText,
  Settings,
  Monitor,
  Sun,
  Moon,
  type LucideIcon,
} from "lucide-react";

import { getHealth, type Health } from "../lib/api";
import { useTheme, type ThemeChoice } from "../lib/theme";

// The four standing destinations after the Arena-shape reshape: Prove (the live loop), Datasets,
// Receipts (now folds in Track Record), Settings. `id` matches App's View union so the bar can
// drive navigation directly. Candidates folded into Prove/Datasets; Track Record into Receipts.
// Each tab carries a Lucide glyph so the nav reads as a scannable instrument panel, not a text
// list — the icon color follows the action/instrument law (cyan-ink when active, faint at rest).
export type NavId = "proof" | "datasets" | "receipts" | "settings";

export const NAV: { id: NavId; label: string; Icon: LucideIcon }[] = [
  { id: "proof", label: "Prove", Icon: Gauge },
  { id: "datasets", label: "Datasets", Icon: Database },
  { id: "receipts", label: "Receipts", Icon: ReceiptText },
  { id: "settings", label: "Settings", Icon: Settings },
];

// Compact single-tier top app bar (~52px, --bar-h). Sticky + blurred so it floats over the
// blueprint canvas; a hairline bottom border seals it. Brand left · nav center · engine status
// right. Replaces the old 15rem left rail — the nav is now horizontal (spec §3).
export function AppBar({
  view,
  onNavigate,
}: {
  view: string;
  onNavigate: (id: NavId) => void;
}) {
  return (
    <header
      className="sticky top-0 z-30 flex h-(--bar-h) shrink-0 items-center gap-4 border-b border-(--color-panel-line) bg-(--color-rail)/85 px-4 backdrop-blur"
    >
      <Brand />
      <nav aria-label="Primary" className="flex items-center gap-1 text-sm">
        {NAV.map((item) => {
          const active = item.id === view;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              aria-current={active ? "page" : undefined}
              className={
                // ≥32px hit target (h-8) per the real-estate budget; active tab = cyan FILL (the
                // one action color), inactive = quiet ink that warms on hover.
                "flex h-8 items-center gap-1.5 rounded-md px-3 font-medium transition-colors " +
                (active
                  ? "bg-(--color-accent) text-(--color-accent-ink) shadow-[0_0_0_1px_var(--color-accent-strong)]"
                  : "text-(--color-ink-muted) hover:bg-(--color-panel-card) hover:text-(--color-ink)")
              }
            >
              <item.Icon
                aria-hidden
                className={
                  "h-4 w-4 shrink-0 " +
                  (active ? "text-(--color-accent-ink)" : "text-(--color-ink-faint)")
                }
              />
              {item.label}
            </button>
          );
        })}
      </nav>
      <div className="ml-auto flex items-center gap-3">
        <ThemeToggle />
        <EngineStatus />
      </div>
    </header>
  );
}

// A compact global theme control in the bar — the app-like, always-reachable switcher (the full
// 3-way radiogroup also lives in Settings). Cycles system → light → dark; the icon shows the
// CURRENT choice so the control reads as state, not a generic gear. Theme is appearance, not an
// action, so it stays quiet instrument ink — never the cyan accent.
const THEME_CYCLE: { value: ThemeChoice; Icon: LucideIcon; label: string }[] = [
  { value: "system", Icon: Monitor, label: "System theme" },
  { value: "light", Icon: Sun, label: "Light theme" },
  { value: "dark", Icon: Moon, label: "Dark theme" },
];

function ThemeToggle() {
  const { choice, setChoice } = useTheme();
  const idx = THEME_CYCLE.findIndex((t) => t.value === choice);
  const current = THEME_CYCLE[idx === -1 ? 0 : idx];
  const next = THEME_CYCLE[(idx + 1) % THEME_CYCLE.length];
  return (
    <button
      type="button"
      onClick={() => setChoice(next.value)}
      aria-label={`${current.label} — switch to ${next.label.toLowerCase()}`}
      title={`Theme: ${current.value} (click for ${next.value})`}
      className="flex h-8 w-8 items-center justify-center rounded-md text-(--color-ink-muted) transition-colors hover:bg-(--color-panel-card) hover:text-(--color-ink)"
    >
      <current.Icon aria-hidden className="h-4 w-4 shrink-0" />
    </button>
  );
}

// Orionfold delta-star mark + wordmark + product line. Mark ported verbatim from the brand sprite
// (a cyan disc + white star rotated 45°). The accessible heading name resolves to "Orionfold Proof".
function Brand() {
  return (
    <div className="flex items-center gap-2">
      <svg viewBox="0 0 64 64" aria-hidden className="h-5 w-5 shrink-0 text-(--color-accent)">
        <circle cx="32" cy="32" r="32" fill="currentColor" />
        <g transform="rotate(45 32 32)">
          <path
            className="fill-white"
            d="M32,9L37.41,24.56L53.88,24.89L40.75,34.84L45.52,50.61L32,41.2L18.48,50.61L23.25,34.84L10.12,24.89L26.59,24.56Z"
          />
        </g>
      </svg>
      <h1
        aria-label="Orionfold Proof"
        className="text-sm font-semibold tracking-tight text-(--color-ink)"
      >
        Orion<span className="text-(--color-accent)">fold</span> Proof
      </h1>
    </div>
  );
}

type Probe =
  | { state: "loading" }
  | { state: "ok"; health: Health }
  | { state: "error"; message: string };

// Calm reassurance that the local engine is reachable — a status, not a control. Moved here from
// the old left rail's footer; condensed to one horizontal pill to fit the compact bar.
function useHealth(): Probe {
  const [probe, setProbe] = useState<Probe>({ state: "loading" });
  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then((health) => {
        if (!cancelled) setProbe({ state: "ok", health });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setProbe({ state: "error", message: err instanceof Error ? err.message : "unknown" });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);
  return probe;
}

function EngineStatus() {
  const probe = useHealth();

  if (probe.state === "loading") {
    return <span className="text-xs text-(--color-ink-faint)">Checking the local engine…</span>;
  }
  if (probe.state === "error") {
    return (
      <span
        title={probe.message}
        className="flex items-center gap-2 text-xs text-(--color-ink-muted)"
      >
        {/* status dot is functional color, never the cyan action accent — never color alone. */}
        <span aria-hidden className="inline-block h-2 w-2 shrink-0 rounded-full bg-(--color-danger)" />
        Engine unreachable
      </span>
    );
  }
  return (
    <span className="flex items-center gap-2 whitespace-nowrap text-xs text-(--color-ink-muted)">
      <span aria-hidden className="inline-block h-2 w-2 shrink-0 rounded-full bg-(--color-ok)" />
      Connected
      <span className="text-(--color-ink-faint)">
        {probe.health.service} · v{probe.health.version}
      </span>
    </span>
  );
}
