import type { ProofReport } from "../../lib/api";
import { ProviderTag } from "./badges";
import { buildCostLedger, type CandidateCost } from "./costLedgerMath";

// The full spend picture for a run, per candidate (WS-D2). The leaderboard already
// shows each candidate's "Est. cost" (candidate $ only); this panel adds what that
// can't: judge $, token volume, each candidate's SHARE of the run, and a reconciled
// run total that — by construction — equals the verdict banner's "Run cost" line
// (both roll up the same result rows). FE-only: no backend field, no hash change.
//
// DS: cost is neither a verdict nor a pass signal, so NOTHING here wears the cyan
// accent (recommended/interactive) or green --color-ok (PASS). The share bar is
// neutral ink; $ and token figures are tabular-nums for calm column alignment.

// USD to 4 decimals, matching DecisionSummary's "Run cost" line exactly so the
// numbers reconcile to the penny when an operator compares the two.
const usd = (v: number) => `$${v.toFixed(4)}`;

// Token counts read better grouped (1,234) than raw; compacts large runs (12.3k).
const tokens = (v: number) =>
  v >= 10_000
    ? new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v)
    : new Intl.NumberFormat("en-US").format(v);

function CandidateRow({ c }: { c: CandidateCost }) {
  const pct = Math.round(c.share * 100);
  return (
    <tr className="border-t border-(--color-panel-line)">
      <td className="p-3">{c.label}</td>
      <td className="p-3">
        <ProviderTag candidate={{ provider_id: c.providerId, privacy: c.privacy }} />
      </td>
      <td className="p-3 text-right tabular-nums text-(--color-ink-muted)">
        {tokens(c.inputTokens)} / {tokens(c.outputTokens)}
      </td>
      <td className="p-3 text-right tabular-nums">{usd(c.candidateCostUsd)}</td>
      <td className="p-3 text-right tabular-nums text-(--color-ink-muted)">
        {c.judgeCostUsd > 0 ? usd(c.judgeCostUsd) : "—"}
      </td>
      <td className="p-3">
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-20 shrink-0 overflow-hidden rounded-full bg-(--color-panel-line)">
            <div
              className="h-full rounded-full bg-(--color-ink-muted)"
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="tabular-nums text-(--color-ink-muted)">{pct}%</span>
        </div>
      </td>
    </tr>
  );
}

export function CostLedger({ report }: { report: ProofReport }) {
  const ledger = buildCostLedger(report.leaderboard, report.results);

  // Nothing to itemize on an empty leaderboard (e.g. all-errored before rows land).
  if (ledger.candidates.length === 0) return null;

  const hasJudge = ledger.judgeCostUsd > 0;
  const free = ledger.totalCostUsd === 0;

  return (
    <section aria-label="Run cost" className="w-full">
      <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-(--color-ink-muted)">
        Run cost
      </h2>
      <div className="overflow-x-auto rounded-xl border border-(--color-panel-line)">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="text-left text-(--color-ink-faint)">
              <th className="p-3 font-medium">Candidate</th>
              <th className="p-3 font-medium">Provider</th>
              <th className="p-3 text-right font-medium">Tokens in / out</th>
              <th className="p-3 text-right font-medium">Candidate $</th>
              <th className="p-3 text-right font-medium">Judge $</th>
              <th className="p-3 font-medium">Share</th>
            </tr>
          </thead>
          <tbody>
            {ledger.candidates.map((c) => (
              <CandidateRow key={c.candidateId} c={c} />
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-(--color-panel-line-strong) text-(--color-ink)">
              <td className="p-3 font-medium" colSpan={2}>
                Run total
              </td>
              <td className="p-3 text-right tabular-nums text-(--color-ink-muted)">
                {tokens(ledger.inputTokens)} / {tokens(ledger.outputTokens)}
              </td>
              <td className="p-3 text-right font-medium tabular-nums">
                {usd(ledger.candidateCostUsd)}
              </td>
              <td className="p-3 text-right font-medium tabular-nums text-(--color-ink-muted)">
                {hasJudge ? usd(ledger.judgeCostUsd) : "—"}
              </td>
              <td className="p-3 font-medium tabular-nums" data-testid="run-cost-total">
                {free ? "Free" : usd(ledger.totalCostUsd)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
      {free && (
        <p className="mt-2 text-xs text-(--color-ink-faint)">
          No spend — local or mock providers only.
        </p>
      )}
    </section>
  );
}
