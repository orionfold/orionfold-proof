import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { DatasetImportPanel } from "./DatasetImportPanel";
import { renderWithQuery } from "../../test/renderWithQuery";
import * as api from "../../lib/api";

afterEach(() => vi.restoreAllMocks());

test("paste → preview → freeze calls createDataset and closes", async () => {
  vi.spyOn(api, "previewDataset").mockResolvedValue({
    examples: [{ input_text: "a", expected_text: "b", keypoints: [] }],
    warnings: ["Line 2: not valid JSON — skipped."],
    count: 1,
  });
  vi.spyOn(api, "createDataset").mockResolvedValue({
    id: "my-set",
    name: "My Set",
    description: "",
    examples: [{ input_text: "a", expected_text: "b", keypoints: [] }],
  });
  const onClose = vi.fn();
  renderWithQuery(<DatasetImportPanel onClose={onClose} />);

  fireEvent.change(screen.getByLabelText(/Paste or upload/i), {
    target: { value: '{"input":"a","expected":"b"}' },
  });
  fireEvent.click(screen.getByRole("button", { name: /Preview/i }));

  await waitFor(() => expect(screen.getByText(/1 example/i)).toBeVisible());
  expect(screen.getByText(/not valid JSON/)).toBeVisible();

  fireEvent.change(screen.getByLabelText(/Dataset name/i), { target: { value: "My Set" } });
  fireEvent.click(screen.getByRole("button", { name: /Freeze dataset/i }));

  await waitFor(() => expect(api.createDataset).toHaveBeenCalled());
  await waitFor(() => expect(onClose).toHaveBeenCalled());
});

test("shows the server error when preview fails", async () => {
  vi.spyOn(api, "previewDataset").mockRejectedValue(new Error("No valid examples found."));
  renderWithQuery(<DatasetImportPanel onClose={vi.fn()} />);
  fireEvent.change(screen.getByLabelText(/Paste or upload/i), { target: { value: "junk" } });
  fireEvent.click(screen.getByRole("button", { name: /Preview/i }));
  await waitFor(() => expect(screen.getByText(/No valid examples found/)).toBeVisible());
});
