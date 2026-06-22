import path from "node:path";

import { expect, test } from "@playwright/test";

// Resolve the fixture relative to THIS file, not the cwd (playwright runs from web/).
const FIXTURE = path.join(__dirname, "fixtures", "cases.xlsx");

// Broadened-ICP must-have: a user imports a document (not just JSONL). Graded in the embedded
// build — open Datasets, upload a 2-row .xlsx, the server extracts it to CSV-text, preview,
// tag it, freeze, and see the tagged card appear.
test("dataset doc import: upload .xlsx → extract → preview → tag → freeze → listed", async ({
  page,
}) => {
  const name = `Doc import smoke ${Date.now()}`;
  await page.goto("/");

  await page.getByRole("button", { name: "Datasets" }).click();
  await page.getByRole("button", { name: "Import dataset" }).click();

  await page.getByLabel(/Upload dataset file/i).setInputFiles(FIXTURE);
  // Extraction populates the textarea with CSV-text.
  await expect(page.getByLabel(/Paste or upload/i)).toHaveValue(/Ping\?/);

  await page.getByRole("button", { name: /^Preview$/ }).click();
  await expect(page.getByText(/2 examples parsed/i)).toBeVisible();

  await page.getByLabel(/Dataset name/i).fill(name);
  const tagInput = page.getByLabel(/^Add tag$/i);
  await tagInput.fill("Legal");
  await tagInput.press("Enter");
  // The tag is committed as a removable chip before we freeze.
  await expect(page.getByRole("button", { name: /Remove tag Legal/i })).toBeVisible();
  await page.getByRole("button", { name: /Freeze dataset/i }).click();

  // Scope to THIS dataset's card (the e2e DB is shared across specs).
  const card = page.locator("section").filter({ has: page.getByRole("heading", { name }) });
  await expect(card.getByRole("heading", { name })).toBeVisible();
  await expect(card.getByText("Legal", { exact: true })).toBeVisible();
  await expect(card.getByText(/cases\.xlsx/)).toBeVisible();
});
