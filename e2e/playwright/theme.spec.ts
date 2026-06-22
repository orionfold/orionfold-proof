import { expect, test } from "@playwright/test";

test("theme switcher toggles to light and persists across reload", async ({ page }) => {
  await page.goto("/");
  // The theme switcher lives in Settings → Appearance (no longer pinned in the rail).
  await page.getByRole("button", { name: "Settings" }).click();
  await page.getByRole("radio", { name: "Light" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("a first-time install defaults to the dark theme", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.removeItem("orionfold-theme"));
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});
