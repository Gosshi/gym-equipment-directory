import { expect, test } from "@playwright/test";

test.describe("検索条件の履歴ナビゲーション", () => {
  test("ブラウザの戻る/進むで検索状態が復元される", async ({ page }) => {
    const baseResults = {
      items: [
        {
          id: 1,
          slug: "national-gym",
          name: "ナショナルジム",
          city: "横浜市",
          prefecture: "神奈川県",
          equipments: ["ダンベル"],
          thumbnailUrl: null,
          score: 4.5,
          lastVerifiedAt: "2024-01-01T00:00:00Z",
        },
        {
          id: 2,
          slug: "coastal-fitness",
          name: "コースタルフィットネス",
          city: "千葉市",
          prefecture: "千葉県",
          equipments: ["ケーブルマシン"],
          thumbnailUrl: null,
          score: 4.2,
          lastVerifiedAt: "2024-01-05T00:00:00Z",
        },
      ],
      meta: {
        total: 2,
        page: 1,
        perPage: 20,
        hasNext: false,
        hasPrev: false,
        hasMore: false,
        pageToken: null,
      },
    };

    const tokyoResults = {
      items: [
        {
          id: 11,
          slug: "tokyo-strong",
          name: "トーキョーストロング",
          city: "新宿区",
          prefecture: "東京都",
          equipments: ["パワーラック"],
          thumbnailUrl: null,
          score: 4.8,
          lastVerifiedAt: "2024-02-10T00:00:00Z",
        },
        {
          id: 12,
          slug: "shibuya-fitness",
          name: "シブヤフィットネス",
          city: "渋谷区",
          prefecture: "東京都",
          equipments: ["ランニングマシン"],
          thumbnailUrl: null,
          score: 4.4,
          lastVerifiedAt: "2024-02-12T00:00:00Z",
        },
      ],
      meta: {
        total: 2,
        page: 1,
        perPage: 20,
        hasNext: false,
        hasPrev: false,
        hasMore: false,
        pageToken: null,
      },
    };

    const tokyoSortedByName = {
      ...tokyoResults,
      items: [...tokyoResults.items].sort((a, b) => a.name.localeCompare(b.name, "ja")),
    };

    await page.route("**/meta/prefectures", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(["tokyo", "kanagawa"]),
      });
    });

    await page.route("**/meta/equipment-categories", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(["フリーウェイト", "マシン"]),
      });
    });

    await page.route("**/meta/cities**", async route => {
      const url = new URL(route.request().url());
      const pref = url.searchParams.get("pref");
      if (pref === "tokyo") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            { city: "shinjuku", count: 10 },
            { city: "shibuya", count: 8 },
          ]),
        });
        return;
      }
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
        body: JSON.stringify([]),
      });
    });

    await page.route("**/gyms/search**", async route => {
      const url = new URL(route.request().url());
      const pref = url.searchParams.get("pref");
      const sort = url.searchParams.get("sort");
      const response = (() => {
        if (pref === "tokyo" && sort === "name") {
          return tokyoSortedByName;
        }
        if (pref === "tokyo") {
          return tokyoResults;
        }
        return baseResults;
      })();

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(response),
      });
    });

    await page.goto("/gyms");

    await page.waitForResponse(response => {
      if (!response.url().includes("/gyms/search")) {
        return false;
      }
      const url = new URL(response.url());
      return !url.searchParams.has("pref");
    });

    const prefectureSelect = page.getByLabel("都道府県");
    const sortSelect = page.getByLabel("並び順");
    const resultsSection = page.locator("section[aria-labelledby='gym-search-results-heading']");

    await expect(prefectureSelect).toHaveValue("");
    await expect(sortSelect).toHaveValue("rating:desc");
    await expect(resultsSection.getByRole("heading", { level: 3 }).first()).toHaveText(
      "ナショナルジム",
    );

    await prefectureSelect.selectOption("tokyo");
    await expect(prefectureSelect).toHaveValue("tokyo");
    await expect(page).toHaveURL(/pref=tokyo/);
    await expect(resultsSection.getByRole("heading", { level: 3 }).first()).toHaveText(
      "トーキョーストロング",
    );

    await sortSelect.selectOption("name:asc");
    await expect(sortSelect).toHaveValue("name:asc");
    await expect(page).toHaveURL(/sort=name/);
    await page.goBack();
    await expect(page).toHaveURL(/pref=tokyo/);
    await expect(page).not.toHaveURL(/sort=name/);
    await expect(prefectureSelect).toHaveValue("tokyo");
    await expect(sortSelect).toHaveValue("rating:desc");
    await expect(resultsSection.getByRole("heading", { level: 3 }).first()).toHaveText(
      "トーキョーストロング",
    );

    await page.goBack();
    await expect(prefectureSelect).toHaveValue("");
    await expect(sortSelect).toHaveValue("rating:desc");
    await expect(page).not.toHaveURL(/pref=/);
    await expect(resultsSection.getByRole("heading", { level: 3 }).first()).toHaveText(
      "ナショナルジム",
    );

    await page.goForward();
    await expect(prefectureSelect).toHaveValue("tokyo");
    await expect(sortSelect).toHaveValue("rating:desc");
    await expect(
      resultsSection.getByRole("heading", { level: 3, name: "トーキョーストロング" }),
    ).toBeVisible();

    await page.goForward();
    await expect(prefectureSelect).toHaveValue("tokyo");
    await expect(sortSelect).toHaveValue("name:asc");
    await expect(
      resultsSection.getByRole("heading", { level: 3, name: "シブヤフィットネス" }),
    ).toBeVisible();
  });
});
