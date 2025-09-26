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
});
