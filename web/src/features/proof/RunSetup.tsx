import type { Candidate, Dataset, ProofBrief } from "../../lib/api";

// The setup is deliberately small: pick a dataset, pick candidates, frame the decision, run.
// A Proof Brief (not a wizard in v0) keeps the receipt anchored to a real decision.
export interface RunSetupProps {
  datasets: Dataset[];
  candidates: Candidate[];
  datasetId: string;
  onDatasetChange: (id: string) => void;
  selectedCandidates: string[];
  onToggleCandidate: (id: string) => void;
  brief: ProofBrief;
  onBriefChange: (brief: ProofBrief) => void;
  onRun: () => void;
  isRunning: boolean;
  error: string | null;
}

export function RunSetup(props: RunSetupProps) {
  const {
    datasets,
    candidates,
    datasetId,
    onDatasetChange,
    selectedCandidates,
    onToggleCandidate,
    brief,
    onBriefChange,
    onRun,
    isRunning,
    error,
  } = props;

  const canRun = selectedCandidates.length > 0 && brief.task_name.trim().length > 0;

  return (
    <form
      aria-label="Proof setup"
      className="w-full rounded-xl border border-[--color-panel-line] bg-[--color-panel-card] p-6"
      onSubmit={(e) => {
        e.preventDefault();
        if (canRun && !isRunning) onRun();
      }}
    >
      <div className="grid gap-5">
        <label className="grid gap-1.5 text-sm">
          <span className="text-[--color-ink-muted]">Dataset</span>
          <select
            value={datasetId}
            onChange={(e) => onDatasetChange(e.target.value)}
            className="rounded-lg border border-[--color-panel-line] bg-[--color-panel] px-3 py-2 text-[--color-ink]"
          >
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.examples.length} examples)
              </option>
            ))}
          </select>
        </label>

        <fieldset className="grid gap-2 text-sm">
          <legend className="text-[--color-ink-muted]">Candidates</legend>
          <div className="flex flex-wrap gap-2">
            {candidates.map((c) => {
              const checked = selectedCandidates.includes(c.id);
              return (
                <label
                  key={c.id}
                  className={
                    "flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 " +
                    (checked
                      ? "border-emerald-400 bg-emerald-500/10"
                      : "border-[--color-panel-line]")
                  }
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => onToggleCandidate(c.id)}
                    className="accent-emerald-400"
                  />
                  <span className="text-[--color-ink]">{c.label}</span>
                  <span className="text-xs text-[--color-ink-muted]">{c.privacy}</span>
                </label>
              );
            })}
          </div>
        </fieldset>

        <label className="grid gap-1.5 text-sm">
          <span className="text-[--color-ink-muted]">Task name</span>
          <input
            value={brief.task_name}
            onChange={(e) => onBriefChange({ ...brief, task_name: e.target.value })}
            className="rounded-lg border border-[--color-panel-line] bg-[--color-panel] px-3 py-2 text-[--color-ink]"
          />
        </label>

        <label className="grid gap-1.5 text-sm">
          <span className="text-[--color-ink-muted]">Decision question</span>
          <input
            value={brief.decision_question}
            onChange={(e) => onBriefChange({ ...brief, decision_question: e.target.value })}
            className="rounded-lg border border-[--color-panel-line] bg-[--color-panel] px-3 py-2 text-[--color-ink]"
          />
        </label>

        {error && <p className="text-sm text-rose-300">{error}</p>}

        <div>
          <button
            type="submit"
            disabled={!canRun || isRunning}
            className="rounded-lg bg-emerald-500 px-5 py-2.5 font-medium text-emerald-950 transition-opacity disabled:opacity-40"
          >
            {isRunning ? "Running proof…" : "Run proof"}
          </button>
        </div>
      </div>
    </form>
  );
}
