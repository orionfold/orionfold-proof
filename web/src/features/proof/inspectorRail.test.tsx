import { act, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { InspectorRail } from "./InspectorRail";
import * as api from "../../lib/api";

const HOST = {
  arch: "arm64",
  chip: "Apple M3 Max",
  cpu_cores: 14,
  memory_gb: 36,
  os_label: "macOS 15.1",
  local_runtime: "Ollama",
  gpu_label: "Apple M3 Max GPU",
};

// Captured per render so a test can push a live sample through the subscription the rail opens.
let onSample: ((s: api.TelemetrySample) => void) | null = null;
let unsubscribe: ReturnType<typeof vi.fn>;

function renderRail(runActive: boolean) {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <InspectorRail runDetail={null} runActive={runActive} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.spyOn(api, "getHostProfile").mockResolvedValue(HOST);
  unsubscribe = vi.fn();
  onSample = null;
  vi.spyOn(api, "subscribeTelemetry").mockImplementation((cb) => {
    onSample = cb;
    return unsubscribe;
  });
});

afterEach(() => vi.restoreAllMocks());

describe("InspectorRail live-gauge wiring", () => {
  it("does NOT subscribe to telemetry when no run is active", () => {
    renderRail(false);
    expect(api.subscribeTelemetry).not.toHaveBeenCalled();
  });

  it("subscribes and renders live gauges WHILE a run is active (the mid-run regression guard)", async () => {
    renderRail(true);
    expect(api.subscribeTelemetry).toHaveBeenCalledTimes(1);
    // Push a live sample as the stream would; the gauge reading must render.
    expect(onSample).toBeTypeOf("function");
    act(() => onSample?.({ cpu_util: 63, mem_used_gb: 24, process_rss_gb: 5.1, gpu_util: null }));
    expect(await screen.findByText(/63%/)).toBeInTheDocument();
    expect(screen.getByText(/5.1 GB/)).toBeInTheDocument();
  });

  it("tears down the subscription when the run ends", () => {
    const { rerender } = renderRail(true);
    const client = new QueryClient();
    rerender(
      <QueryClientProvider client={client}>
        <InspectorRail runDetail={null} runActive={false} />
      </QueryClientProvider>,
    );
    expect(unsubscribe).toHaveBeenCalled();
  });
});
