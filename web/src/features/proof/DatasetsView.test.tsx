import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { DatasetsView } from "./DatasetsView";
import { renderWithQuery } from "../../test/renderWithQuery";
import * as api from "../../lib/api";

afterEach(() => vi.restoreAllMocks());

test("renders tags, metadata, and the derived eval type on a card", async () => {
  vi.spyOn(api, "getDatasets").mockResolvedValue([
    {
      id: "d1",
      name: "Client memos",
      description: "",
      examples: [{ input_text: "i", expected_text: "e", keypoints: [] }],
      tags: ["Legal", "Finance"],
      created_at: "2026-06-22T10:00:00Z",
      source: "file:cases.xlsx",
      check_hint: "substring",
    },
  ]);
  renderWithQuery(<DatasetsView />);
  // Domains/eval-types also appear in the coverage strip, so scope assertions to the card section.
  const card = (await screen.findByText("Client memos")).closest("section")!;
  await waitFor(() => expect(within(card).getByText("Legal")).toBeInTheDocument());
  expect(within(card).getByText("Finance")).toBeInTheDocument();
  // The substring check-hint now reads as the "Contains" eval-type badge (replaces the old chip).
  expect(within(card).getByText("Contains")).toBeInTheDocument();
  expect(within(card).getByText(/cases\.xlsx/)).toBeInTheDocument();
});

test("shows the coverage strip and the governance-bench eval type for a bench dataset", async () => {
  vi.spyOn(api, "getDatasets").mockResolvedValue([
    {
      id: "bench",
      name: "Governance bench",
      description: "",
      examples: [{ input_text: "q", expected_text: "a", keypoints: [], expected_behavior: "refuse", requires_refusal: true }],
      corpus_id: "ainative-field-notes",
      system_prompt: "You are an advisor…",
      tags: ["Governance"],
    },
  ]);
  renderWithQuery(<DatasetsView />);
  // Find the card via its name heading (unique), not the eval label (also in the coverage legend).
  const card = (await screen.findByRole("heading", { name: /Governance bench/i })).closest("section")!;
  // Coverage strip is present (sibling of the card).
  expect(screen.getByLabelText("Dataset library coverage")).toBeInTheDocument();
  // The bench eval type (badge label appears in addition to the name heading) + the corpus/contract
  // metadata chips, scoped to the card.
  expect(within(card).getAllByText("Governance bench").length).toBeGreaterThanOrEqual(1);
  expect(within(card).getByText("corpus")).toBeInTheDocument();
  expect(within(card).getByText("governance contract")).toBeInTheDocument();
});

test("'Run proof →' invokes the run handler with the dataset id", async () => {
  vi.spyOn(api, "getDatasets").mockResolvedValue([
    { id: "d1", name: "Memos", description: "", examples: [{ input_text: "i", expected_text: "e", keypoints: [] }] },
  ]);
  const onRunDataset = vi.fn();
  renderWithQuery(<DatasetsView onRunDataset={onRunDataset} />);
  const link = await screen.findByRole("button", { name: /Run a proof on Memos/i });
  fireEvent.click(link);
  expect(onRunDataset).toHaveBeenCalledWith("d1");
});

test("an exact dataset renders its example with the equality match rule", async () => {
  vi.spyOn(api, "getDatasets").mockResolvedValue([
    {
      id: "triage",
      name: "Triage",
      description: "",
      examples: [{ input_text: "card declined", expected_text: "billing", keypoints: [] }],
      check_hint: "exact",
    },
  ]);
  renderWithQuery(<DatasetsView />);
  const card = (await screen.findByText("Triage")).closest("section")!;
  expect(within(card).getByText("Exact match")).toBeInTheDocument();
  expect(within(card).getByText(/must equal/)).toBeInTheDocument();
  expect(within(card).getByText("billing")).toBeInTheDocument();
});
