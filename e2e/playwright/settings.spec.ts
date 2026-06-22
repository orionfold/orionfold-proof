import { expect, test } from "@playwright/test";

// Settings → Data Management, graded against the embedded build. The suite shares one DB, so each
// test asserts only its OWN artifacts and sets the global sandbox flag deterministically via the API.
test("seed adds a Sample receipt, remove deletes it", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Settings" }).click();

  await page.getByRole("button", { name: /^Seed sample data$/ }).click();
  await page.getByRole("button", { name: /^Confirm$/ }).click();

  await page.getByRole("button", { name: "Receipts" }).click();
  // The seeded receipt carries a "Sample" badge (exact match avoids the dataset name "Sample ·…").
  await expect(page.getByText("Sample", { exact: true }).first()).toBeVisible();

  await page.getByRole("button", { name: "Settings" }).click();
  await page.getByRole("button", { name: /^Remove sample data$/ }).click();
  await page.getByRole("button", { name: /^Confirm$/ }).click();

  await page.getByRole("button", { name: "Receipts" }).click();
  // Only the sample is gone — other tests' runs may persist in the shared DB, so assert the
  // Sample badge specifically rather than global emptiness.
  await expect(page.getByText("Sample", { exact: true })).toHaveCount(0);
});

test("sandbox toggle controls the Mock provider in the picker", async ({ page }) => {
  // Force OFF deterministically (the flag is global, shared across the suite), then verify the
  // toggle brings the simulated Mock provider into the picker.
  await page.request.put("/api/settings", { data: { sandbox_enabled: false } });
  await page.goto("/");
  await expect(page.getByRole("checkbox", { name: "Good model" })).toHaveCount(0);

  await page.getByRole("button", { name: "Settings" }).click();
  await page.getByRole("switch", { name: /Sandbox/i }).click();
  await page.getByRole("button", { name: "Proof Run" }).click();
  await expect(page.getByRole("checkbox", { name: "Good model" })).toBeVisible();
});
