import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { patchWinner, type ProofReport, type ResultRow } from "../../lib/api";
import { ProviderTag } from "./badges";
import { objectiveBar, totalTokens } from "./quickCompareFormat";

// The unscored head-to-head: two outputs, objective bars (latency / cost / tokens), and the
// operator's pick. Bars use neutral ink — never the accent (interactive) or green (PASS).
export function QuickCompare({
  report,
  onReport,
  onPromote,
}: {
  report: ProofReport;
  onReport: (r: ProofReport) => void;
  onPromote: () => void;
}) {
  const [pick, setPick] = useState<string | null>(report.run.chosen_winner ?? null);
  const save = useMutation({
    mutationFn: (winner: string) => patchWinner(report.run.id, winner),
    onSuccess: (r) => onReport(r),
  });

  const byId = new Map(report.run.candidates.map((c) => [c.id, c]));
  const rows = report.results;
  const maxLatency = Math.max(...rows.map((r) => r.latency_ms), 0);
  const maxCost = Math.max(...rows.map((r) => r.estimated_cost_usd), 0);
  const maxTokens = Math.max(...rows.map((r) => totalTokens(r)), 0);

  return (
    <section aria-label="Quick compare" className="grid gap-5">
      <p className="text-sm text-(--color-ink-muted)">
        {report.run.brief.decision_question || report.run.brief.task_name}
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        {rows.map((r) => {
          const cand = byId.get(r.candidate_id);
          const picked = pick === r.candidate_id;
          return (
            <article
              key={r.candidate_id}
              className={
                "rounded-xl border p-4 " +
                (picked
                  ? "border-(--color-accent)/50 bg-(--color-accent)/[0.06]"
                  : "border-(--color-panel-line)")
              }
            >
              <div className="flex items-center gap-2">
                <span className="font-semibold text-(--color-ink)">{cand?.label ?? r.candidate_id}</span>
                {cand && <ProviderTag candidate={cand} />}
              </div>
              <p className="mt-2 whitespace-pre-wrap text-sm text-(--color-ink-muted)">
                {r.error ? `error: ${r.error}` : r.output_text || "—"}
              </p>
              <QuickBars row={r} maxLatency={maxLatency} maxCost={maxCost} maxTokens={maxTokens} />
              <button
                type="button"
                aria-pressed={picked}
                onClick={() => setPick(r.candidate_id)}
                className={
                  "mt-3 w-full rounded-lg px-3 py-2 text-sm font-medium transition-colors " +
                  (picked
                    ? "bg-(--color-accent-strong) text-(--color-accent-ink)"
                    : "border border-(--color-panel-line) text-(--color-ink-muted) hover:text-(--color-ink)")
                }
              >
                {cand?.label ?? r.candidate_id} wins
              </button>
            </article>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          aria-pressed={pick === "tie"}
          onClick={() => setPick("tie")}
          className={
            "rounded-lg px-4 py-2 text-sm transition-colors " +
            (pick === "tie"
              ? "bg-(--color-accent-strong) text-(--color-accent-ink)"
              : "border border-(--color-panel-line) text-(--color-ink-muted) hover:text-(--color-ink)")
          }
        >
          Tie
        </button>
        <button
          type="button"
          disabled={pick === null || save.isPending}
          onClick={() => pick && save.mutate(pick)}
          className="rounded-lg bg-(--color-accent-strong) px-5 py-2.5 font-medium text-(--color-accent-ink) transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          {save.isPending ? "Saving…" : "Save as Proof Receipt"}
        </button>
        <button
          type="button"
          onClick={onPromote}
          className="text-sm text-(--color-accent) hover:underline"
        >
          Promote to a full scored run →
        </button>
      </div>
      <p className="text-xs text-(--color-ink-faint)">
        Single-example quick check — not scored proof. Promote to a full scored run for repeatable proof.
      </p>
      {save.isError && (
        <p role="alert" className="text-sm text-(--color-danger)">
          Could not save the pick. Try again.
        </p>
      )}
    </section>
  );
}

function QuickBars({
  row,
  maxLatency,
  maxCost,
  maxTokens,
}: {
  row: ResultRow;
  maxLatency: number;
  maxCost: number;
  maxTokens: number;
}) {
  const bar = (label: string, value: string, frac: number) => (
    <div className="grid grid-cols-[4rem_1fr_auto] items-center gap-2 text-xs tabular-nums text-(--color-ink-faint)">
      <span>{label}</span>
      <span className="h-1.5 rounded-full bg-(--color-panel-line)">
        <span
          className="block h-full rounded-full bg-(--color-ink-faint)"
          style={{ width: `${Math.round(frac * 100)}%` }}
        />
      </span>
      <span>{value}</span>
    </div>
  );
  return (
    <div className="mt-3 grid gap-1.5">
      {bar("latency", `${row.latency_ms}ms`, objectiveBar(row.latency_ms, maxLatency))}
      {bar("cost", `$${row.estimated_cost_usd.toFixed(4)}`, objectiveBar(row.estimated_cost_usd, maxCost))}
      {bar("tokens", String(totalTokens(row)), objectiveBar(totalTokens(row), maxTokens))}
    </div>
  );
}
