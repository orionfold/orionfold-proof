import { expect, test } from "@playwright/test";

// The charter's happy path, graded in a real browser against the embedded build:
// open → run sample proof → see leaderboard → open a failure case → export all three receipts.
test("proof loop: run → leaderboard → failure case → receipts", async ({ page }) => {
  // Mocks are off the customer happy path — enable Sandbox up front. The flag is global and the
  // suite shares one DB, so set it deterministically via the API rather than clicking the toggle.
  await page.request.put("/api/settings", { data: { sandbox_enabled: true } });
  await page.goto("/");

  // Engine reachable and setup rendered.
  await expect(page.getByRole("heading", { name: "Orionfold Proof" })).toBeVisible();
  await expect(page.getByText(/Connected/)).toBeVisible();

  // The shared DB may hold datasets from other tests; pin the keypoint demo set explicitly so the
  // 5-example / keypoint-coverage / 5-failure-cases assertions below are deterministic.
  await page.getByLabel("Dataset").selectOption("investment-memo-summarization");

  // Type the decision question AFTER selecting the dataset. Since WS-C, an *untouched* question
  // clears on dataset change, so the receipt heading would otherwise fall back to the task name —
  // a typed (touched) question survives and headlines the receipt (matched in the archive below).
  await page.getByLabel("Decision question").fill("Which model should I trust for client memos?");

  // The Mock provider's Good/Bad models appear in the picker, pre-selected for a keyless run.
  await expect(page.locator("legend").filter({ hasText: /^Candidates$/ })).toBeVisible();
  await expect(page.getByRole("checkbox", { name: "Good model" })).toBeChecked();
  await expect(page.getByRole("checkbox", { name: "Bad model" })).toBeChecked();
  await expect(page.getByRole("button", { name: /custom model for Ollama/i })).toBeVisible();

  // Run the sample proof (both mock candidates are selected by default in Sandbox).
  await page.getByRole("button", { name: /Run proof/ }).click();

  // Leaderboard: mock_good is recommended and passes everything.
  const leaderboard = page.getByRole("region", { name: "Leaderboard" });
  await expect(leaderboard).toBeVisible();
  await expect(leaderboard.getByText("Recommended")).toBeVisible();
  await expect(leaderboard.getByText("100% (5/5)")).toBeVisible();

  // Pareto cost-vs-quality scatter (WS-D1) mounts beneath the leaderboard on a populated run.
  const scatter = page.getByRole("region", { name: "Cost vs quality" });
  await expect(scatter).toBeVisible();
  await expect(scatter.getByTestId("frontier-scatter").locator("svg.recharts-surface")).toBeVisible();

  // Decide insight layer (Task 7): default Y is Pass rate; the toggle flips it to Avg score.
  const passToggle = scatter.getByRole("button", { name: "Pass rate" });
  const avgToggle = scatter.getByRole("button", { name: "Avg score" });
  await expect(passToggle).toHaveAttribute("aria-pressed", "true");
  await avgToggle.click();
  await expect(avgToggle).toHaveAttribute("aria-pressed", "true");
  // Chart stays mounted under the new metric and the axis re-labels to "Avg score".
  await expect(scatter.getByTestId("frontier-scatter").locator("svg.recharts-surface")).toBeVisible();
  await expect(scatter.locator("svg.recharts-surface").getByText("Avg score")).toBeVisible();
  // The deterministic explainer renders beneath the chart (clear-winner run → ok tone).
  const explainer = scatter.getByTestId("decide-explainer");
  await expect(explainer).toBeVisible();
  await expect(explainer).toHaveAttribute("data-tone", "ok");

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
  const recipe = page.getByRole("button", { name: /Different providers/i });
  await expect(recipe).toBeVisible();
  await recipe.click();
  await expect(page.getByLabel(/decision question/i)).toHaveValue(/different hosts/i);
});

test("prompt compare: one model, two prompts → leaderboard + receipt section", async ({ page }) => {
  // Prompt-compare keyless needs a mock model — enable Sandbox up front via the API (deterministic).
  await page.request.put("/api/settings", { data: { sandbox_enabled: true } });
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

// Quick-compare: the unscored head-to-head lane — one prompt, two candidates, human pick,
// saved as a clearly-labeled quick-check Proof Receipt.
test("quick compare: run → pick → save receipt", async ({ page }) => {
  await page.request.put("/api/settings", { data: { sandbox_enabled: true } });
  await page.goto("/");
  await expect(page.getByText(/Connected/)).toBeVisible();

  // Enter the Quick lane; the two mock candidates are pre-selected in Sandbox.
  // Since WS-C, a Quick receipt's headline is DERIVED FROM THE PROMPT (never a carried
  // Models-mode question), so a unique prompt is what makes the receipt card deterministic to
  // open later. The suite shares one DB, so keep it distinctive.
  const quickPrompt = "Quick e2e summarize: revenue grew 22% to $48.2M.";
  await page.getByRole("button", { name: /Quick/ }).click();
  await page.getByLabel("Prompt", { exact: true }).fill(quickPrompt);
  await page.getByRole("button", { name: /Run proof/ }).click();

  // Head-to-head renders; Save is gated until a pick is made.
  const quick = page.getByRole("region", { name: "Quick compare" });
  await expect(quick).toBeVisible();
  const save = quick.getByRole("button", { name: /Save as Proof Receipt/i });
  await expect(save).toBeDisabled();

  // Pick a winner, then save.
  await quick.getByRole("button", { name: /wins$/ }).first().click();
  await expect(save).toBeEnabled();
  await save.click();

  // The picked quick check now appears in Receipts and the receipt reads as a QUICK CHECK.
  await page.getByRole("button", { name: "Receipts" }).click();
  await page.getByRole("button", { name: new RegExp(quickPrompt.replace(/[.?$]/g, "\\$&")) }).first().click();
  const preview = page.frameLocator('iframe[title="Proof Receipt preview"]');
  await expect(preview.getByText(/QUICK CHECK/i).first()).toBeVisible();
  await expect(preview.getByText(/Picked Mock/i)).toBeVisible();
  await expect(preview.getByText(/Promote to a full scored run/i)).toBeVisible();
});
