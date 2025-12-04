import { expect, test } from "@playwright/test";

test("トップページにランディングページが表示される", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { level: 1, name: "IRON MAP" })).toBeVisible();
  await expect(page.getByPlaceholder("SEARCH EQUIPMENT (E.G. POWER RACK)...")).toBeVisible();
  await expect(page.getByRole("link", { name: "千代田区" })).toBeVisible();
});
