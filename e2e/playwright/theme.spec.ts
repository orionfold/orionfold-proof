import { expect, test } from "@playwright/test";

test("theme switcher toggles to light and persists across reload", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("radio", { name: "Light" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});
