// A single scoring-method card: title, one-line guidance, and a cost chip. Selection mirrors the
// accent pattern used by CandidatePicker chips.
export interface MethodCardProps {
  title: string;
  guidance: string;
  cost: string;
  selected: boolean;
  onSelect: () => void;
}

// flex-col + h-full lets every card stretch to the tallest in its grid row; mt-auto pins the
// cost chip to the bottom so the chips line up regardless of how the guidance wraps. text-balance
// evens the guidance across lines so the cards read as a balanced set.
const base = "flex h-full flex-col gap-1 rounded-lg border p-3 text-left text-sm transition-colors";
const active = "border-(--color-accent)/50 bg-(--color-accent)/10";
const idle = "border-(--color-panel-line) hover:border-(--color-panel-line-strong)";

export function MethodCard({ title, guidance, cost, selected, onSelect }: MethodCardProps) {
  return (
    <button type="button" aria-label={`${title} — ${cost}`} aria-pressed={selected} onClick={onSelect} className={`${base} ${selected ? active : idle}`}>
      <span className="font-medium text-(--color-ink)">{title}</span>
      <span className="text-xs text-balance text-(--color-ink-muted)">{guidance}</span>
      <span className="mt-auto pt-1 text-xs text-(--color-ink-faint)">{cost}</span>
    </button>
  );
}
