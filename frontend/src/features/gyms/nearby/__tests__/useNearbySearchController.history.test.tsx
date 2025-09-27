import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useNearbySearchController } from "../useNearbySearchController";

const mockRouter = {
  push: vi.fn(),
  replace: vi.fn(),
};

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  usePathname: () => "/gyms/nearby",
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

const syncHistoryWithLastCall = (calls: unknown[][]) => {
  const lastCall = calls[calls.length - 1];
  if (!lastCall) {
    return;
  }
  const [url] = lastCall as [string];
  const target = new URL(url, "http://localhost");
  window.history.replaceState(null, "", target.toString());
};

describe("useNearbySearchController history navigation", () => {
  beforeEach(() => {
    Object.defineProperty(window.navigator, "geolocation", {
      configurable: true,
      value: {
        getCurrentPosition: vi.fn(),
        watchPosition: vi.fn(),
        clearWatch: vi.fn(),
      },
    });
    window.history.replaceState(null, "", "http://localhost/gyms/nearby");
    mockRouter.push.mockClear();
    mockRouter.replace.mockClear();
  });

  it("uses replace navigation for page changes", async () => {
    const { result, unmount } = renderHook(() =>
      useNearbySearchController({ defaultCenter: { lat: 35.6, lng: 139.7 } }),
    );

    act(() => {
      result.current.setPage(3);
    });

    await waitFor(() => {
      expect(mockRouter.replace).toHaveBeenCalledTimes(1);
    });
    const [url] = mockRouter.replace.mock.calls[0] as [string];
    expect(url).toContain("page=3");
    syncHistoryWithLastCall(mockRouter.replace.mock.calls);

    unmount();
  });

  it("uses push navigation for radius updates", async () => {
    const { result, unmount } = renderHook(() =>
      useNearbySearchController({ defaultCenter: { lat: 35.6, lng: 139.7 } }),
    );

    act(() => {
      result.current.updateRadius(8);
    });

    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledTimes(1);
    });
    const [url] = mockRouter.push.mock.calls[0] as [string];
    expect(url).toContain("radiusKm=8");
    syncHistoryWithLastCall(mockRouter.push.mock.calls);

    unmount();
  });

  it("avoids navigation when the radius does not change", async () => {
    const { result, unmount } = renderHook(() =>
      useNearbySearchController({ defaultCenter: { lat: 35.6, lng: 139.7 }, defaultRadiusKm: 5 }),
    );

    act(() => {
      result.current.updateRadius(5);
    });

    await waitFor(() => {
      expect(mockRouter.push).not.toHaveBeenCalled();
      expect(mockRouter.replace).not.toHaveBeenCalled();
    });

    unmount();
  });
});
