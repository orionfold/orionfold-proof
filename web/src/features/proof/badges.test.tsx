import { render } from "@testing-library/react";
import { expect, test } from "vitest";

import { ProviderTag, StatusBadge } from "./badges";

test("provider tag is neutral, token-driven, and not a pill (categorical identity, never a control)", () => {
  const { container } = render(
    <ProviderTag candidate={{ provider_id: "openai", privacy: "cloud" }} />,
  );
  const el = container.querySelector("span")!;
  // Neutral ink-muted on the card surface — no literal hue, no cyan accent.
  expect(el.className).toContain("text-(--color-ink-muted)");
  expect(el.className).not.toContain("accent");
  // Receipt-stub shape, not a pill (pills read as interactive in Orionfold).
  expect(el.className).toContain("rounded");
  expect(el.className).not.toContain("rounded-full");
});

test("local provider tag is strengthened (stronger neutral ink) without green or the accent", () => {
  // 'Local & private' is the product promise — the local tag reads more prominently than cloud,
  // but green is reserved for PASS status and cyan for controls, so neither appears here.
  const { container } = render(
    <ProviderTag candidate={{ provider_id: "ollama", privacy: "local" }} />,
  );
  const el = container.querySelector("span")!;
  expect(el.className).toContain("text-(--color-ink)");
  expect(el.className).toContain("font-semibold");
  expect(el.className).not.toContain("--color-ok");
  expect(el.className).not.toContain("accent");
  // Still the neutral receipt-stub shape, not a pill.
  expect(el.className).toContain("rounded");
  expect(el.className).not.toContain("rounded-full");
});

test("status badges are token-driven status colors, never literal hues or the accent", () => {
  // error = hard failure → danger; fail = graded miss → warn. Status ≠ accent (no cyan).
  const error = render(<StatusBadge kind="error">boom</StatusBadge>);
  const errEl = error.container.querySelector("span")!;
  expect(errEl.className).toContain("text-(--color-danger)");
  expect(errEl.className).not.toContain("accent");

  const fail = render(<StatusBadge kind="fail">missed</StatusBadge>);
  const failEl = fail.container.querySelector("span")!;
  expect(failEl.className).toContain("text-(--color-warn)");
});
