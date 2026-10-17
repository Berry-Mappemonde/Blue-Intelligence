import { test, expect } from "@playwright/test";

test.use({ storageState: { cookies: [], origins: [] } });

test("sans choix enregistré, l'écran s'ouvre en anglais", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.getByTestId("view-suivre")).toHaveText("Follow expedition");
});
