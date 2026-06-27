import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HostPanel } from "./HostPanel";

const profile = {
  arch: "arm64",
  chip: "Apple M3 Max",
  cpu_cores: 14,
  memory_gb: 36,
  os_label: "macOS 15.1",
  local_runtime: "Ollama",
  gpu_label: "Apple M3 Max GPU",
};

describe("HostPanel", () => {
  it("shows the chip, unified memory, and runtime", () => {
    render(<HostPanel profile={profile} telemetry={null} />);
    // "Apple M3 Max" appears in both the chip row and the GPU label ("… GPU") — both are correct.
    expect(screen.getAllByText(/Apple M3 Max/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/36 GB/)).toBeInTheDocument();
    expect(screen.getByText(/Ollama/)).toBeInTheDocument();
  });

  it("renders an honest fallback when a field is unavailable", () => {
    render(<HostPanel profile={{ ...profile, chip: null, local_runtime: null }} telemetry={null} />);
    // arch still shows in place of a missing chip; no crash on nulls.
    expect(screen.getByText(/arm64/)).toBeInTheDocument();
    expect(screen.getByText(/cloud only/)).toBeInTheDocument();
  });

  it("asserts the trust story and shows at-rest gauges when idle", () => {
    render(<HostPanel profile={profile} telemetry={null} />);
    expect(screen.getByText(/this proof runs here/i)).toBeInTheDocument();
    expect(screen.getByText(/Private · on this machine/i)).toBeInTheDocument();
    // The gauge geometry is present even idle, labeled "at rest" (never a fake live 0%).
    expect(screen.getAllByText(/at rest/i).length).toBe(2);
  });

  it("shows live gauges with real readings during a run", () => {
    render(
      <HostPanel
        profile={profile}
        telemetry={{ cpu_util: 47, mem_used_gb: 24.2, process_rss_gb: 5.1, gpu_util: null }}
      />,
    );
    expect(screen.getByText(/47%/)).toBeInTheDocument(); // CPU gauge reading
    expect(screen.getByText(/5.1 GB/)).toBeInTheDocument(); // runtime RSS (the fixed sampling)
    // No "at rest" placeholder once live.
    expect(screen.queryByText(/at rest/i)).not.toBeInTheDocument();
  });
});
