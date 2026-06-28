import { afterEach, describe, expect, it, test, vi } from "vitest";

import {
  costRollupSchema,
  createDataset,
  datasetSchema,
  extractResultSchema,
  getCostSummary,
  getGpuIdle,
  getGpuSetupStatus,
  getLatestRun,
  getSettings,
  previewDataset,
  proofReportSchema,
  rubricSchema,
  scoredByLabel,
  seedSampleData,
  setMaxRetries,
  setSandbox,
  setThresholds,
} from "./api";
import { SAMPLE_REPORT } from "../test/fixtures";

afterEach(() => vi.restoreAllMocks());

function mockResponse(body: unknown, status = 200) {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(body), { status }),
  );
}

test("previewDataset returns the validated ParseResult", async () => {
  mockResponse({ examples: [{ input_text: "a", expected_text: "b" }], warnings: ["w"], count: 1 });
  const r = await previewDataset({ format: "jsonl", text: '{"input":"a","expected":"b"}' });
  expect(r.count).toBe(1);
  expect(r.warnings).toEqual(["w"]);
});

test("createDataset surfaces the server detail on error", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "A dataset named 'X' already exists." }), { status: 409 }),
  );
  await expect(
    createDataset({ name: "X", format: "jsonl", text: '{"input":"a","expected":"b"}' }),
  ).rejects.toThrow(/already exists/);
});

describe("scoring schemas", () => {
  it("rubric accepts keypoint and judge kinds", () => {
    expect(rubricSchema.parse({ kind: "keypoint", threshold: 0.8, case_sensitive: false }).kind).toBe("keypoint");
    expect(rubricSchema.parse({ kind: "judge", threshold: 0.8, case_sensitive: false, judge_provider_id: "mock_judge", judge_model: null }).judge_provider_id).toBe("mock_judge");
  });

  it("report carries a cost_summary", () => {
    const r = proofReportSchema.parse(SAMPLE_REPORT);
    expect(r.cost_summary.total_cost_usd).toBeGreaterThanOrEqual(0);
  });

  it("scoredByLabel maps kinds", () => {
    expect(scoredByLabel({ kind: "keypoint", threshold: 0.8, case_sensitive: false })).toBe("Keypoint coverage");
    expect(scoredByLabel({ kind: "judge", threshold: 0.8, case_sensitive: false, judge_model: "claude-haiku-4-5", judge_provider_id: "anthropic" })).toContain("claude-haiku-4-5");
  });
});

describe("settings + sample-data client", () => {
  const THRESHOLDS = { similarity: 0.55, keypoint: 0.8, judge: 0.8 };

  it("getSettings parses sandbox_enabled, retries, and thresholds", async () => {
    mockResponse({ sandbox_enabled: true, powermetrics_gpu_optin: false, provider_max_retries: 2, thresholds: THRESHOLDS });
    expect(await getSettings()).toEqual({ sandbox_enabled: true, powermetrics_gpu_optin: false, provider_max_retries: 2, thresholds: THRESHOLDS });
  });

  it("setMaxRetries PUTs a retries-only body", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(
          JSON.stringify({ sandbox_enabled: false, powermetrics_gpu_optin: false, provider_max_retries: 3, thresholds: THRESHOLDS }),
          { status: 200 },
        ),
      );
    await setMaxRetries(3);
    const body = JSON.parse((spy.mock.calls[0][1] as RequestInit).body as string);
    expect(body).toEqual({ provider_max_retries: 3 });
  });

  it("setSandbox PUTs the flag", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(
          JSON.stringify({ sandbox_enabled: false, powermetrics_gpu_optin: false, provider_max_retries: 2, thresholds: THRESHOLDS }),
          { status: 200 },
        ),
      );
    await setSandbox(false);
    expect(spy).toHaveBeenCalledWith("/api/settings", expect.objectContaining({ method: "PUT" }));
  });

  it("setThresholds PUTs a thresholds-only body", async () => {
    const next = { similarity: 0.4, keypoint: 0.8, judge: 0.8 };
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(
          JSON.stringify({ sandbox_enabled: false, powermetrics_gpu_optin: false, provider_max_retries: 2, thresholds: next }),
          { status: 200 },
        ),
      );
    await setThresholds(next);
    const body = JSON.parse((spy.mock.calls[0][1] as RequestInit).body as string);
    expect(body).toEqual({ thresholds: next });
  });

  it("seedSampleData parses counts", async () => {
    mockResponse({ datasets: 1, receipts: 1 });
    expect(await seedSampleData()).toEqual({ datasets: 1, receipts: 1 });
  });
});

