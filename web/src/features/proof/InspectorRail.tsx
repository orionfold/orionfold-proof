import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { getHostProfile, subscribeTelemetry, type TelemetrySample } from "../../lib/api";
import { HostPanel } from "./HostPanel";

// The app-level right rail: a single scrollable 22rem column present on EVERY screen, so the
// right side is never dead whitespace. The Host card is the permanent base tenant; `runDetail`
// (the cockpit's run inspector) stacks ABOVE it only when a run is active. Hidden below lg, the
// same breakpoint the left rail-nav uses.
export function InspectorRail({ runDetail }: { runDetail: React.ReactNode }) {
  const { data: profile } = useQuery({
    queryKey: ["telemetry-host"],
    queryFn: getHostProfile,
    staleTime: Infinity,
  });
  // Live telemetry only while a run is active (runDetail present). The stream self-closes when the
  // run ends; we also unsubscribe on cleanup and clear the last sample so gauges don't linger.
  const [sample, setSample] = useState<TelemetrySample | null>(null);
  const runActive = runDetail != null;
  useEffect(() => {
    if (!runActive) {
      setSample(null);
      return;
    }
    // Clear gauges when the stream closes (run finished) so a completed run doesn't freeze a stale
    // reading; the static Host profile remains.
    const unsubscribe = subscribeTelemetry(setSample, () => setSample(null));
    return () => {
      unsubscribe();
      setSample(null);
    };
  }, [runActive]);
  return (
    <aside
      aria-label="Inspector rail"
      className="hidden w-[22rem] flex-col overflow-y-auto bg-(--color-inspector) lg:flex"
    >
      {runDetail}
      <HostPanel profile={profile} telemetry={sample} />
    </aside>
  );
}
