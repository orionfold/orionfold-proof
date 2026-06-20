import { useEffect, useState } from "react";

import { getHealth, type Health } from "../lib/api";
import { ProofCockpit } from "../features/proof/ProofCockpit";

type Probe =
  | { state: "loading" }
  | { state: "ok"; health: Health }
  | { state: "error"; message: string };

// A compact engine status pill — calm reassurance that the local engine is reachable,
// without stealing focus from the proof loop.
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
          setProbe({
            state: "error",
            message: err instanceof Error ? err.message : "unknown",
          });
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
      <span className="flex items-center gap-2 text-xs text-(--color-ink-muted)">
        <span aria-hidden className="inline-block h-2 w-2 rounded-full bg-rose-400" />
        Engine unreachable
        <span className="text-(--color-ink-faint)">({probe.message})</span>
      </span>
    );
  }
  return (
    <span className="flex items-center gap-2 text-xs text-(--color-ink-muted)">
      <span aria-hidden className="inline-block h-2 w-2 rounded-full bg-(--color-accent)" />
      Connected · <span className="text-(--color-ink-faint)">{probe.health.service}</span> v
      {probe.health.version}
    </span>
  );
}

// The quiet left rail: the product's full map. "Proof Run" is the live v0 surface; the rest
// are calm destinations on the roadmap, shown so the structure reads, never as dead links.
const NAV: { label: string; active?: boolean; soon?: boolean }[] = [
  { label: "Proof Run", active: true },
  { label: "Datasets", soon: true },
  { label: "Candidates", soon: true },
  { label: "Receipts", soon: true },
];

function LeftRail() {
  return (
    <aside
      aria-label="Navigation"
      className="flex flex-col gap-6 border-b border-(--color-panel-line) bg-(--color-rail) px-4 py-5 lg:h-full lg:border-b-0 lg:border-r"
    >
      <div className="flex items-center gap-2">
        <span aria-hidden className="h-4 w-4 rounded-sm bg-(--color-accent)" />
        <h1 className="text-sm font-semibold tracking-tight text-(--color-ink)">
          Orionfold Proof
        </h1>
      </div>

      <nav className="flex flex-col gap-0.5 text-sm">
        {NAV.map((item) =>
          item.soon ? (
            <span
              key={item.label}
              aria-disabled="true"
              className="flex items-center justify-between rounded-md px-2.5 py-1.5 text-(--color-ink-faint)"
            >
              {item.label}
              <span className="text-[10px] uppercase tracking-wide text-(--color-ink-faint)">
                soon
              </span>
            </span>
          ) : (
            <span
              key={item.label}
              aria-current={item.active ? "page" : undefined}
              className="flex items-center gap-2 rounded-md bg-(--color-panel-card) px-2.5 py-1.5 font-medium text-(--color-ink)"
            >
              <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-(--color-accent)" />
              {item.label}
            </span>
          ),
        )}
      </nav>

      <div className="mt-auto flex flex-col gap-3 border-t border-(--color-panel-line) pt-4">
        <span
          aria-disabled="true"
          className="rounded-md px-2.5 py-1.5 text-sm text-(--color-ink-faint)"
        >
          Settings
        </span>
        <div className="px-2.5">
          <EngineStatus />
        </div>
      </div>
    </aside>
  );
}

export function App() {
  return (
    <div className="grid min-h-full grid-rows-[auto_1fr] lg:grid-cols-[15rem_minmax(0,1fr)] lg:grid-rows-1">
      <LeftRail />
      <ProofCockpit />
    </div>
  );
}
