import { useEffect, useState } from "react";

import { getHealth, type Health, type ProofReport } from "../lib/api";
import { CandidatesView } from "../features/proof/CandidatesView";
import { DatasetsView } from "../features/proof/DatasetsView";
import { ProofCockpit } from "../features/proof/ProofCockpit";
import { ReceiptsView } from "../features/proof/ReceiptsView";

type View = "proof" | "datasets" | "candidates" | "receipts";

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

// The quiet left rail: the product's full map. Each item is a real destination now — Proof Run
// is the live loop; Datasets, Candidates, and Receipts are read-only views over the same engine.
const NAV: { id: View; label: string }[] = [
  { id: "proof", label: "Proof Run" },
  { id: "datasets", label: "Datasets" },
  { id: "candidates", label: "Candidates" },
  { id: "receipts", label: "Receipts" },
];

function LeftRail({ view, onNavigate }: { view: View; onNavigate: (view: View) => void }) {
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
        {NAV.map((item) => {
          const active = item.id === view;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              aria-current={active ? "page" : undefined}
              className={
                "flex items-center gap-2 rounded-md px-2.5 py-1.5 text-left transition-colors " +
                (active
                  ? "bg-(--color-panel-card) font-medium text-(--color-ink)"
                  : "text-(--color-ink-muted) hover:bg-(--color-panel-card)/60 hover:text-(--color-ink)")
              }
            >
              <span
                aria-hidden
                className={
                  "h-1.5 w-1.5 rounded-full " + (active ? "bg-(--color-accent)" : "bg-transparent")
                }
              />
              {item.label}
            </button>
          );
        })}
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
  const [view, setView] = useState<View>("proof");
  // The run shown in the cockpit. Lifted here so a row in Receipts can load a past run into the
  // same Proof Run workspace (leaderboard, failures, inspector) rather than a separate viewer.
  const [report, setReport] = useState<ProofReport | null>(null);

  const openInCockpit = (r: ProofReport) => {
    setReport(r);
    setView("proof");
  };

  return (
    <div className="grid min-h-full grid-rows-[auto_1fr] lg:grid-cols-[15rem_minmax(0,1fr)] lg:grid-rows-1">
      <LeftRail view={view} onNavigate={setView} />
      {/* Proof Run stays mounted (toggled with display, not unmounted) so an in-flight run, the
          brief, and the result survive a side trip to the other views. `contents` lets the
          cockpit's own grid be the content-column grid item; `hidden` removes it from layout. */}
      <div className={view === "proof" ? "contents" : "hidden"}>
        <ProofCockpit report={report} onReport={setReport} />
      </div>
      {view === "datasets" && <DatasetsView />}
      {view === "candidates" && <CandidatesView />}
      {view === "receipts" && <ReceiptsView onOpen={openInCockpit} />}
    </div>
  );
}
