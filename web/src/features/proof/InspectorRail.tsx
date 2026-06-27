import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { getHostProfile, subscribeTelemetry, type TelemetrySample } from "../../lib/api";
import { HostPanel } from "./HostPanel";

// The app-level right rail: a single scrollable 22rem column present on EVERY screen, so the
// right side is never dead whitespace. The Host card is the permanent base tenant; `runDetail`
// (the cockpit's FINISHED-run inspector) stacks ABOVE it once a run completes. `runActive` is the
// separate live-run signal that drives the gauges — it is true DURING the run, when `runDetail`
// is still null (the report only exists after the run ends), so the gauges light up exactly while
// the hardware is under load. Hidden below lg, the same breakpoint the left rail-nav uses.
export function InspectorRail({
  runDetail,
  runActive,
}: {
  runDetail: React.ReactNode;
  runActive: boolean;
}) {
  const { data: profile } = useQuery({
    queryKey: ["telemetry-host"],
    queryFn: getHostProfile,
    staleTime: Infinity,
  });
  // Live telemetry only while a run is active. The stream self-closes when the run ends; we also
  // unsubscribe on cleanup and clear the last sample so gauges don't linger after completion.
  const [sample, setSample] = useState<TelemetrySample | null>(null);
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
      // Pins to the viewport on desktop, mirroring the left nav rail (sticky + full screen
      // height + internal scroll). Without this the rail flowed with page height, so a tall
      // post-run Inspector pushed the always-on Host card ~2000px down the page. Now the rail is
      // its own fixed-height pane: the Host card is one short in-rail scroll away, never buried.
      className="hidden w-[22rem] flex-col overflow-y-auto bg-(--color-inspector) lg:sticky lg:top-0 lg:flex lg:h-screen"
    >
      {runDetail}
      <HostPanel profile={profile} telemetry={sample} />
    </aside>
  );
}
