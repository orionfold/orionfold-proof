// Shared display helpers for provider health, so the run-setup picker and the Candidates view
// render identical badges and tooltips. Health is a liveness signal orthogonal to key presence:
// a provider can have a key (available) yet be unhealthy (revoked key → auth, billing → quota).
import { TriangleAlert, CircleX } from "lucide-react";

import type { ProviderHealth, ProviderHealthPanel, ProviderHealthStatus } from "../../lib/api";

// Short chip label per status. "ok" never renders a badge.
const HEALTH_LABEL: Record<ProviderHealthStatus, string> = {
  ok: "OK",
  auth: "Auth failed",
  permission: "No access",
  quota: "Quota / rate limit",
  down: "Provider down",
  unreachable: "Unreachable",
};

// auth/permission/quota/down are hard failures (red); unreachable (local server off, network
// blip) is caution-toned (amber) — recoverable by starting a server or retrying.
const HEALTH_TONE: Record<ProviderHealthStatus, "error" | "warn"> = {
  ok: "warn",
  auth: "error",
  permission: "error",
  quota: "error",
  down: "error",
  unreachable: "warn",
};

const TONE_CLS = {
  error: "border-(--color-danger)/40 bg-(--color-danger)/10 text-(--color-danger)",
  warn: "border-(--color-warn)/40 bg-(--color-warn)/10 text-(--color-warn)",
} as const;

export function healthOk(h: ProviderHealth | undefined): boolean {
  // Treat "no probe result yet" as ok so the render-first/probe-async path doesn't flicker
  // every provider into a disabled state before the probe returns.
  return h === undefined || h.status === "ok";
}

/** Index a health panel by provider_id for O(1) per-row lookup. */
export function healthByProvider(
  panel: ProviderHealthPanel | undefined,
): Map<string, ProviderHealth> {
  const map = new Map<string, ProviderHealth>();
  if (panel) for (const h of panel.providers) map.set(h.provider_id, h);
  return map;
}

/** A compact status badge with the provider's failure reason as a tooltip. Renders null for ok. */
export function ProviderHealthBadge({ health }: { health: ProviderHealth | undefined }) {
  if (!health || health.status === "ok") return null;
  const tone = HEALTH_TONE[health.status];
  const Icon = tone === "error" ? CircleX : TriangleAlert;
  return (
    <span
      title={`${health.message}\n${health.remediation}`}
      className={`inline-flex shrink-0 items-center gap-1 rounded border px-2 py-0.5 text-[11px] ${TONE_CLS[tone]}`}
    >
      <Icon aria-hidden className="h-3 w-3 shrink-0" />
      {HEALTH_LABEL[health.status]}
    </span>
  );
}

/** The one-line remediation, shown inline under an unhealthy provider's chips. */
export function HealthRemediation({ health }: { health: ProviderHealth | undefined }) {
  if (!health || health.status === "ok") return null;
  return <span className="self-center text-xs text-(--color-ink-faint)">{health.remediation}</span>;
}
