import { useEffect, useState } from "react";
import {
  Boxes,
  Database,
  Gauge,
  ReceiptText,
  Settings as SettingsIcon,
  type LucideIcon,
} from "lucide-react";

import { getHealth, type Health, type ProofReport } from "../lib/api";
import { CandidatesView } from "../features/proof/CandidatesView";
import { DatasetsView } from "../features/proof/DatasetsView";
import { ProofCockpit } from "../features/proof/ProofCockpit";
import { ReceiptDetailView } from "../features/proof/ReceiptDetailView";
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
      <span className="flex flex-col gap-0.5 text-xs">
        <span className="flex items-center gap-2 text-(--color-ink-muted)">
          <span aria-hidden className="inline-block h-2 w-2 shrink-0 rounded-full bg-rose-400" />
          Engine unreachable
        </span>
        <span className="break-words text-(--color-ink-faint)">{probe.message}</span>
      </span>
    );
  }
  // Two calm lines so the narrow rail never wraps mid-word or strands the separator: the
  // status on top, then the service name and version together on one no-wrap detail line.
  return (
    <span className="flex flex-col gap-0.5 text-xs">
      <span className="flex items-center gap-2 text-(--color-ink-muted)">
        <span aria-hidden className="inline-block h-2 w-2 shrink-0 rounded-full bg-(--color-accent)" />
        Connected
      </span>
      <span className="whitespace-nowrap text-(--color-ink-faint)">
        {probe.health.service} · v{probe.health.version}
      </span>
    </span>
  );
}

// The quiet left rail: the product's full map. Each item is a real destination now — Proof Run
// is the live loop; Datasets, Candidates, and Receipts are read-only views over the same engine.
const NAV: { id: View; label: string; Icon: LucideIcon }[] = [
  { id: "proof", label: "Proof Run", Icon: Gauge },
  { id: "datasets", label: "Datasets", Icon: Database },
  { id: "candidates", label: "Candidates", Icon: Boxes },
  { id: "receipts", label: "Receipts", Icon: ReceiptText },
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
              <item.Icon
                aria-hidden
                className={
                  "h-4 w-4 shrink-0 " + (active ? "text-(--color-accent)" : "text-(--color-ink-faint)")
                }
              />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="mt-auto flex flex-col gap-3 border-t border-(--color-panel-line) pt-4">
        {/* Settings has no screen in v0 (config is via env vars). Marked clearly as a roadmap
            item — a "soon" tag + not-allowed cursor — so it doesn't read as a clickable nav item. */}
        <span
          aria-disabled="true"
          className="flex cursor-not-allowed items-center justify-between rounded-md px-2.5 py-1.5 text-sm text-(--color-ink-faint)"
        >
          <span className="flex items-center gap-2">
            <SettingsIcon aria-hidden className="h-4 w-4 shrink-0" />
            Settings
          </span>
          <span className="text-[10px] uppercase tracking-wide text-(--color-ink-faint)">soon</span>
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
  // The run shown in the cockpit. Lifted here so a past run can load into the Proof Run workspace.
  const [report, setReport] = useState<ProofReport | null>(null);
  // The receipt being previewed as an artifact (Receipts → detail view). Null = show the archive.
  const [receiptInView, setReceiptInView] = useState<ProofReport | null>(null);

  // Rail navigation always clears the open receipt so Receipts reopens to its list.
  const navigate = (next: View) => {
    setReceiptInView(null);
    setView(next);
  };

  const openInCockpit = (r: ProofReport) => {
    setReceiptInView(null);
    setReport(r);
    setView("proof");
  };

  return (
    <div className="grid min-h-full grid-rows-[auto_1fr] lg:grid-cols-[15rem_minmax(0,1fr)] lg:grid-rows-1">
      <LeftRail view={view} onNavigate={navigate} />
      {/* Proof Run stays mounted (toggled with display, not unmounted) so an in-flight run, the
          brief, and the result survive a side trip to the other views. */}
      <div className={view === "proof" ? "contents" : "hidden"}>
        <ProofCockpit report={report} onReport={setReport} />
      </div>
      {view === "datasets" && <DatasetsView />}
      {view === "candidates" && <CandidatesView />}
      {view === "receipts" &&
        (receiptInView ? (
          <ReceiptDetailView
            report={receiptInView}
            onBack={() => setReceiptInView(null)}
            onExplore={openInCockpit}
          />
        ) : (
          <ReceiptsView onOpenReceipt={setReceiptInView} />
        ))}
    </div>
  );
}
