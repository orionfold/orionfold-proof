import { expect, test } from "@playwright/test";

// The charter's happy path, graded in a real browser against the embedded build:
// open → run sample proof → see leaderboard → open a failure case → export all three receipts.
test("proof loop: run → leaderboard → failure case → receipts", async ({ page }) => {
  await page.goto("/");

  // Engine reachable and setup rendered.
  await expect(page.getByRole("heading", { name: "Orionfold Proof" })).toBeVisible();
  await expect(page.getByText(/Connected/)).toBeVisible();

  // Run the sample proof (both mock candidates are selected by default).
  await page.getByRole("button", { name: /Run proof/ }).click();

  // Leaderboard: mock_good is recommended and passes everything.
  const leaderboard = page.getByRole("region", { name: "Leaderboard" });
  await expect(leaderboard).toBeVisible();
  await expect(leaderboard.getByText("Recommended")).toBeVisible();
  await expect(leaderboard.getByText("100% (5/5)")).toBeVisible();

  // Failure cases: at least one, including the surfaced provider error.
  const failures = page.getByRole("region", { name: "Failure cases" });
  await expect(failures.getByRole("heading", { name: /Failure cases \(5\)/ })).toBeVisible();
  await expect(failures.getByText(/simulated provider failure/)).toBeVisible();

  // All three receipts download with the config hash in the filename.
  const exporter = page.getByRole("region", { name: "Proof Receipt export" });
  for (const label of ["Export Markdown", "Export HTML", "Export JSON"]) {
    const downloadPromise = page.waitForEvent("download");
    await exporter.getByRole("link", { name: label }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/^proof-receipt-[a-f0-9]{12}\.(md|html|json)$/);
  }
});