describe("cost summary client", () => {
  const ROLLUP = {
    window: "today",
    run_count: 2,
    eval_cost_usd: 0.34,
    judge_cost_usd: 0.02,
    total_cost_usd: 0.36,
    trend: [
      { run_id: "r1", created_at: "2026-06-27T10:00:00Z", total_cost_usd: 0.1, pass_rate: 0.8 },
      { run_id: "r2", created_at: "2026-06-27T11:00:00Z", total_cost_usd: 0.26, pass_rate: 0.9 },
    ],
  };

  it("costRollupSchema parses the eval/judge split + trend", () => {
    const r = costRollupSchema.parse(ROLLUP);
    expect(r.window).toBe("today");
    expect(r.total_cost_usd).toBe(0.36);
    expect(r.trend.map((p) => p.run_id)).toEqual(["r1", "r2"]);
  });

  it("getCostSummary requests the window and returns the validated rollup", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify(ROLLUP), { status: 200 }));
    const r = await getCostSummary("today");
    expect(spy).toHaveBeenCalledWith("/api/cost-summary?window=today");
    expect(r.eval_cost_usd).toBe(0.34);
    expect(r.judge_cost_usd).toBe(0.02);
  });
});

describe("latest-run client (rail at-rest hydrate)", () => {
  it("getLatestRun requests /api/runs/latest and validates the report", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify(SAMPLE_REPORT), { status: 200 }));
    const r = await getLatestRun();
    expect(spy).toHaveBeenCalledWith("/api/runs/latest");
    expect(r?.run.id).toBe(SAMPLE_REPORT.run.id);
  });

  it("getLatestRun returns null when there are no stored runs", async () => {
    mockResponse(null);
    const r = await getLatestRun();
    expect(r).toBeNull();
  });
});

describe("gpu-idle client (rail at-rest GPU read)", () => {
  it("getGpuIdle requests /api/telemetry/gpu-idle and returns the reading", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify({ gpu_util: 20.7 }), { status: 200 }));
    const r = await getGpuIdle();
    expect(spy).toHaveBeenCalledWith("/api/telemetry/gpu-idle");
    expect(r.gpu_util).toBe(20.7);
  });

  it("getGpuIdle parses a null reading (opt-in off / unavailable)", async () => {
    mockResponse({ gpu_util: null });
    const r = await getGpuIdle();
    expect(r.gpu_util).toBeNull();
  });
});

describe("gpu-setup client (Settings ready / needs-setup badge)", () => {
  it("getGpuSetupStatus requests /api/telemetry/gpu-setup and returns the flags", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify({ supported: true, opt_in: true, reachable: false }), {
          status: 200,
        }),
      );
    const r = await getGpuSetupStatus();
    expect(spy).toHaveBeenCalledWith("/api/telemetry/gpu-setup");
    expect(r).toEqual({ supported: true, opt_in: true, reachable: false });
  });
});

describe("dataset metadata schemas", () => {
  it("datasetSchema accepts metadata and stays loose when absent", () => {
    const d = datasetSchema.parse({
      id: "x",
      name: "n",
      description: "",
      examples: [],
      tags: ["Legal"],
      created_at: "2026-06-22T00:00:00Z",
      source: "pasted",
      check_hint: "substring",
    });
    expect(d.tags).toEqual(["Legal"]);
    expect(d.check_hint).toBe("substring");
    // Absent metadata parses fine (loose for fixtures).
    const bare = datasetSchema.parse({ id: "y", name: "n", description: "", examples: [] });
    expect(bare.tags).toBeUndefined();
  });

  it("extractResultSchema parses an extract response", () => {
    const r = extractResultSchema.parse({
      format: "csv",
      text: "input,expected\na,b",
      warnings: [],
    });
    expect(r.format).toBe("csv");
  });
});
