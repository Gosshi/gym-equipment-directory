import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useGymSearch } from "../useGymSearch";
import { useSearchStore } from "@/store/searchStore";
import { DEFAULT_FILTER_STATE, filterStateToQueryString } from "@/lib/searchParams";

const mockRouter = {
  push: vi.fn(),
  replace: vi.fn(),
};

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  usePathname: () => "/gyms",
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

vi.mock("@tanstack/react-query", () => ({
  keepPreviousData: Symbol("keepPreviousData"),
  useQuery: vi.fn(() => ({
    data: null,
    error: null,
    isError: false,
    isFetching: false,
  })),
}));

vi.mock("@/services/gyms", () => ({
  searchGyms: vi.fn().mockResolvedValue({
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
  }),
}));

vi.mock("@/services/meta", () => ({
  getPrefectures: vi.fn().mockResolvedValue([]),
  getEquipmentOptions: vi.fn().mockResolvedValue([]),
  getCities: vi.fn().mockResolvedValue([]),
}));

describe("useGymSearch popstate synchronization", () => {
  const setupGeolocation = () => {
    Object.defineProperty(window.navigator, "geolocation", {
      configurable: true,
      value: {
        getCurrentPosition: vi.fn(),
        watchPosition: vi.fn(),
        clearWatch: vi.fn(),
      },
    });
  };

  const resetStore = () => {
    useSearchStore.setState({
      filters: DEFAULT_FILTER_STATE,
      queryString: filterStateToQueryString(DEFAULT_FILTER_STATE),
      navigationSource: "initial",
      scrollPositions: {},
    });
  };

  beforeEach(() => {
    setupGeolocation();
    resetStore();
    window.history.replaceState(null, "", "http://localhost/gyms");
    mockRouter.push.mockClear();
    mockRouter.replace.mockClear();
  });

  it("updates the search store when the browser popstate event fires", async () => {
    window.history.replaceState(null, "", "http://localhost/gyms?pref=tokyo");

    const { unmount } = renderHook(() => useGymSearch());

    await waitFor(() => {
      expect(useSearchStore.getState().filters.pref).toBe("tokyo");
    });

    act(() => {
      const next = { ...DEFAULT_FILTER_STATE, pref: "kanagawa" };
      useSearchStore
        .getState()
        .setFilters(next, { queryString: filterStateToQueryString(next), force: true });
      useSearchStore.getState().setNavigationSource("push");
    });

    expect(useSearchStore.getState().filters.pref).toBe("kanagawa");

    await act(async () => {
      window.history.replaceState(null, "", "http://localhost/gyms?pref=tokyo");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });

    await waitFor(() => {
      expect(useSearchStore.getState().filters.pref).toBe("tokyo");
    });
    expect(useSearchStore.getState().navigationSource).toBe("pop");
    expect(useSearchStore.getState().queryString).toContain("pref=tokyo");

    unmount();
  });
});
