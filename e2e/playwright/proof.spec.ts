import { expect, test } from "@playwright/test";

// The charter's happy path, graded in a real browser against the embedded build:
// open → run sample proof → see leaderboard → open a failure case → export all three receipts.
test("proof loop: run → leaderboard → failure case → receipts", async ({ page }) => {
  await page.goto("/");

  // Engine reachable and setup rendered.
  await expect(page.getByRole("heading", { name: "Orionfold Proof" })).toBeVisible();
  await expect(page.getByText(/Connected/)).toBeVisible();

  // The model picker renders catalog models per provider (the #4 capability). A local model
  // chip is selectable; cloud providers without a key are greyed. Mocks stay default-selected.
  await expect(page.getByText("Candidates")).toBeVisible();
  await expect(page.getByRole("checkbox", { name: "Mock · good" })).toBeChecked();
  await expect(page.getByRole("button", { name: /custom model for Ollama/i })).toBeVisible();

  // Run the sample proof (both mock candidates are selected by default).
  await page.getByRole("button", { name: /Run proof/ }).click();

  // Leaderboard: mock_good is recommended and passes everything.
  const leaderboard = page.getByRole("region", { name: "Leaderboard" });
  await expect(leaderboard).toBeVisible();
  await expect(leaderboard.getByText("Recommended")).toBeVisible();
  await expect(leaderboard.getByText("100% (5/5)")).toBeVisible();

  // Finding 2 — keypoint default: the demo dataset has keypoints, so the keyless
  // run defaults to keypoint coverage scoring. The DecisionSummary must say so.
  await expect(page.getByText(/Scored by/i)).toContainText(/Keypoint coverage/i);

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

  // The receipt is viewable in-app, not just downloadable: open it from the archive.
  await page.getByRole("button", { name: "Receipts" }).click();
  await page.getByRole("button", { name: /Which model should I trust/ }).first().click();
  await expect(page.getByTitle("Proof Receipt preview")).toBeVisible();
  await expect(page.getByRole("button", { name: /Explore in cockpit/ })).toBeVisible();
  for (const label of ["Markdown", "HTML", "JSON"]) {
    await expect(page.getByRole("link", { name: label, exact: true })).toBeVisible();
  }
});

test("decision recipes pre-fill the setup", async ({ page }) => {
  await page.goto("/");
  // The recipe row renders above setup.
  await expect(page.getByRole("heading", { name: "Start from a decision recipe" })).toBeVisible();
  // A recipe with a keyless local arm pre-fills the decision question.
  const recipe = page.getByRole("button", { name: /Same model, different providers/i });
  await expect(recipe).toBeVisible();
  await recipe.click();
  await expect(page.getByLabel(/decision question/i)).toHaveValue(/different hosts/i);
});
