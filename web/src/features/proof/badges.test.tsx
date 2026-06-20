import { render } from "@testing-library/react";
import { expect, test } from "vitest";

import { ProviderTag, StatusBadge } from "./badges";

test("provider tag carries both a light base and a dark override class", () => {
  const { container } = render(
    <ProviderTag candidate={{ provider_id: "openai", privacy: "cloud" }} />,
  );
  const el = container.querySelector("span")!;
  expect(el.className).toContain("text-sky-700"); // light base
  expect(el.className).toContain("dark:text-sky-300"); // dark override
});

test("status badge carries both a light base and a dark override class", () => {
  const { container } = render(<StatusBadge kind="error">boom</StatusBadge>);
  const el = container.querySelector("span")!;
  expect(el.className).toContain("text-rose-700");
  expect(el.className).toContain("dark:text-rose-300");
});
