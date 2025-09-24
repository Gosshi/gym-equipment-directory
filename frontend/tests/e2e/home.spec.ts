import { expect, test } from "@playwright/test";

test.describe("トップページ", () => {
  test("ヘルスチェック UI が表示される", async ({ page }) => {
    await page.goto("/");

    await expect(
      page.getByRole("heading", { level: 1, name: "API ヘルスチェック" })
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "再チェック" })).toBeVisible();
  });
});
