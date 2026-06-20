import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { ReceiptDetailView } from "./ReceiptDetailView";
import { SAMPLE_REPORT } from "../../test/fixtures";

test("renders the receipt artifact in a sandboxed iframe with downloads", () => {
  render(<ReceiptDetailView report={SAMPLE_REPORT} onBack={() => {}} onExplore={() => {}} />);

  const frame = screen.getByTitle("Proof Receipt preview");
  expect(frame).toHaveAttribute("src", "/api/runs/run_abc123def456/receipt.html?inline=1");
  expect(frame).toHaveAttribute("sandbox");

  for (const label of ["Markdown", "HTML", "JSON"]) {
    expect(screen.getByRole("link", { name: label })).toHaveAttribute(
      "href",
      expect.stringContaining("/api/runs/run_abc123def456/receipt."),
    );
  }
});

test("fires onExplore and onBack from the nav buttons", () => {
  const onBack = vi.fn();
  const onExplore = vi.fn();
  render(<ReceiptDetailView report={SAMPLE_REPORT} onBack={onBack} onExplore={onExplore} />);

  fireEvent.click(screen.getByRole("button", { name: /Explore in cockpit/ }));
  expect(onExplore).toHaveBeenCalledWith(SAMPLE_REPORT);

  fireEvent.click(screen.getByRole("button", { name: /Receipts/ }));
  expect(onBack).toHaveBeenCalled();
});
