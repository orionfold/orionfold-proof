import { useState } from "react";

import { type ProofReport } from "../lib/api";
import { AppBar, type NavId } from "./AppBar";
import { TelemetryRail } from "./TelemetryRail";
import { type RunProgress } from "../features/proof/useRunProgress";
import { CorpusView } from "../features/proof/CorpusView";
import { DatasetsView } from "../features/proof/DatasetsView";
import { ProofCockpit } from "../features/proof/ProofCockpit";
import { ReceiptDetailView } from "../features/proof/ReceiptDetailView";
import { ReceiptsView, type ReceiptsMode } from "../features/proof/ReceiptsView";
import { SettingsView } from "../features/proof/SettingsView";

// "corpus" is a sub-surface of Datasets (opened from a bench card's corpus badge), so it lives in
// the View union but is not a nav tab — it has no bar entry; "Back to datasets" returns to the list.
// The nav set is the 4 NavId tabs (Prove·Datasets·Receipts·Settings); Candidates folded into
// Prove/Datasets and Track Record folds into Receipts (Slice 4).
type View = NavId | "corpus";

export function App() {
  const [view, setView] = useState<View>("proof");
  // The run shown in the cockpit. Lifted here so a past run can load into the Proof Run workspace.
  const [report, setReport] = useState<ProofReport | null>(null);
  // The receipt being previewed as an artifact (Receipts → detail view). Null = show the archive.
  const [receiptInView, setReceiptInView] = useState<ProofReport | null>(null);
  // A dataset to auto-expand when Datasets opens — set by "View details" on the Proof Run summary,
  // cleared on any plain nav so the deep-link is one-shot.
  const [datasetFocusId, setDatasetFocusId] = useState<string | null>(null);
  // The mirror of datasetFocusId: a dataset to preselect when the cockpit opens — set by "Run proof"
  // on a Datasets card, consumed once by the cockpit, cleared on any plain nav.
  const [preselectDatasetId, setPreselectDatasetId] = useState<string | null>(null);
  // The corpus to browse — set by a bench card's corpus badge; the "corpus" sub-view reads it.
  const [corpusFocusId, setCorpusFocusId] = useState<string | null>(null);
  // True WHILE a proof run is streaming. Lifted from the cockpit so the telemetry rail can light up
  // the live gauges during the run — the finished `report` only exists AFTER the run, so it can't
  // be the live signal. The rail subscribes to the telemetry stream whenever runActive is true.
  const [runActive, setRunActive] = useState(false);
  // Live run progress (pass-rate-so-far + candidates done/total), lifted from the cockpit so the
  // telemetry rail can show it. Null at rest. Sibling to runActive.
  const [runProgress, setRunProgress] = useState<RunProgress | null>(null);
  // Which Receipts mode to open in. The rail drills into the right one: last-result/last-receipt →
  // Runs (that receipt), cost/pass-rate trend → Track Record (the standings). Consumed by
  // ReceiptsView's initialMode; reset to "runs" on a plain nav so the tab reopens to its root.
  const [receiptsMode, setReceiptsMode] = useState<ReceiptsMode>("runs");

  // Nav always clears the open receipt + one-shot deep-links so each tab reopens to its own root.
  const navigate = (next: View) => {
    setReceiptInView(null);
    setDatasetFocusId(null);
    setPreselectDatasetId(null);
    setCorpusFocusId(null);
    setReceiptsMode("runs");
    setView(next);
  };

  // A rail cell drills into Receipts on a specific mode (Runs vs Track Record, per spec §4). Unlike
  // a plain nav this sets the target mode first, so the toggle opens where the cell points.
  const openReceipts = (mode: ReceiptsMode) => {
    setReceiptInView(null);
    setReceiptsMode(mode);
    setView("receipts");
  };

  // "View details" on the Proof Run dataset summary: jump to Datasets with that card expanded.
  const openDataset = (id: string) => {
    setReceiptInView(null);
    setDatasetFocusId(id);
    setView("datasets");
  };

  // "Run proof →" on a Datasets card: jump to the Proof Run workspace with that dataset selected.
  const runDataset = (id: string) => {
    setReceiptInView(null);
    setPreselectDatasetId(id);
    setView("proof");
  };

  // The corpus badge on a bench card: open the Corpus browse surface for that source set.
  const openCorpus = (id: string) => {
    setReceiptInView(null);
    setCorpusFocusId(id);
    setView("corpus");
  };

  const openInCockpit = (r: ProofReport) => {
    setReceiptInView(null);
    setReport(r);
    setView("proof");
  };

  // The reverse of openInCockpit: "View full receipt →" on a finished Prove run opens that run's
  // L3 detail page (config hash, hardware, leaderboard, cost, failure detail, exports) — the record
  // the right Inspector used to show in place. Switches to the Receipts tab with the run open.
  const openReceiptDetail = (r: ProofReport) => {
    setReceiptInView(r);
    setView("receipts");
  };

  return (
    // Arena shape: a vertical stack — app bar / telemetry rail / full-width canvas / footer. The
    // blueprint draughting field (spec §3.2) shows only in whitespace; dense surfaces paint over it.
    <div className="blueprint flex min-h-full flex-col">
      {/* Skip-to-content: the first focusable element, hidden until focused. Targets the Prove
          workspace — the primary default region. */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-(--color-accent-strong) focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-(--color-accent-ink)"
      >
        Skip to content
      </a>

      <AppBar view={view} onNavigate={navigate} />
      <TelemetryRail
        runActive={runActive}
        runProgress={runProgress}
        lastReport={report}
        onOpenReceipts={openReceipts}
      />

      {/* MAIN CANVAS — single full-width region. Each screen owns its own width cap (reading vs
          working) via ViewShell / its component. flex-1 so short screens still fill the fold. */}
      <div className="flex flex-1 flex-col">
        {/* Prove stays mounted (toggled with display, not unmounted) so an in-flight run, the brief,
            and the result survive a side trip to other views. The run's config, hardware, and
            failure-case detail (once the right Inspector's content) now live on the L3 receipt-detail
            screen (Slice 5), so Prove is a single full-width working canvas like every other view. */}
        <div className={view === "proof" ? "contents" : "hidden"}>
          <ProofCockpit
            report={report}
            onReport={setReport}
            onViewDataset={openDataset}
            onViewReceipt={openReceiptDetail}
            preselectDatasetId={preselectDatasetId}
            onPreselectConsumed={() => setPreselectDatasetId(null)}
            onRunActiveChange={setRunActive}
            onRunProgressChange={setRunProgress}
          />
        </div>

        {view === "datasets" && (
          <DatasetsView focusId={datasetFocusId} onRunDataset={runDataset} onOpenCorpus={openCorpus} />
        )}
        {view === "corpus" && corpusFocusId && (
          <CorpusView corpusId={corpusFocusId} onBack={() => navigate("datasets")} />
        )}
        {view === "settings" && <SettingsView />}
        {view === "receipts" &&
          (receiptInView ? (
            <ReceiptDetailView
              report={receiptInView}
              onBack={() => setReceiptInView(null)}
              onExplore={openInCockpit}
            />
          ) : (
            <ReceiptsView initialMode={receiptsMode} onOpenReceipt={setReceiptInView} />
          ))}
      </div>
    </div>
  );
}
