import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { CandidatePicker } from "./CandidatePicker";
import type { SelectionPanel } from "../../lib/api";

const PANEL: SelectionPanel = {
  providers: [
    {
      provider_id: "mock_good",
      label: "Mock · good",
      privacy: "local",
      available: true,
      supports_custom: false,
      candidate_id: "mock_good",
      models: [],
    },
    {
      provider_id: "anthropic",
      label: "Anthropic",
      privacy: "cloud",
      available: false,
      supports_custom: true,
      candidate_id: null,
      models: [
        { candidate_id: "anthropic:claude-haiku-4-5", model: "claude-haiku-4-5", display_name: "Claude Haiku 4.5", tier: "economy", cost_class: "$", context_window: 200000, latest: false, recommended: true },
      ],
    },
    {
      provider_id: "ollama",
      label: "Ollama",
      privacy: "local",
      available: true,
      supports_custom: true,
      candidate_id: null,
      models: [
        { candidate_id: "ollama:llama3.2", model: "llama3.2", display_name: "Llama 3.2", tier: "balanced", cost_class: "free", context_window: 8192, latest: true, recommended: true },
      ],
    },
  ],
};

test("renders a mock chip and provider model chips", () => {
  render(<CandidatePicker panel={PANEL} selected={["mock_good"]} onToggle={vi.fn()} />);
  expect(screen.getByRole("checkbox", { name: "Mock · good" })).toBeChecked();
  expect(screen.getByText("Claude Haiku 4.5")).toBeVisible();
  expect(screen.getByText("Llama 3.2")).toBeVisible();
});

test("toggling an available model chip emits its candidate_id", () => {
  const onToggle = vi.fn();
  render(<CandidatePicker panel={PANEL} selected={[]} onToggle={onToggle} />);
  fireEvent.click(screen.getByLabelText("Llama 3.2"));
  expect(onToggle).toHaveBeenCalledWith("ollama:llama3.2");
});

test("unavailable provider model chips are disabled", () => {
  render(<CandidatePicker panel={PANEL} selected={[]} onToggle={vi.fn()} />);
  expect(screen.getByLabelText("Claude Haiku 4.5")).toBeDisabled();
});

test("custom entry builds a provider:model candidate id", () => {
  const onToggle = vi.fn();
  render(<CandidatePicker panel={PANEL} selected={[]} onToggle={onToggle} />);
  fireEvent.click(screen.getByRole("button", { name: /custom model for Ollama/i }));
  fireEvent.change(screen.getByLabelText(/custom Ollama model/i), { target: { value: "phi3:mini" } });
  fireEvent.click(screen.getByRole("button", { name: "Add" }));
  expect(onToggle).toHaveBeenCalledWith("ollama:phi3:mini");
});

test("custom Add adds a candidate without submitting a surrounding form", () => {
  const onToggle = vi.fn();
  const onSubmit = vi.fn((e) => e.preventDefault());
  render(
    <form onSubmit={onSubmit}>
      <CandidatePicker panel={PANEL} selected={[]} onToggle={onToggle} />
    </form>,
  );
  fireEvent.click(screen.getByRole("button", { name: /custom model for Ollama/i }));
  fireEvent.change(screen.getByLabelText(/custom Ollama model/i), { target: { value: "phi3:mini" } });
  fireEvent.click(screen.getByRole("button", { name: "Add" }));
  expect(onToggle).toHaveBeenCalledWith("ollama:phi3:mini");
  expect(onSubmit).not.toHaveBeenCalled();
});
