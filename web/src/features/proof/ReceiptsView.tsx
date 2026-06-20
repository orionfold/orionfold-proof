import { useQuery } from "@tanstack/react-query";

import { getRuns, receiptUrl, type LeaderboardEntry, type ProofReport } from "../../lib/api";
import { ProviderTag } from "./badges";
import { ViewNotice, ViewShell } from "./ViewShell";

const FORMATS: { fmt: "md" | "html" | "json"; label: string }[] = [
  { fmt: "md", label: "Markdown" },
  { fmt: "html", label: "HTML" },
  { fmt: "json", label: "JSON" },
];

// The receipts archive: every past proof run, newest first. Each is the takeaway artifact —
// open it back into the cockpit to re-read the leaderboard and failures, or download it to share.
export function ReceiptsView({ onOpen }: { onOpen: (report: ProofReport) => void }) {
  const runs = useQuery({ queryKey: ["runs"], queryFn: getRuns });

  return (
    <ViewShell
      title="Receipts"
      subtitle="Every proof you've run, newest first. Open one to re-read its leaderboard and failure cases in the cockpit, or download the receipt to share — each carries its config hash and timestamp."
    >
      {runs.isLoading ? (
        <ViewNotice>Loading receipts…</ViewNotice>
      ) : runs.isError || !runs.data ? (
        <ViewNotice tone="error">
          Could not reach the local engine. Start it with <code>orionfold up</code>, then reload.
        </ViewNotice>
      ) : runs.data.length === 0 ? (
        <ViewNotice>
          No proof runs yet. Head to <span className="text-(--color-ink)">Proof Run</span> and press
          Run proof — your first receipt will appear here.
        </ViewNotice>
      ) : (
        <ul aria-label="Past proof runs" className="grid gap-3">
          {runs.data.map((report) => (
            <li key={report.run.id}>
              <ReceiptCard report={report} onOpen={() => onOpen(report)} />
            </li>
          ))}
        </ul>
      )}
    </ViewShell>
  );
}

function winnerOf(leaderboard: LeaderboardEntry[]): LeaderboardEntry | undefined {
  return leaderboard.find((e) => e.recommended) ?? leaderboard[0];
}

function ReceiptCard({ report, onOpen }: { report: ProofReport; onOpen: () => void }) {
  const { run } = report;
  const winner = winnerOf(report.leaderboard);
  const heading = run.brief.decision_question || run.brief.task_name;

  return (
    <div className="rounded-xl border border-(--color-panel-line) bg-(--color-panel-card) transition-colors hover:border-(--color-panel-line-strong)">
      {/* Clickable summary reopens the run in the cockpit. Kept a button (not a link) so the
          download anchors below can live outside it — anchors must never nest inside a button. */}
      <button
        type="button"
        onClick={onOpen}
        className="grid w-full gap-2 rounded-t-xl px-5 pt-4 pb-3 text-left"
      >
        <div className="flex items-start justify-between gap-3">
          <span className="font-medium text-(--color-ink)">{heading}</span>
          <span aria-hidden className="text-(--color-ink-faint)">
            Open ›
          </span>
        </div>
        {winner && (
          <div className="flex flex-wrap items-center gap-2 text-sm text-(--color-ink-muted)">
            <span className="text-(--color-ink-faint)">Winner</span>
            <span className="text-(--color-ink)">{winner.label}</span>
            <ProviderTag candidate={winner} />
            <span>
              {Math.round(winner.pass_rate * 100)}% ({winner.pass_count}/{winner.total})
            </span>
          </div>
        )}
      </button>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-(--color-panel-line) px-5 py-3 text-xs">
        <span className="text-(--color-ink-faint)">{run.dataset_name}</span>
        <code className="text-(--color-ink-muted)">{run.config_hash}</code>
        <span className="text-(--color-ink-faint)">{run.created_at}</span>
        <span className="ml-auto flex items-center gap-2">
          <span className="text-(--color-ink-faint)">Download</span>
          {FORMATS.map(({ fmt, label }) => (
            <a
              key={fmt}
              href={receiptUrl(run.id, fmt)}
              download
              className="rounded-md border border-(--color-panel-line) px-2 py-1 text-(--color-ink) transition-colors hover:border-(--color-accent)/50"
            >
              {label}
            </a>
          ))}
        </span>
      </div>
    </div>
  );
}
