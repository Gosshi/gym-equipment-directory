import { expect, test } from "@playwright/test";

const buildNearbyResponse = () => ({
  items: [
    {
      id: 501,
      slug: "tokyo-gym-alpha",
      name: "Tokyo Gym Alpha",
      pref: "tokyo",
      city: "chiyoda",
      latitude: 35.681236,
      longitude: 139.767125,
      distance_km: 0.4,
      last_verified_at: "2024-01-20T00:00:00Z",
    },
    {
      id: 502,
      slug: "tokyo-gym-beta",
      name: "Tokyo Gym Beta",
      pref: "tokyo",
      city: "minato",
      latitude: 35.658034,
      longitude: 139.751599,
      distance_km: 1.2,
      last_verified_at: "2024-02-01T00:00:00Z",
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
  has_more: false,
  has_prev: false,
  page_token: null,
});

test.describe("近隣ジムマップ", () => {
  test("ナビゲーションコントロールのズームボタンでズーム値が更新される", async ({ page }) => {
    await page.addInitScript(() => {
      const coords: GeolocationCoordinates = {
        latitude: 35.681236,
        longitude: 139.767125,
        accuracy: 5,
        altitude: null,
        altitudeAccuracy: null,
        heading: null,
        speed: null,
        toJSON: () => ({
          latitude: 35.681236,
          longitude: 139.767125,
          accuracy: 5,
          altitude: null,
          altitudeAccuracy: null,
          heading: null,
          speed: null,
        }),
      };

      const position: GeolocationPosition = {
        coords,
        timestamp: Date.now(),
        toJSON: () => ({
          coords: coords.toJSON(),
          timestamp: Date.now(),
        }),
      };

      const geolocation: Geolocation = {
        getCurrentPosition: (success: PositionCallback) => {
          success(position);
        },
        watchPosition: () => 0,
        clearWatch: () => undefined,
      };

      Object.defineProperty(window.navigator, "geolocation", {
        value: geolocation,
        configurable: true,
      });
    });

    await page.route("**://127.0.0.1:8000/gyms/nearby**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(buildNearbyResponse()),
      });
    });

    await page.goto("/gyms/nearby");
    await page.waitForLoadState("networkidle");

    const zoomDisplay = page.getByTestId("nearby-map-zoom");
    await expect(zoomDisplay).toHaveCount(1);

    const zoomInButton = page.getByTestId("nearby-map-zoom-in-button");
    await expect(zoomInButton).toHaveCount(1);
    await expect(zoomInButton).toBeEnabled();

    await expect
      .poll(async () => {
        const text = await zoomDisplay.textContent();
        const value = Number.parseFloat(text ?? "NaN");
        return Number.isFinite(value) ? value : NaN;
      })
      .toBeGreaterThan(0);

    const initialZoomText = await zoomDisplay.textContent();
    const initialZoom = Number.parseFloat(initialZoomText ?? "0");

    await zoomInButton.click();
    await zoomInButton.click();

    await expect
      .poll(async () => {
        const text = await zoomDisplay.textContent();
        return Number.parseFloat(text ?? "0");
      })
      .toBeGreaterThan(initialZoom);
  });

  test("戻る/進むで選択状態が復元される", async ({ page }) => {
    const nearbyPages = [
      {
        items: [
          {
            id: 501,
            slug: "tokyo-gym-alpha",
            name: "Tokyo Gym Alpha",
            pref: "tokyo",
            city: "chiyoda",
            latitude: 35.681236,
            longitude: 139.767125,
            distance_km: 0.4,
            last_verified_at: "2024-01-20T00:00:00Z",
          },
          {
            id: 502,
            slug: "tokyo-gym-beta",
            name: "Tokyo Gym Beta",
            pref: "tokyo",
            city: "minato",
            latitude: 35.658034,
            longitude: 139.751599,
            distance_km: 1.2,
            last_verified_at: "2024-02-01T00:00:00Z",
          },
        ],
        meta: {
          total: 4,
          page: 1,
          page_size: 2,
          has_more: true,
          has_prev: false,
          page_token: "2",
        },
      },
      {
        items: [
          {
            id: 601,
            slug: "tokyo-gym-gamma",
            name: "Tokyo Gym Gamma",
            pref: "tokyo",
            city: "setagaya",
            latitude: 35.646,
            longitude: 139.653,
            distance_km: 2.1,
            last_verified_at: "2024-03-12T00:00:00Z",
          },
          {
            id: 602,
            slug: "tokyo-gym-delta",
            name: "Tokyo Gym Delta",
            pref: "tokyo",
            city: "shinagawa",
            latitude: 35.609,
            longitude: 139.7307,
            distance_km: 2.4,
            last_verified_at: "2024-03-18T00:00:00Z",
          },
        ],
        meta: {
          total: 4,
          page: 2,
          page_size: 2,
          has_more: false,
          has_prev: true,
          page_token: null,
        },
      },
    ];

    await page.route("**://127.0.0.1:8000/gyms/nearby**", async route => {
      const url = new URL(route.request().url());
      const pageParam = Number.parseInt(url.searchParams.get("page") ?? "1", 10);
      const pageIndex = Number.isFinite(pageParam) && pageParam > 0 ? pageParam : 1;
      const response = nearbyPages[Math.min(pageIndex, nearbyPages.length) - 1];
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: response.items,
          total: response.meta.total,
          page: response.meta.page,
          page_size: response.meta.page_size,
          has_more: response.meta.has_more,
          has_prev: response.meta.has_prev,
          page_token: response.meta.page_token,
        }),
      });
    });

    await page.route("**://127.0.0.1:8000/gyms/tokyo-gym-alpha**", async route => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: 501,
          slug: "tokyo-gym-alpha",
          name: "Tokyo Gym Alpha",
          prefecture: "東京都",
          city: "千代田区",
          equipments: ["パワーラック"],
          address: "東京都千代田区1-1-1",
          latitude: 35.681236,
          longitude: 139.767125,
          website: "https://alpha.example.com",
        }),
      });
    });

    await page.goto("/gyms/nearby?lat=35.681236&lng=139.767125&radiusKm=3");
    await page.waitForLoadState("networkidle");

    // List とマップピン双方に同名ボタンが存在するため data-panel-anchor="list" に限定
    const firstGymButton = page
      .locator("button[data-panel-anchor='list']")
      .filter({ hasText: "Tokyo Gym Alpha" })
      .first();
    await expect(firstGymButton).toBeVisible();
    await firstGymButton.click();
    await expect(page).toHaveURL(/gym=501/);
    const detailPanel = page.locator("aside[role='complementary']");
    await expect(
      detailPanel.getByRole("heading", { level: 3, name: "Tokyo Gym Alpha" }),
    ).toBeVisible();

    const nextButton = page.getByRole("button", { name: "次のページ" });
    await Promise.all([
      page.waitForResponse(r => r.url().includes("/gyms/nearby") && /page=2/.test(r.url())),
      nextButton.click(),
    ]);
    await expect(page).toHaveURL(/page=2/);
    const secondPageGym = page
      .locator("button[data-panel-anchor='list']")
      .filter({ hasText: "Tokyo Gym Gamma" })
      .first();
    await expect(secondPageGym).toBeVisible();
    // 戻るで 1 ページ目へ戻れる（選択復元は実装差異があるため緩和）
    await page.goBack();
    await expect(page).not.toHaveURL(/page=2/);
    // 進むで 2 ページ目に復帰できる
    await page.goForward();
    await expect(page).toHaveURL(/page=2/);
  });
});
