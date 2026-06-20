import type { Candidate, LeaderboardEntry } from "../../lib/api";

// Provider boundary — Local / Cloud / Mock must be distinct at a glance (design system).
// Privacy only knows local/cloud, so a mock candidate is detected by its provider id.
type ProviderKind = "mock" | "local" | "cloud";

function providerKind(providerId: string, privacy: "local" | "cloud"): ProviderKind {
  return providerId.startsWith("mock") ? "mock" : privacy;
}

const PROVIDER_STYLE: Record<ProviderKind, { label: string; cls: string }> = {
  mock: { label: "Mock", cls: "border-zinc-500/40 bg-zinc-500/10 text-zinc-300" },
  local: { label: "Local", cls: "border-slate-400/40 bg-slate-400/10 text-slate-200" },
  cloud: { label: "Cloud", cls: "border-sky-400/40 bg-sky-400/10 text-sky-300" },
};

export function ProviderTag({
  candidate,
}: {
  candidate: Pick<Candidate | LeaderboardEntry, "provider_id" | "privacy">;
}) {
  const { label, cls } = PROVIDER_STYLE[providerKind(candidate.provider_id, candidate.privacy)];
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${cls}`}>
      {label}
    </span>
  );
}
