import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { SelectionPanel } from "../../lib/api";
import { PromptVariants } from "./PromptVariants.tsx";

const panel: SelectionPanel = {
  providers: [
    { provider_id: "mock_good", label: "Mock · good", privacy: "local", available: true,
      supports_custom: false, candidate_id: "mock_good", models: [] },
  ],
};
const variants = [
  { name: "Baseline", system_prompt: "a" },
  { name: "Concise", system_prompt: "b" },
];

describe("PromptVariants", () => {
  it("renders the model select and a row per variant", () => {
    render(<PromptVariants variants={variants} modelId="mock_good" panel={panel}
      onChangeVariants={() => {}} onChangeModel={() => {}} />);
    expect(screen.getByLabelText(/Prompt model/i)).toBeInTheDocument();
    expect(screen.getAllByRole("textbox", { name: /variant prompt/i })).toHaveLength(2);
  });

  it("adds a variant row", () => {
    const onChange = vi.fn();
    render(<PromptVariants variants={variants} modelId="mock_good" panel={panel}
      onChangeVariants={onChange} onChangeModel={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: /add prompt/i }));
    expect(onChange).toHaveBeenCalledWith([...variants, { name: "", system_prompt: "" }]);
  });

  it("removes a variant row", () => {
    const onChange = vi.fn();
    render(<PromptVariants variants={variants} modelId="mock_good" panel={panel}
      onChangeVariants={onChange} onChangeModel={() => {}} />);
    fireEvent.click(screen.getAllByRole("button", { name: /remove/i })[0]);
    expect(onChange).toHaveBeenCalledWith([variants[1]]);
  });
});
