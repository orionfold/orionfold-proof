import type { RunProgressEvent, RunStartEvent } from "../../lib/api";

// Live run progress derived purely from the run SSE events. The cockpit already owns the single
// `createRunStream` subscription, so this is a PURE REDUCER it folds events into (not a second
// stream + its own EventSource, which the plan's literal wording implied — that would open a
// duplicate connection and race the cockpit's). The cockpit lifts the resulting snapshot to App,
// which hands it to the telemetry rail. FE-only: no backend change (spec §5).

export interface RunProgress {
  candidatesTotal: number;
  candidatesDone: number;
  examplesTotal: number;
  examplesDone: number;
  // Pooled pass-rate over all completed examples so far, or null when nothing is scored yet
  // (honest "—", never a fake 0%).
  passRateSoFar: number | null;
  // Per-candidate set of reported example indices, so a re-sent cell never double-counts and a
  // candidate is "done" only once all its examples report.
  _cells: Record<string, Set<number>>;
  _passes: number;
  _perCandidateExamples: number; // n_examples per candidate (from start)
}

export function emptyRunProgress(): RunProgress {
  return {
    candidatesTotal: 0,
    candidatesDone: 0,
    examplesTotal: 0,
    examplesDone: 0,
    passRateSoFar: null,
    _cells: {},
    _passes: 0,
    _perCandidateExamples: 0,
  };
}

export function reduceRunProgress(
  state: RunProgress,
  event: RunStartEvent | RunProgressEvent,
): RunProgress {
  if (event.type === "start") {
    return {
      ...emptyRunProgress(),
      candidatesTotal: event.candidates.length,
      examplesTotal: event.total,
      _perCandidateExamples: event.n_examples,
    };
  }

  // progress event — record this (candidate, example) cell once.
  const seen = state._cells[event.candidate_id] ?? new Set<number>();
  if (seen.has(event.example_index)) return state; // idempotent on a repeated cell

  const cells = { ...state._cells, [event.candidate_id]: new Set(seen).add(event.example_index) };
  const examplesDone = state.examplesDone + 1;
  const passes = state._passes + (event.passed ? 1 : 0);
  const passRateSoFar = examplesDone > 0 ? passes / examplesDone : null;

  // A candidate is done once it has reported all its examples. Guard against per==0 (no start yet)
  // so a stray progress before start doesn't divide by zero.
  const per = state._perCandidateExamples;
  const candidatesDone =
    per > 0
      ? Object.values(cells).filter((s) => s.size >= per).length
      : state.candidatesDone;

  return {
    ...state,
    candidatesDone,
    examplesDone,
    passRateSoFar,
    _cells: cells,
    _passes: passes,
  };
}
