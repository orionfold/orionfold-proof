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
});
