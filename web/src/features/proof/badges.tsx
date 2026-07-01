import type { ReactNode } from "react";
import {
  Cloud,
  CircleX,
  Dices,
  FlaskConical,
  Lock,
  Repeat2,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";

import type { Candidate, LeaderboardEntry } from "../../lib/api";

// Provider boundary — Local / Cloud / Mock must be distinct at a glance (design system). Each
// gets its own icon as well as color so the privacy boundary reads without relying on hue alone.
// Privacy only knows local/cloud, so a mock candidate is detected by its provider id.
type ProviderKind = "mock" | "local" | "cloud";

function providerKind(providerId: string, privacy: "local" | "cloud"): ProviderKind {
  return providerId.startsWith("mock") ? "mock" : privacy;
}

// Real-provider boundaries (Cloud / Local) are CATEGORICAL IDENTITY, not controls — so they wear
// the neutral token surface (Orionfold rule: identity tags are neutral, non-pressable, never a
// pill). Cloud/Local still read apart via distinct icon + label — never hue alone. Cyan (controls)
// and green (PASS) never appear here.
//
// Mock is different in kind: it marks a SIMULATED candidate (no real evaluation), so per the
// reference kit's `.badge.warn` it carries a quiet warn (caution) tint — simulated ≠ real reads at
// a glance, distinct from the neutral real-provider tags. Warn here means "not a real run," the
// same caution sense as a graded-miss status; it is never green (PASS) or cyan (a control). — WS-F F4
// Neutral receipt-stub surface for the real-provider (Cloud / Local) tags. Mock overrides it
// with its own warn-tinted border/bg below, so the base carries no border/bg of its own (avoids
// a same-property Tailwind conflict with the mock override).
const NEUTRAL_SURFACE = "border-(--color-panel-line) bg-(--color-panel-card)";

const PROVIDER_STYLE: Record<ProviderKind, { label: string; Icon: LucideIcon; cls: string }> = {
  mock: {
    label: "Mock",
    Icon: FlaskConical,
    cls: "border-(--color-warn)/40 bg-(--color-warn)/10 text-(--color-warn)",
  },
  local: { label: "Local", Icon: Lock, cls: `${NEUTRAL_SURFACE} text-(--color-ink) font-semibold` },
  cloud: { label: "Cloud", Icon: Cloud, cls: `${NEUTRAL_SURFACE} text-(--color-ink-muted)` },
};

export function ProviderTag({
  candidate,
}: {
  candidate: Pick<Candidate | LeaderboardEntry, "provider_id" | "privacy">;
}) {
  const { label, Icon, cls } = PROVIDER_STYLE[providerKind(candidate.provider_id, candidate.privacy)];
  return (
    <span
      // `rounded` (not a pill): identity tags take the receipt-stub shape so they never read as
      // interactive. Border/bg + text are all owned by the per-kind `cls` (Cloud/Local share the
      // neutral surface; Mock carries the warn tint), so the kinds never collide on a property.
      className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] font-medium ${cls}`}
    >
      <Icon aria-hidden className="h-3 w-3 shrink-0" />
      {label}
    </span>
  );
}

// Sampling disclosure (cloud-provider-determinism-audit) — HOW a candidate was sampled, so the
// receipt's "repeatable" promise is honest. This is CATEGORICAL IDENTITY/disclosure (like the
// Cloud/Local tags), not a control or a status, so it wears the same neutral surface + receipt-stub
// shape — never the cyan accent (a control) or green ok (PASS). The two modes read apart via icon +
// label, never hue alone: "deterministic" (temperature pinned to 0 → reproducible) vs "sampled"
// (provider defaults → not guaranteed to reproduce). Absent descriptor (mock/errored) renders null.
const SAMPLING_STYLE: Record<
  "deterministic" | "provider_default",
  { label: string; title: string; Icon: LucideIcon }
> = {
  deterministic: {
    label: "Deterministic",
    title: "Temperature pinned to 0 — a re-run reproduces this output (local Ollama).",
    Icon: Repeat2,
  },
  provider_default: {
    label: "Sampled",
    title:
      "Provider default sampling was used — the output is not guaranteed to reproduce exactly (cloud providers).",
    Icon: Dices,
  },
};

export function SamplingTag({
  sampling,
}: {
  sampling: LeaderboardEntry["sampling"];
}) {
  if (!sampling) return null;
  const style = SAMPLING_STYLE[sampling.mode as "deterministic" | "provider_default"];
  if (!style) return null;
  const { label, title, Icon } = style;
  return (
    <span
      title={title}
      // Same neutral receipt-stub shape as the identity tags (rounded, not a pill; neutral surface):
      // disclosure is neither a control nor a PASS, so no accent/ok token appears here.
      className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] font-medium ${NEUTRAL_SURFACE} text-(--color-ink-muted)`}
    >
      <Icon aria-hidden className="h-3 w-3 shrink-0" />
      {label}
    </span>
  );
}

// Failure status — token-driven, never literal hues, never the accent (status ≠ action). The two
// kinds keep distinct tokens AND icons so severity reads without relying on color alone:
//   • error = a hard provider/judge failure (the call broke) → --color-danger (red)
//   • fail  = a graded rubric miss (the model ran but missed) → --color-warn (amber/caution)
// A graded miss is an expected, legitimate outcome here, so it's caution, not alarm.
const STATUS_STYLE: Record<"error" | "fail", { cls: string; Icon: LucideIcon }> = {
  error: {
    cls: "border-(--color-danger)/40 bg-(--color-danger)/10 text-(--color-danger)",
    Icon: CircleX,
  },
  fail: {
    cls: "border-(--color-warn)/40 bg-(--color-warn)/10 text-(--color-warn)",
    Icon: TriangleAlert,
  },
};

export function StatusBadge({ kind, children }: { kind: "error" | "fail"; children: ReactNode }) {
  const { cls, Icon } = STATUS_STYLE[kind];
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 rounded border px-2 py-0.5 text-[11px] ${cls}`}
    >
      <Icon aria-hidden className="h-3 w-3 shrink-0" />
      {children}
    </span>
  );
}
