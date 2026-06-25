import { expect, test } from "@playwright/test";

// The Datasets screen golden feature, graded in the embedded build: a coverage strip up top, an
// eval-type badge per card, the adaptive governance-contract example render for the bundled bench,
// and the "Run proof →" link that lands on Proof Run with the dataset preselected.
test("datasets screen: coverage strip, eval badge, governance contract, run-proof deep link", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Datasets" }).click();

  // Coverage strip is present and reads the library's shape.
  const coverage = page.getByLabel("Dataset library coverage");
  await expect(coverage).toBeVisible();
  await expect(coverage.getByText("eval types")).toBeVisible();

  // The bundled governance bench card carries the bench eval type + corpus/contract metadata.
  // Locate the innermost card section (the one whose heading is the bench dataset name).
  const bench = page
    .locator("section")
    .filter({ has: page.getByRole("heading", { name: /Advisor curveball/i }) })
    .last();
  await expect(bench.getByText("Governance bench").first()).toBeVisible();
  await expect(bench.getByText("corpus", { exact: true })).toBeVisible();
  await expect(bench.getByText("governance contract", { exact: true })).toBeVisible();

  // Expand its examples → the adaptive governance contract renders (behavior + required gate).
  await bench.getByText("Examples", { exact: true }).click();
  await expect(bench.getByText(/needs:/).first()).toBeVisible();

  // "Run proof →" lands on the Proof Run workspace with this dataset preselected.
  await bench.getByRole("button", { name: /Run a proof on Advisor curveball/i }).click();
  await expect(page.getByRole("heading", { name: "Proof Run", exact: true })).toBeVisible();
  await expect(page.getByLabel("Dataset", { exact: true })).toHaveValue(/advisor-curveball/);
});
