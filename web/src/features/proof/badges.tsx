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

const PROVIDER_STYLE: Record<ProviderKind, { label: string; cls: string; Icon: LucideIcon }> = {
  mock: { label: "Mock", cls: "border-zinc-500/40 bg-zinc-500/10 text-zinc-300", Icon: FlaskConical },
  local: { label: "Local", cls: "border-slate-400/40 bg-slate-400/10 text-slate-200", Icon: HardDrive },
  cloud: { label: "Cloud", cls: "border-sky-400/40 bg-sky-400/10 text-sky-300", Icon: Cloud },
};

export function ProviderTag({
  candidate,
}: {
  candidate: Pick<Candidate | LeaderboardEntry, "provider_id" | "privacy">;
}) {
  const { label, cls, Icon } = PROVIDER_STYLE[providerKind(candidate.provider_id, candidate.privacy)];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${cls}`}
    >
      <Icon aria-hidden className="h-3 w-3 shrink-0" />
      {label}
    </span>
  );
}

// Failure status — an outright provider error vs. a graded miss. Icon + color + text together so
// the severity reads at a glance and never depends on color alone.
const STATUS_STYLE: Record<"error" | "fail", { cls: string; Icon: LucideIcon }> = {
  error: { cls: "border-rose-400/40 bg-rose-500/10 text-rose-300", Icon: CircleX },
  fail: { cls: "border-amber-400/40 bg-amber-500/10 text-amber-300", Icon: TriangleAlert },
};

export function StatusBadge({ kind, children }: { kind: "error" | "fail"; children: ReactNode }) {
  const { cls, Icon } = STATUS_STYLE[kind];
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] ${cls}`}
    >
      <Icon aria-hidden className="h-3 w-3 shrink-0" />
      {children}
    </span>
  );
}
