import { render } from "@testing-library/react";
import { expect, test } from "vitest";

import { SourceDisclosure } from "./SourceDisclosure";

test("a cited source gets the accent frame", () => {
  const { container } = render(
    <SourceDisclosure cited summary={<span>S1</span>} body={<span>excerpt</span>} />,
  );
  const details = container.querySelector("details");
  expect(details?.className).toContain("--color-accent");
});

test("an uncited source uses the neutral panel frame, not the accent", () => {
  const { container } = render(
    <SourceDisclosure cited={false} summary={<span>S1</span>} body={<span>excerpt</span>} />,
  );
  const details = container.querySelector("details");
  expect(details?.className).toContain("--color-panel-line");
  expect(details?.className).not.toContain("--color-accent");
});

test("with a body the card is expandable (cursor-pointer) and renders the body", () => {
  const { container } = render(
    <SourceDisclosure cited={false} summary={<span>S1</span>} body={<span>the excerpt</span>} />,
  );
  expect(container.querySelector("summary")?.className).toContain("cursor-pointer");
  expect(container.textContent ?? "").toContain("the excerpt");
});

test("with no body the card is non-expandable (cursor-default) and renders no body wrapper", () => {
  const { container } = render(
    <SourceDisclosure cited={false} summary={<span>S1</span>} />,
  );
  const summary = container.querySelector("summary");
  expect(summary?.className).toContain("cursor-default");
  expect(summary?.className).not.toContain("cursor-pointer");
  // Only the <summary> lives under <details> — no bordered body div.
  expect(container.querySelector("details > div")).toBeNull();
});

test("comfortable density uses the larger radius and roomier padding", () => {
  const { container } = render(
    <SourceDisclosure cited={false} density="comfortable" summary={<span>S1</span>} body={<span>b</span>} />,
  );
  expect(container.querySelector("details")?.className).toContain("rounded-lg");
  expect(container.querySelector("summary")?.className).toContain("px-3 py-2");
  expect(container.querySelector("details > div")?.className).toContain("px-3 py-2");
});

test("compact density (the default) uses the tighter radius and padding", () => {
  const { container } = render(
    <SourceDisclosure cited={false} summary={<span>S1</span>} body={<span>b</span>} />,
  );
  const details = container.querySelector("details");
  expect(details?.className).toContain("rounded");
  expect(details?.className).not.toContain("rounded-lg");
  expect(container.querySelector("summary")?.className).toContain("px-2 py-1.5");
  expect(container.querySelector("details > div")?.className).toContain("px-2 py-1.5");
});
