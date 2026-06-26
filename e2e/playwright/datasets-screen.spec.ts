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

// The smart-parse of the bench example's flattened retrieved-context, plus the Corpus browse surface
// reached from the corpus badge — both derived, no migration.
test("datasets screen: retrieved-context disclosure + corpus browse surface", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Datasets" }).click();

  const bench = page
    .locator("section")
    .filter({ has: page.getByRole("heading", { name: /Advisor curveball/i }) })
    .last();

  // Expand examples → the flattened context is parsed into a Question + collapsible source cards,
  // and at least one source is cross-linked as "Must cite".
  await bench.getByText("Examples", { exact: true }).click();
  await expect(bench.getByText(/Retrieved context · \d+ sources/).first()).toBeVisible();
  await expect(bench.getByText("Must cite").first()).toBeVisible();

  // The corpus badge is a button (accessible name = its "corpus" text) that opens the Corpus
  // browse surface with derived sources.
  await bench.getByRole("button", { name: "corpus" }).click();
  await expect(page.getByRole("heading", { name: /field notes/i })).toBeVisible();
  await expect(page.getByText(/sources · \d+ cited by the bench/)).toBeVisible();

  // "Back to datasets" returns to the list.
  await page.getByRole("button", { name: /Back to datasets/i }).click();
  await expect(page.getByRole("heading", { name: "Datasets", exact: true })).toBeVisible();
});

// The Corpora list at the top of the Datasets screen — a second, always-available entry point to a
// corpus that does not depend on a bench dataset binding (the corpus badge path). This closes the
// latent gap where an unbound/imported corpus would be invisible in the UI.
test("datasets screen: corpora list opens the corpus browse surface directly", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Datasets" }).click();

  // The Corpora section is present and lists the bundled corpus with its manifest source count.
  const corpora = page.getByRole("heading", { name: /Corpora \(\d+\)/ });
  await expect(corpora).toBeVisible();
  const card = page.getByRole("button", { name: /Browse the .* corpus/ }).first();
  await expect(card).toBeVisible();
  await expect(card.getByText(/\d+ sources?/)).toBeVisible();

  // Clicking the corpus card opens the Corpus browse surface (the same view the badge reaches).
  await card.click();
  await expect(page.getByText(/sources · \d+ cited by the bench/)).toBeVisible();

  // "Back to datasets" returns to the list.
  await page.getByRole("button", { name: /Back to datasets/i }).click();
  await expect(page.getByRole("heading", { name: "Datasets", exact: true })).toBeVisible();
});
