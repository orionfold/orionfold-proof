/**
 * Publish-grade screenshot capture for samples/screenshots/ (the README hero + the rail set).
 *
 * NOT a test — a deterministic capture run against the embedded build, gated behind CAPTURE=1 so
 * it never runs in the normal e2e suite. Reproduces the keyless Sandbox flow (investment-memo +
 * the two mock candidates) the README has always shown, but on the 0.2.0 Arena layout (top app bar
 * + always-on telemetry rail + bento Receipts). Dark theme, 1440-wide viewport to match the
 * existing assets (hero = full-page, the rest = 1440x900 viewport).
 *
 *   CAPTURE=1 pnpm playwright test capture-screenshots.spec.ts --project=chromium
 */
import { test } from "@playwright/test";

const OUT = "../samples/screenshots";
const shot = process.env.CAPTURE === "1";

test.skip(!shot, "capture-only; run with CAPTURE=1");
test.use({ viewport: { width: 1440, height: 900 }, colorScheme: "dark" });

test("capture: Arena cockpit screenshot set (0.2.0)", async ({ page }) => {
  await page.request.put("/api/settings", { data: { sandbox_enabled: true } });
  await page.goto("/");
  await page.getByRole("heading", { name: "Orionfold Proof" }).waitFor();

  // ── Prove: configure (the empty setup canvas + rail) ──────────────────────────────────────
  const dataset = page.getByLabel("Dataset");
  await dataset.waitFor({ state: "visible", timeout: 30_000 });
  await dataset.selectOption("investment-memo-summarization");
  await page.getByLabel("Decision question").fill("Which model should I trust for client memos?");
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/stream-configure.png` });

  // ── Prove: run → populated results (the hero) ─────────────────────────────────────────────
  await page.getByRole("button", { name: /Run proof/ }).click();
  await page.getByRole("region", { name: "Leaderboard" }).waitFor({ timeout: 30_000 });
  await page.waitForTimeout(800); // let the scatter + ledger settle
  // Hero = full-page so the verdict band + leaderboard + cost-vs-quality all land in one image.
  await page.screenshot({ path: `${OUT}/cockpit-arena-populated.png`, fullPage: true });
  // Viewport-height variant: app bar + rail + verdict above the fold (the rail "result" cells live).
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(200);
  await page.screenshot({ path: `${OUT}/rail-prove-result.png` });

  // ── Datasets screen (rail + bento) ────────────────────────────────────────────────────────
  await page.getByRole("button", { name: "Datasets" }).click();
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/rail-datasets.png` });

  // ── Receipts screen (bento masthead + Runs table) ─────────────────────────────────────────
  await page.getByRole("button", { name: "Receipts" }).click();
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/rail-receipts.png` });

  // ── L3 receipt detail (the tabbed artifact) ───────────────────────────────────────────────
  const openRow = page.getByRole("button", { name: /^Open Which model should I trust/ }).first();
  if (await openRow.count()) {
    await openRow.click();
    await page.getByTitle("Proof Receipt preview").waitFor({ timeout: 15_000 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${OUT}/receipt-detail-l3.png` });
  }

  // ── Settings bento ────────────────────────────────────────────────────────────────────────
  await page.getByRole("button", { name: "Settings" }).click();
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/rail-settings.png` });
});
