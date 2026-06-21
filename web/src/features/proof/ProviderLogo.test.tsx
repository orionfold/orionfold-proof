import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { ProviderLogo } from "./ProviderLogo";

test("renders a branded svg logo for a known provider", () => {
  render(<ProviderLogo providerId="anthropic" available label="Anthropic" />);
  const logo = screen.getByLabelText("Anthropic logo");
  expect(logo.tagName.toLowerCase()).toBe("svg");
});

test("dims the logo when the provider is unavailable", () => {
  render(<ProviderLogo providerId="openai" available={false} label="OpenAI" />);
  expect(screen.getByLabelText("OpenAI logo").getAttribute("class")).toContain("opacity-50");
});

test("falls back to a status dot for unbranded providers (mocks)", () => {
  const { container } = render(
    <ProviderLogo providerId="mock_good" available label="Mock · good" />,
  );
  // No branded svg; a decorative dot span instead.
  expect(screen.queryByLabelText(/logo/)).toBeNull();
  expect(container.querySelector("span.rounded-full")).not.toBeNull();
});
