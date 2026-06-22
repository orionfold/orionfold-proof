import type { ReactNode } from "react";
import { Cloud, CircleX, FlaskConical, HardDrive, TriangleAlert, type LucideIcon } from "lucide-react";

import type { Candidate, LeaderboardEntry } from "../../lib/api";

// Provider boundary — Local / Cloud / Mock must be distinct at a glance (design system). Each
// gets its own icon as well as color so the privacy boundary reads without relying on hue alone.
// Privacy only knows local/cloud, so a mock candidate is detected by its provider id.
type ProviderKind = "mock" | "local" | "cloud";

function providerKind(providerId: string, privacy: "local" | "cloud"): ProviderKind {
  return providerId.startsWith("mock") ? "mock" : privacy;
}

// Provider boundary is CATEGORICAL IDENTITY, not a control — so every kind wears the same neutral
// token surface (Orionfold rule: identity tags are neutral, non-pressable, never a pill). The
// privacy/kind still reads at a glance because each carries a distinct icon AND label — never hue
// alone. Cyan never appears here (status/identity ≠ accent).
const PROVIDER_STYLE: Record<ProviderKind, { label: string; Icon: LucideIcon }> = {
  mock: { label: "Mock", Icon: FlaskConical },
  local: { label: "Local", Icon: HardDrive },
  cloud: { label: "Cloud", Icon: Cloud },
};

export function ProviderTag({
  candidate,
}: {
  candidate: Pick<Candidate | LeaderboardEntry, "provider_id" | "privacy">;
}) {
  const { label, Icon } = PROVIDER_STYLE[providerKind(candidate.provider_id, candidate.privacy)];
  return (
    <span
      // `rounded` (not a pill): identity tags take the receipt-stub shape so they never read as
      // interactive. Neutral ink-muted on the card surface, distinguished by icon + label.
      className="inline-flex items-center gap-1 rounded border border-(--color-panel-line) bg-(--color-panel-card) px-2 py-0.5 text-[11px] font-medium text-(--color-ink-muted)"
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
