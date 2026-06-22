import { screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { DatasetsView } from "./DatasetsView";
import { renderWithQuery } from "../../test/renderWithQuery";
import * as api from "../../lib/api";

afterEach(() => vi.restoreAllMocks());

test("renders tags, metadata, and the check hint on a card", async () => {
  vi.spyOn(api, "getDatasets").mockResolvedValue([
    {
      id: "d1",
      name: "Client memos",
      description: "",
      examples: [],
      tags: ["Legal", "Finance"],
      created_at: "2026-06-22T10:00:00Z",
      source: "file:cases.xlsx",
      check_hint: "substring",
    },
  ]);
  renderWithQuery(<DatasetsView />);
  expect(await screen.findByText("Client memos")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText("Legal")).toBeInTheDocument());
  expect(screen.getByText("Finance")).toBeInTheDocument();
  expect(screen.getByText(/Contains text/)).toBeInTheDocument();
  expect(screen.getByText(/cases\.xlsx/)).toBeInTheDocument();
});
