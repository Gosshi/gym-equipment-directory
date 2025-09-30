import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useGymSearch } from "../useGymSearch";
import { DEFAULT_FILTER_STATE, filterStateToQueryString } from "@/lib/searchParams";
import { useSearchStore } from "@/store/searchStore";

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

const syncHistoryWithLastCall = (calls: unknown[][]) => {
  const lastCall = calls[calls.length - 1];
  if (!lastCall) {
    return;
  }
  const [url] = lastCall as [string];
  const target = new URL(url, "http://localhost");
  window.history.replaceState(null, "", target.toString());
};

describe("useGymSearch history navigation", () => {
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

  it("uses push navigation for filter interactions", async () => {
    const { result, unmount } = renderHook(() => useGymSearch({ debounceMs: 0 }));

    await waitFor(() => {
      expect(useSearchStore.getState().filters.page).toBe(1);
    });

    mockRouter.push.mockClear();
    mockRouter.replace.mockClear();

    act(() => {
      result.current.updatePrefecture("tokyo");
    });

    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledTimes(1);
    });
    expect(mockRouter.replace).not.toHaveBeenCalled();
    const [url] = mockRouter.push.mock.calls[0] as [string];
    expect(url).toContain("pref=tokyo");
    syncHistoryWithLastCall(mockRouter.push.mock.calls);

    unmount();
  });

  it("uses replace navigation for pagination", async () => {
    const { result, unmount } = renderHook(() => useGymSearch({ debounceMs: 0 }));

    await waitFor(() => {
      expect(result.current.page).toBe(1);
    });

    mockRouter.push.mockClear();
    mockRouter.replace.mockClear();

    act(() => {
      result.current.setPage(2);
    });

    await waitFor(() => {
      expect(mockRouter.replace).toHaveBeenCalledTimes(1);
    });
    expect(mockRouter.push).not.toHaveBeenCalled();
    const [url] = mockRouter.replace.mock.calls[0] as [string];
    expect(url).toContain("page=2");
    syncHistoryWithLastCall(mockRouter.replace.mock.calls);

    unmount();
  });

  it("skips navigation when pagination target is unchanged", async () => {
    const { result, unmount } = renderHook(() => useGymSearch({ debounceMs: 0 }));

    await waitFor(() => {
      expect(result.current.page).toBe(1);
    });

    mockRouter.push.mockClear();
    mockRouter.replace.mockClear();

    act(() => {
      result.current.setPage(1);
    });

    await waitFor(() => {
      expect(mockRouter.push).not.toHaveBeenCalled();
      expect(mockRouter.replace).not.toHaveBeenCalled();
    });

    unmount();
  });

  it("applies fallback location with replace navigation", async () => {
    const { result, unmount } = renderHook(() => useGymSearch({ debounceMs: 0 }));

    await waitFor(() => {
      expect(result.current.formState.sort).toBeTruthy();
    });

    mockRouter.push.mockClear();
    mockRouter.replace.mockClear();

    act(() => {
      result.current.updateSort("distance", "asc");
    });

    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(mockRouter.replace).toHaveBeenCalled();
    });

    const replaceCalls = mockRouter.replace.mock.calls;
    const [url] = replaceCalls[replaceCalls.length - 1] as [string];
    expect(url).toContain("lat=");
    expect(url).toContain("lng=");

    unmount();
  });

  it("keeps navigation idle when unrelated query parameters change", async () => {
    const { result, rerender, unmount } = renderHook(() => useGymSearch({ debounceMs: 0 }));

    await waitFor(() => {
      expect(result.current.page).toBe(1);
    });

    mockRouter.push.mockClear();
    mockRouter.replace.mockClear();

    act(() => {
      result.current.updatePrefecture("tokyo");
    });

    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledTimes(1);
    });
    syncHistoryWithLastCall(mockRouter.push.mock.calls);
    act(() => {
      rerender();
    });
    mockRouter.push.mockClear();
    mockRouter.replace.mockClear();

    await waitFor(() => {
      expect(useSearchStore.getState().filters.pref).toBe("tokyo");
    });

    act(() => {
      useSearchStore.getState().setNavigationSource("idle");
    });
    expect(useSearchStore.getState().navigationSource).toBe("idle");

    act(() => {
      window.history.replaceState(null, "", "http://localhost/gyms?pref=tokyo&gym=501");
    });

    act(() => {
      rerender();
    });

    await waitFor(() => {
      expect(useSearchStore.getState().navigationSource).toBe("idle");
    });

    expect(mockRouter.push).not.toHaveBeenCalled();
    expect(mockRouter.replace).not.toHaveBeenCalled();

    unmount();
  });
});
