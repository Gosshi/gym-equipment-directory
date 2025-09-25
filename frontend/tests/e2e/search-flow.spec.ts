import { expect, test } from "@playwright/test";

type SearchMeta = {
  total: number | null;
  page: number;
  perPage: number;
  hasNext: boolean;
  hasPrev: boolean;
  hasMore: boolean;
};

type SearchItem = {
  id: number;
  slug: string;
  name: string;
  prefecture: string;
  city: string;
  address: string;
  equipments: string[];
  thumbnailUrl: string | null;
  score: number;
  lastVerifiedAt: string;
};

type SearchResponse = {
  items: SearchItem[];
  meta: SearchMeta;
};

type GymDetailResponse = {
  slug: string;
  name: string;
  address: string;
  prefecture: string;
  city: string;
  description: string;
  openingHours: string;
  fees: string;
  website: string;
  categories: string[];
  facilities: Array<{ category: string; items: string[] }>;
  latitude: number;
  longitude: number;
};

declare global {
  interface Window {
    __mockGeolocation: {
      shouldFail: boolean;
      position: { latitude: number; longitude: number };
    };
  }
}

test.describe("検索から詳細までの結合フロー", () => {
  test("検索→一覧→詳細、位置情報、距離、ページングを通しで確認", async ({ page }) => {
    await page.addInitScript(() => {
      const geoState = {
        shouldFail: false,
        position: { latitude: 35.681236, longitude: 139.767125 },
      };
      Object.defineProperty(window, "__mockGeolocation", {
        value: geoState,
        configurable: true,
      });
      const geolocation = {
        getCurrentPosition: (
          success: (position: GeolocationPosition) => void,
          error?: (error: GeolocationPositionError) => void,
        ) => {
          if (geoState.shouldFail) {
            error?.({ code: 1, message: "denied" } as GeolocationPositionError);
            return;
          }
          success({
            coords: {
              latitude: geoState.position.latitude,
              longitude: geoState.position.longitude,
              accuracy: 5,
              altitude: null,
              altitudeAccuracy: null,
              heading: null,
              speed: null,
            },
            timestamp: Date.now(),
          } as GeolocationPosition);
        },
        watchPosition: () => 1,
        clearWatch: () => undefined,
      } satisfies Geolocation;
      Object.defineProperty(navigator, "geolocation", {
        value: geolocation,
        configurable: true,
      });
    });

    const searchResponses: Record<string, SearchResponse> = {
      default: {
        items: [
          {
            id: 1,
            slug: "central-fit",
            name: "Central Fit 新宿",
            prefecture: "東京都",
            city: "新宿区",
            address: "東京都新宿区西新宿1-1-1",
            equipments: ["パワーラック", "ダンベル", "ストレッチエリア"],
            thumbnailUrl: null,
            score: 4.8,
            lastVerifiedAt: "2024-09-01T00:00:00Z",
          },
          {
            id: 2,
            slug: "harbor-fitness",
            name: "Harbor Fitness 品川",
            prefecture: "東京都",
            city: "港区",
            address: "東京都港区港南2-2-2",
            equipments: ["スミスマシン", "フリーウェイト", "カーディオ"],
            thumbnailUrl: null,
            score: 4.6,
            lastVerifiedAt: "2024-08-15T00:00:00Z",
          },
        ],
        meta: {
          total: 3,
          page: 1,
          perPage: 2,
          hasNext: true,
          hasPrev: false,
          hasMore: true,
        },
      },
      radius5: {
        items: [
          {
            id: 1,
            slug: "central-fit",
            name: "Central Fit 新宿",
            prefecture: "東京都",
            city: "新宿区",
            address: "東京都新宿区西新宿1-1-1",
            equipments: ["パワーラック", "ダンベル", "ストレッチエリア"],
            thumbnailUrl: null,
            score: 4.8,
            lastVerifiedAt: "2024-09-01T00:00:00Z",
          },
        ],
        meta: {
          total: 1,
          page: 1,
          perPage: 1,
          hasNext: false,
          hasPrev: false,
          hasMore: false,
        },
      },
      page2: {
        items: [
          {
            id: 3,
            slug: "river-side-gym",
            name: "River Side Gym 中野",
            prefecture: "東京都",
            city: "中野区",
            address: "東京都中野区中野3-3-3",
            equipments: ["ケーブルマシン", "スタジオ", "サウナ"],
            thumbnailUrl: null,
            score: 4.5,
            lastVerifiedAt: "2024-07-21T00:00:00Z",
          },
        ],
        meta: {
          total: 3,
          page: 2,
          perPage: 2,
          hasNext: false,
          hasPrev: true,
          hasMore: false,
        },
      },
      empty: {
        items: [],
        meta: {
          total: 0,
          page: 1,
          perPage: 20,
          hasNext: false,
          hasPrev: false,
          hasMore: false,
        },
      },
    };

    const detailResponses: Record<string, GymDetailResponse> = {
      "central-fit": {
        slug: "central-fit",
        name: "Central Fit 新宿",
        address: "東京都新宿区西新宿1-1-1",
        prefecture: "東京都",
        city: "新宿区",
        description: "新宿駅徒歩3分の24時間営業フィットネスジム。",
        openingHours: "24時間営業",
        fees: "月額 12,000円",
        website: "https://central-fit.example.com",
        categories: ["24時間", "フリーウェイト"],
        facilities: [
          { category: "フリーウェイト", items: ["パワーラック", "スミスマシン"] },
          { category: "有酸素", items: ["トレッドミル", "バイク"] },
        ],
        latitude: 35.6895,
        longitude: 139.6917,
      },
    };

    await page.route("**/meta/prefectures", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([{ code: "13", label: "東京都" }]),
      });
    });

    await page.route("**/meta/equipment-categories", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([{ value: "free-weight", label: "フリーウェイト" }]),
      });
    });

    await page.route("**/meta/cities**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([{ value: "shinjuku", label: "新宿区" }]),
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
      const query = (url.searchParams.get("q") ?? "").trim().toLowerCase();
      const pageParam = Number.parseInt(url.searchParams.get("page") ?? "1", 10) || 1;
      const radius = Number.parseInt(url.searchParams.get("radius_km") ?? "0", 10);

      let key = "default";
      if (query === "nomatch") {
        key = "empty";
      } else if (pageParam >= 2) {
        key = "page2";
      } else if (radius > 0 && radius <= 5) {
        key = "radius5";
      }

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(searchResponses[key]),
      });
    });

    await page.route("**/gyms/*", async route => {
      const url = new URL(route.request().url());
      if (url.pathname.endsWith("/gyms/search")) {
        await route.continue();
        return;
      }
      const match = url.pathname.match(/\/gyms\/([^/]+)$/);
      if (!match) {
        await route.continue();
        return;
      }
      const slug = match[1];
      const detail = detailResponses[slug];
      if (!detail) {
        await route.fulfill({ status: 404, contentType: "application/json", body: "{}" });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(detail),
      });
    });

    await page.evaluate(() => {
      window.__mockGeolocation.shouldFail = true;
    });

    await page.goto("/gyms");

    await expect(page.getByRole("heading", { name: "検索結果" })).toBeVisible();

    const searchButton = page.getByRole("button", { name: "検索を実行" });
    await expect(searchButton).toBeEnabled();

    await page.getByRole("button", { name: "現在地を再取得" }).click();

    const locationError = page.getByRole("alert").getByText("位置情報が許可されていません。");
    await expect(locationError).toBeVisible();

    await page.evaluate(() => {
      window.__mockGeolocation.shouldFail = false;
      window.__mockGeolocation.position = { latitude: 35.699, longitude: 139.698 };
    });

    await page.getByRole("button", { name: "現在地を再取得" }).click();

    await expect(
      page.getByText("現在地を使用中（35.6990, 139.6980）", { exact: false }),
    ).toBeVisible();

    const cardLink = page.getByRole("link", { name: "Central Fit 新宿の詳細を見る" });
    await expect(cardLink).toBeVisible();

    await expect(page.locator("[data-testid='gym-equipments']").first()).toContainText("パワーラック");

    await expect(page.locator("[data-testid='gym-equipments']")).toHaveCount(1);

    await page.locator("#gym-search-distance").evaluate((element, value) => {
      const input = element as HTMLInputElement;
      input.value = String(value);
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }, 15);

    await expect(page.locator("[data-testid='gym-equipments']")).toHaveCount(2, {
      timeout: 3000,
    });

    await expect(page.locator("a", { hasText: "Harbor Fitness 品川" })).toBeVisible();

    await page.getByRole("button", { name: "次のページ" }).click();

    await expect(page.locator("a", { hasText: "River Side Gym 中野" })).toBeVisible();

    await page.getByRole("button", { name: "前のページ" }).click();

    await expect(page.locator("a", { hasText: "Central Fit 新宿" })).toBeVisible();

    const keywordInput = page.getByLabel("キーワード");
    await keywordInput.fill("nomatch");

    const waitForEmpty = page.waitForResponse(response =>
      response.url().includes("/gyms/search") && response.request().url().includes("nomatch"),
    );
    await Promise.all([waitForEmpty, searchButton.click()]);

    await expect(page.getByText("該当するジムが見つかりませんでした")).toBeVisible();

    await keywordInput.fill("central");
    const waitForCentral = page.waitForResponse(response =>
      response.url().includes("/gyms/search") && !response.request().url().includes("nomatch"),
    );
    await Promise.all([waitForCentral, searchButton.click()]);

    await expect(cardLink).toBeVisible();

    await cardLink.click();

    await expect(page).toHaveURL(/\/gyms\/central-fit$/);

    await expect(page.getByRole("heading", { name: "Central Fit 新宿" })).toBeVisible();

    await expect(page.getByRole("link", { name: "このジムの情報を報告する" })).toBeVisible();
  });
});
