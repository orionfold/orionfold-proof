import { useQuery } from "@tanstack/react-query";

import { getHostProfile } from "../../lib/api";
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
  return (
    <aside
      aria-label="Inspector rail"
      className="hidden w-[22rem] flex-col overflow-y-auto bg-(--color-inspector) lg:flex"
    >
      {runDetail}
      <HostPanel profile={profile} telemetry={null} />
    </aside>
  );
}
