import { expect, test } from "@playwright/test";

test("トップページにランディングページが表示される", async ({ page }) => {
  await page.goto("/");

  await expect(page.locator("h1").first()).toContainText("MAP");
  await expect(page.getByPlaceholder("設備名で検索 (例: パワーラック)...")).toBeVisible();
  await expect(page.getByRole("link", { name: "千代田区" })).toBeVisible();
});
