// Pure per-example shape helpers for the adaptive ExampleCard renderer. No React — unit-tested.
import type { Example } from "../../lib/api";

export type BenchBehavior = "answer" | "route" | "refuse";

// How an expected governance behavior reads. `tone` decides the pill's surface: refuse is a
// caution-class expectation (the model is SUPPOSED to decline), so it earns the one meaningful
// status hue here (warn); answer/route are neutral routing facts. Icon names map to lucide-react.
export interface BehaviorMeta {
  label: string;
  icon: "MessageSquare" | "Signpost" | "ShieldX";
  tone: "neutral" | "warn";
}

const BEHAVIOR_META: Record<BenchBehavior, BehaviorMeta> = {
  answer: { label: "Answer", icon: "MessageSquare", tone: "neutral" },
  route: { label: "Route", icon: "Signpost", tone: "neutral" },
  refuse: { label: "Refuse", icon: "ShieldX", tone: "warn" },
};

// Default to "answer" when a bench row leaves expected_behavior unset (mirrors the backend scorer,
// which grades a null behavior as "answer").
export function behaviorMeta(behavior: Example["expected_behavior"]): BehaviorMeta {
  return BEHAVIOR_META[(behavior ?? "answer") as BenchBehavior] ?? BEHAVIOR_META.answer;
}

// The governance gates a bench row requires, as short chips. Order is fixed (cite · refuse · route)
// so a column of examples reads consistently. Only the flags that are set appear.
export function requirementChips(ex: Example): string[] {
  const chips: string[] = [];
  if (ex.requires_citation) chips.push("cite");
  if (ex.requires_refusal) chips.push("refuse");
  if (ex.requires_route) chips.push("route");
  return chips;
}

// The source ids a bench row expects to see cited. expected_citations must all appear; the
// accepted set is a defensible superset (any one passes). Both are shown as mono id chips.
export function citationIds(ex: Example): { expected: string[]; accepted: string[] } {
  return { expected: ex.expected_citations ?? [], accepted: ex.accepted_source_ids ?? [] };
}
