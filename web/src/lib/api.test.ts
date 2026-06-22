import { afterEach, describe, expect, it, test, vi } from "vitest";

import {
  createDataset,
  getSettings,
  previewDataset,
  proofReportSchema,
  rubricSchema,
  scoredByLabel,
  seedSampleData,
  setSandbox,
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
  it("getSettings parses sandbox_enabled", async () => {
    mockResponse({ sandbox_enabled: true });
    expect(await getSettings()).toEqual({ sandbox_enabled: true });
  });

  it("setSandbox PUTs the flag", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify({ sandbox_enabled: false }), { status: 200 }));
    await setSandbox(false);
    expect(spy).toHaveBeenCalledWith("/api/settings", expect.objectContaining({ method: "PUT" }));
  });

  it("seedSampleData parses counts", async () => {
    mockResponse({ datasets: 1, receipts: 1 });
    expect(await seedSampleData()).toEqual({ datasets: 1, receipts: 1 });
  });
});
