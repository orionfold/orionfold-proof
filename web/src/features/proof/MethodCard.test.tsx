import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MethodCard } from "./MethodCard";

describe("MethodCard", () => {
  it("renders title, guidance and cost", () => {
    render(<MethodCard title="Keypoint" guidance="Checks facts" cost="Free" selected={false} onSelect={() => {}} />);
    expect(screen.getByText("Keypoint")).toBeInTheDocument();
    expect(screen.getByText("Checks facts")).toBeInTheDocument();
    expect(screen.getByText("Free")).toBeInTheDocument();
  });
  it("reflects selected state via aria-pressed and fires onSelect", () => {
    const onSelect = vi.fn();
    render(<MethodCard title="Auto" guidance="g" cost="Free" selected onSelect={onSelect} />);
    const btn = screen.getByRole("button", { name: /Auto/i });
    expect(btn).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(btn);
    expect(onSelect).toHaveBeenCalledOnce();
  });
});
