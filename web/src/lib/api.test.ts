import { afterEach, expect, test, vi } from "vitest";

import { createDataset, previewDataset } from "./api";

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
