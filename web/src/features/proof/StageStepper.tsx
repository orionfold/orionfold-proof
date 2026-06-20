import { Check } from "lucide-react";

// A quiet map of the loop so a newcomer always knows where they are and what's next:
// Configure the run → Run it → Decide from the receipt. Calm, never a wizard.
const STEPS = [
  { id: "configure", label: "Configure" },
  { id: "run", label: "Run" },
  { id: "decide", label: "Decide" },
] as const;

export type Stage = (typeof STEPS)[number]["id"];

export function StageStepper({ stage }: { stage: Stage }) {
  const currentIndex = STEPS.findIndex((s) => s.id === stage);
  return (
    <ol aria-label="Where you are" className="flex items-center gap-1 text-xs">
      {STEPS.map((s, i) => {
        const state = i < currentIndex ? "done" : i === currentIndex ? "current" : "upcoming";
        return (
          <li key={s.id} className="flex items-center gap-1">
            <span
              aria-current={state === "current" ? "step" : undefined}
              className={
                "flex items-center gap-1.5 rounded-full px-2 py-0.5 " +
                (state === "current"
                  ? "bg-(--color-accent)/15 font-medium text-(--color-accent)"
                  : state === "done"
                    ? "text-(--color-ink-muted)"
                    : "text-(--color-ink-faint)")
              }
            >
              <span
                aria-hidden
                className={
                  "flex h-4 w-4 items-center justify-center rounded-full text-[10px] " +
                  (state === "current"
                    ? "bg-(--color-accent) text-(--color-accent-ink)"
                    : state === "done"
                      ? "bg-(--color-panel-line-strong) text-(--color-ink)"
                      : "border border-(--color-panel-line)")
                }
              >
                {state === "done" ? <Check className="h-2.5 w-2.5" /> : i + 1}
              </span>
              {s.label}
            </span>
            {i < STEPS.length - 1 && <span aria-hidden className="h-px w-5 bg-(--color-panel-line)" />}
          </li>
        );
      })}
    </ol>
  );
}
