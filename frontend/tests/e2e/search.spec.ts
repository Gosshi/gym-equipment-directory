import { expect, test } from "@playwright/test";

test("検索キーワードでジム一覧を表示できる", async ({ page }) => {
  const emptyResults = {
    items: [],
    meta: {
      total: 0,
      page: 1,
      perPage: 20,
      hasNext: false,
      hasPrev: false,
      hasMore: false,
      pageToken: null,
    },
  };

  const benchResults = {
    items: [
      {
        id: 101,
        slug: "bench-press-studio",
        name: "Bench Press Studio",
        city: "千代田区",
        prefecture: "東京都",
        address: "東京都千代田区丸の内1-1-1",
        equipments: ["ベンチプレス", "ダンベル"],
        thumbnailUrl: null,
        score: 4.8,
        lastVerifiedAt: "2024-01-15T00:00:00Z",
      },
    ],
    meta: {
      total: 1,
      page: 1,
      perPage: 20,
      hasNext: false,
      hasPrev: false,
      hasMore: false,
      pageToken: null,
    },
  };

  await page.route("**/meta/prefectures", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(["tokyo"]),
    });
  });

  await page.route("**/meta/equipment-categories", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(["strength"]),
    });
  });

  await page.route("**/meta/cities**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.route("**/suggest/gyms**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          slug: "bench-press-studio",
          name: "Bench Press Studio",
          pref: "tokyo",
          city: "chiyoda",
        },
      ]),
    });
  });

  await page.route("**/gyms/search**", async route => {
    const url = new URL(route.request().url());
    const keyword = (url.searchParams.get("q") ?? "").trim().toLowerCase();
    const response = keyword === "bench" ? benchResults : emptyResults;

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(response),
    });
  });

  await page.goto("/gyms");

  await page.waitForResponse(response => response.url().includes("/gyms/search"));

  await page.getByLabel("キーワード").fill("bench");

  const submitButton = page.getByRole("button", { name: "検索を実行" });
  await expect(submitButton).toBeEnabled();

  const searchResponse = page.waitForResponse(response => {
    if (!response.url().includes("/gyms/search")) {
      return false;
    }
    try {
      const url = new URL(response.url());
      return (url.searchParams.get("q") ?? "").trim().toLowerCase() === "bench";
    } catch (error) {
      return false;
    }
  });

  await Promise.all([searchResponse, submitButton.click()]);

  const resultsSection = page.locator("section[aria-labelledby='gym-search-results-heading']");
  await expect(resultsSection).toBeVisible();
  await expect(resultsSection.locator("a").first()).toContainText("Bench Press Studio");
});
