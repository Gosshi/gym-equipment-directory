import { expect, test } from "@playwright/test";

test("トップページにランディングページが表示される", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { level: 1, name: "Find the Perfect Public Gym in Tokyo" }),
  ).toBeVisible();
  await expect(page.getByRole("searchbox", { name: "Search by keyword" })).toBeVisible();
  await expect(page.getByRole("link", { name: "千代田区" })).toBeVisible();
});
