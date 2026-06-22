import { expect, test } from "@playwright/test";

// Charter must-have: a user imports their own dataset. Graded in the embedded build —
// open Datasets, paste a 2-line JSONL, preview, name, freeze, and see the card appear.
test("dataset import: paste JSONL → preview → freeze → listed", async ({ page }) => {
  const name = `Import smoke ${Date.now()}`;
  await page.goto("/");

  await page.getByRole("button", { name: "Datasets" }).click();
  await page.getByRole("button", { name: "Import dataset" }).click();

  await page
    .getByLabel(/Paste or upload/i)
    .fill('{"input":"two plus two","expected":"4"}\n{"input":"capital of France","expected":"Paris"}');
  await page.getByRole("button", { name: /^Preview$/ }).click();

  await expect(page.getByText(/2 examples parsed/i)).toBeVisible();

  await page.getByLabel(/Dataset name/i).fill(name);
  await page.getByRole("button", { name: /Freeze dataset/i }).click();

  // The panel closes and the new dataset appears in the list. Scope to THIS dataset's card
  // (the e2e DB is shared across specs, so match within the card for our unique name).
  const card = page.locator("section").filter({ has: page.getByRole("heading", { name }) });
  await expect(card.getByRole("heading", { name })).toBeVisible();
  await expect(card.getByText(/2 examples/)).toBeVisible();
});
