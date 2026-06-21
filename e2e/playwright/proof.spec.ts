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
  await expect(page.locator("legend").filter({ hasText: /^Candidates$/ })).toBeVisible();
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

test("scoring cards: LLM-judge card reveals judge filter", async ({ page }) => {
  await page.goto("/");

  // The scoring section renders before the Run proof button.
  await expect(page.getByText("Scoring method")).toBeVisible();

  // The LLM-judge card is visible (aria-label includes title and cost).
  const judgeCard = page.getByRole("button", { name: /LLM judge/i });
  await expect(judgeCard).toBeVisible();

  // Click the LLM-judge card — it should expand the judge filter below.
  await judgeCard.click();

  // "Run on" row with Local/Hosted toggles must appear.
  await expect(page.getByText(/Run on/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /^Local$/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Hosted$/ })).toBeVisible();

  // The judge-model label and dropdown are visible; the Mock judge option is the default.
  await expect(page.getByText(/Judge model/i)).toBeVisible();
  const judgeSelect = page.getByLabel(/Judge model/i);
  const selectedText = await judgeSelect.evaluate((el: HTMLSelectElement) =>
    el.options[el.selectedIndex]?.text ?? ""
  );
  expect(selectedText).toMatch(/Mock judge/i);
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

test("prompt compare: one model, two prompts → leaderboard + receipt section", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Orionfold Proof" })).toBeVisible();

  // Switch the comparison axis to Prompts.
  await page.getByRole("button", { name: "prompts", exact: true }).click();

  // The prompt editor appears, seeded with two starter variants on a keyless mock model.
  await expect(page.getByLabel(/Prompt model/i)).toBeVisible();
  await expect(page.getByLabel(/Variant prompt 1/i)).toBeVisible();
  await expect(page.getByLabel(/Variant prompt 2/i)).toBeVisible();

  // Run keyless (mock model) and confirm a leaderboard row per variant.
  await page.getByRole("button", { name: /Run proof/ }).click();
  const leaderboard = page.getByRole("region", { name: "Leaderboard" });
  await expect(leaderboard).toBeVisible();
  await expect(leaderboard.getByText("Baseline")).toBeVisible();
  await expect(leaderboard.getByText("Concise")).toBeVisible();

  // The receipt records the prompt variants — fetch the JSON receipt for THIS run.
  // (The iframe approach is blocked by the receipt's Content-Security-Policy: sandbox header.)
  // Extract the run ID from the "Export JSON" link in the inspector (unique to this run).
  const exportJsonLink = page.getByRole("link", { name: "Export JSON" });
  const href = await exportJsonLink.getAttribute("href");
  const runId = href!.match(/runs\/(run_[a-f0-9]+)\//)?.[1];
  expect(runId).toBeTruthy();
  const receiptRes = await page.request.get(`/api/runs/${runId}/receipt.json`);
  const receipt = await receiptRes.json();
  expect(receipt.prompt_variants.length).toBe(2);
});
