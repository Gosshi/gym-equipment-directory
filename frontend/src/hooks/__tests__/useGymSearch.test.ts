import { act, renderHook } from "@testing-library/react";

import { ApiError } from "@/lib/apiClient";
import { DEFAULT_DISTANCE_KM, DEFAULT_FILTER_STATE } from "@/lib/searchParams";
import { FALLBACK_LOCATION, useGymSearch } from "@/hooks/useGymSearch";

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
  useSearchParams: jest.fn(),
  usePathname: jest.fn(),
}));

jest.mock("@/services/gyms", () => ({
  searchGyms: jest.fn(),
}));

jest.mock("@/services/meta", () => ({
  getPrefectures: jest.fn(),
  getEquipmentCategories: jest.fn(),
  getCities: jest.fn(),
}));

const { useRouter, useSearchParams, usePathname } = jest.requireMock("next/navigation") as {
  useRouter: jest.Mock;
  useSearchParams: jest.Mock;
  usePathname: jest.Mock;
};

const { searchGyms } = jest.requireMock("@/services/gyms") as {
  searchGyms: jest.Mock;
};

const { getPrefectures, getEquipmentCategories, getCities } =
  jest.requireMock("@/services/meta") as {
    getPrefectures: jest.Mock;
    getEquipmentCategories: jest.Mock;
    getCities: jest.Mock;
  };

describe("useGymSearch", () => {
  const mockRouter = {
    push: jest.fn(),
    replace: jest.fn(),
  };

  beforeEach(() => {
    jest.useFakeTimers();
    useRouter.mockReturnValue(mockRouter);
    usePathname.mockReturnValue("/gyms");
    useSearchParams.mockReturnValue(new URLSearchParams());
    searchGyms.mockResolvedValue({
      items: [],
      meta: { total: 0, page: 1, perPage: 20, hasNext: false, hasPrev: false, pageToken: null },
    });
    getPrefectures.mockResolvedValue([
      { value: "tokyo", label: "Tokyo" },
      { value: "chiba", label: "Chiba" },
    ]);
    getEquipmentCategories.mockResolvedValue([
      { value: "free-weight", label: "Free Weight" },
    ]);
    getCities.mockResolvedValue([{ value: "shinjuku", label: "Shinjuku" }]);
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  it("derives the initial state from query parameters", async () => {
    useSearchParams.mockReturnValue(
      new URLSearchParams(
        "q=bench&pref=tokyo&city=shinjuku&cats=squat-rack&sort=name&order=asc&page=2&per_page=30&distance=15",
      ),
    );

    const { result } = renderHook(() => useGymSearch());

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.formState).toEqual({
      q: "bench",
      prefecture: "tokyo",
      city: "shinjuku",
      categories: ["squat-rack"],
      sort: "name",
      order: "asc",
      distance: 15,
      lat: null,
      lng: null,
    });
    expect(result.current.page).toBe(2);
    expect(result.current.limit).toBe(30);
    expect(searchGyms).toHaveBeenCalledWith(
      {
        q: "bench",
        prefecture: "tokyo",
        city: "shinjuku",
        categories: ["squat-rack"],
        sort: "name",
        order: "asc",
        page: 2,
        limit: 30,
        perPage: 30,
      },
      { signal: expect.any(AbortSignal) },
    );
  });

  it("updates the keyword with debounce and pushes a new URL", async () => {
    const { result } = renderHook(() => useGymSearch({ debounceMs: 200 }));

    await act(async () => {
      await Promise.resolve();
    });

    await act(async () => {
      result.current.updateKeyword("bench");
    });

    expect(mockRouter.push).not.toHaveBeenCalled();

    await act(async () => {
      jest.advanceTimersByTime(200);
      await Promise.resolve();
    });

    expect(mockRouter.push).toHaveBeenCalledWith("/gyms?q=bench&sort=rating&order=desc", {
      scroll: false,
    });
  });

  it("updates form state when search params change after navigation", async () => {
    let currentParams = new URLSearchParams();
    useSearchParams.mockImplementation(() => currentParams);

    const { result, rerender } = renderHook(() => useGymSearch({ debounceMs: 0 }));

    await act(async () => {
      await Promise.resolve();
    });

    await act(async () => {
      result.current.updateKeyword("bench");
    });

    await act(async () => {
      jest.runOnlyPendingTimers();
      await Promise.resolve();
    });

    expect(mockRouter.push).toHaveBeenCalledWith("/gyms?q=bench&sort=rating&order=desc", {
      scroll: false,
    });

    currentParams = new URLSearchParams("q=bench&sort=rating&order=desc");

    await act(async () => {
      rerender();
      await Promise.resolve();
    });

    expect(result.current.formState.q).toBe("bench");
    expect(searchGyms).toHaveBeenLastCalledWith(
      expect.objectContaining({ q: "bench", page: 1, order: "desc" }),
      { signal: expect.any(AbortSignal) },
    );
  });

  it("changes page immediately without debounce", async () => {
    const { result } = renderHook(() => useGymSearch());

    await act(async () => {
      await Promise.resolve();
    });

    await act(async () => {
      result.current.setPage(3);
    });

    expect(mockRouter.push).toHaveBeenCalledWith("/gyms?sort=rating&order=desc&page=3", {
      scroll: false,
    });
  });

  it("updates sort and order while resetting the page", async () => {
    let currentParams = new URLSearchParams("page=3&sort=rating&order=desc");
    useSearchParams.mockImplementation(() => currentParams);
    mockRouter.push.mockImplementation((url: string) => {
      const [, query = ""] = url.split("?");
      currentParams = new URLSearchParams(query);
    });

    const { result, rerender } = renderHook(() => useGymSearch({ debounceMs: 0 }));

    await act(async () => {
      await Promise.resolve();
    });

    await act(async () => {
      result.current.updateSort("reviews", "desc");
    });

    await act(async () => {
      jest.runOnlyPendingTimers();
      await Promise.resolve();
    });

    const lastCall = mockRouter.push.mock.calls.at(-1);
    expect(lastCall).toBeDefined();
    const [url] = lastCall!;
    expect(url).toContain("sort=reviews");
    expect(url).toContain("order=desc");
    expect(url).not.toContain("page=3");

    await act(async () => {
      rerender();
      await Promise.resolve();
    });

    expect(result.current.appliedFilters.sort).toBe("reviews");
    expect(result.current.appliedFilters.page).toBe(1);
    expect(searchGyms).toHaveBeenLastCalledWith(
      expect.objectContaining({ sort: "reviews", order: "desc", page: 1 }),
      { signal: expect.any(AbortSignal) },
    );

    mockRouter.push.mockImplementation(() => {});
  });

  it("clears filters and keeps the current per-page value", async () => {
    useSearchParams.mockReturnValue(
      new URLSearchParams(
        "q=bench&pref=tokyo&cats=squat-rack&page=2&per_page=24&distance=10",
      ),
    );

    const { result } = renderHook(() => useGymSearch());

    await act(async () => {
      await Promise.resolve();
    });

    await act(async () => {
      result.current.clearFilters();
    });

    expect(mockRouter.push).toHaveBeenCalled();
    expect(mockRouter.push).toHaveBeenCalledWith(
      expect.stringContaining("per_page=24"),
      { scroll: false },
    );
    const [url] = mockRouter.push.mock.calls[0];
    expect(url).toContain("sort=rating");
    expect(url).toContain("order=desc");
    expect(result.current.formState).toEqual({
      q: "",
      prefecture: "",
      city: "",
      categories: [],
      sort: DEFAULT_FILTER_STATE.sort,
      order: DEFAULT_FILTER_STATE.order,
      distance: DEFAULT_DISTANCE_KM,
      lat: null,
      lng: null,
    });
  });

  it("applies location coordinates from query parameters", async () => {
    useSearchParams.mockReturnValue(
      new URLSearchParams("lat=35.1234&lng=139.9876&distance=8"),
    );

    const { result } = renderHook(() => useGymSearch());

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.formState.lat).toBeCloseTo(35.1234);
    expect(result.current.formState.lng).toBeCloseTo(139.9876);
    expect(result.current.location.mode).toBe("manual");
    expect(result.current.location.status).toBe("success");
    expect(result.current.location.isFallback).toBe(false);
    expect(result.current.location.fallbackLabel).toBeNull();
    expect(searchGyms).toHaveBeenCalledWith(
      expect.objectContaining({
        lat: 35.1234,
        lng: 139.9876,
        distance: 8,
      }),
      { signal: expect.any(AbortSignal) },
    );
  });

  it("retains location information when clearing filters", async () => {
    useSearchParams.mockReturnValue(
      new URLSearchParams("lat=34&lng=135&per_page=24&distance=12"),
    );

    const { result } = renderHook(() => useGymSearch());

    await act(async () => {
      await Promise.resolve();
    });

    mockRouter.push.mockClear();

    await act(async () => {
      result.current.clearFilters();
    });

    expect(mockRouter.push).toHaveBeenCalled();
    const [url, options] = mockRouter.push.mock.calls[0];
    expect(url).toContain("per_page=24");
    expect(url).toContain("lat=34.000000");
    expect(url).toContain("lng=135.000000");
    expect(url).toContain("sort=rating");
    expect(url).toContain("order=desc");
    expect(options).toEqual({ scroll: false });
    expect(result.current.formState.lat).toBeCloseTo(34);
    expect(result.current.formState.lng).toBeCloseTo(135);
    expect(result.current.formState.distance).toBe(DEFAULT_DISTANCE_KM);
    expect(result.current.formState.order).toBe(DEFAULT_FILTER_STATE.order);
  });

  it("clears coordinates and resets sorting when the current location is cleared", async () => {
    let currentParams = new URLSearchParams(
      "sort=distance&order=asc&lat=35.6&lng=139.7&distance=5",
    );
    useSearchParams.mockImplementation(() => currentParams);
    mockRouter.push.mockImplementation((url: string) => {
      const [, query = ""] = url.split("?");
      currentParams = new URLSearchParams(query);
    });

    const { result, rerender } = renderHook(() => useGymSearch({ debounceMs: 0 }));

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.appliedFilters.sort).toBe("distance");
    expect(result.current.appliedFilters.lat).toBeCloseTo(35.6);

    mockRouter.push.mockClear();
    searchGyms.mockClear();

    await act(async () => {
      result.current.clearLocation();
    });

    expect(mockRouter.push).toHaveBeenCalledTimes(1);
    const [url, options] = mockRouter.push.mock.calls[0];
    expect(url).toContain(`sort=${DEFAULT_FILTER_STATE.sort}`);
    expect(url).toContain(`order=${DEFAULT_FILTER_STATE.order}`);
    expect(url).not.toContain("lat=");
    expect(url).not.toContain("lng=");
    expect(options).toEqual({ scroll: false });

    await act(async () => {
      rerender();
      await Promise.resolve();
    });

    expect(result.current.appliedFilters.sort).toBe(DEFAULT_FILTER_STATE.sort);
    expect(result.current.appliedFilters.lat).toBeNull();
    expect(result.current.appliedFilters.lng).toBeNull();
    expect(result.current.location.mode).toBe("off");
    expect(result.current.location.isFallback).toBe(false);
    expect(result.current.formState.lat).toBeNull();
    expect(result.current.formState.lng).toBeNull();

    expect(searchGyms).toHaveBeenCalledTimes(1);
    const [params] = searchGyms.mock.calls[0];
    expect(params.sort).toBe(DEFAULT_FILTER_STATE.sort);
    expect(params.lat ?? null).toBeNull();
    expect(params.lng ?? null).toBeNull();

    mockRouter.push.mockImplementation(() => {});
  });

  it("restores fallback coordinates when distance sorting lacks an explicit location", async () => {
    let currentParams = new URLSearchParams("sort=distance&order=asc");
    useSearchParams.mockImplementation(() => currentParams);
    mockRouter.push.mockImplementation((url: string) => {
      const [, query = ""] = url.split("?");
      currentParams = new URLSearchParams(query);
    });

    searchGyms.mockClear();

    const { result, rerender } = renderHook(() => useGymSearch({ debounceMs: 0 }));

    await act(async () => {
      await Promise.resolve();
    });

    expect(mockRouter.push).toHaveBeenCalled();
    const [url] = mockRouter.push.mock.calls[0];
    expect(url).toContain("sort=distance");
    expect(url).toContain("order=asc");
    expect(url).toContain(`lat=${FALLBACK_LOCATION.lat.toFixed(6)}`);
    expect(url).toContain(`lng=${FALLBACK_LOCATION.lng.toFixed(6)}`);

    await act(async () => {
      rerender();
      await Promise.resolve();
    });

    expect(result.current.appliedFilters.lat).toBeCloseTo(FALLBACK_LOCATION.lat);
    expect(result.current.appliedFilters.lng).toBeCloseTo(FALLBACK_LOCATION.lng);
    expect(result.current.location.mode).toBe("fallback");
    expect(result.current.location.isFallback).toBe(true);

    expect(searchGyms).toHaveBeenCalledTimes(1);
    const [params] = searchGyms.mock.calls[0];
    expect(params.lat).toBeCloseTo(FALLBACK_LOCATION.lat);
    expect(params.lng).toBeCloseTo(FALLBACK_LOCATION.lng);

    mockRouter.push.mockImplementation(() => {});
  });

  it("surfaces API errors from searchGyms as error state", async () => {
    const error = new ApiError("検索に失敗しました", 500);
    searchGyms.mockRejectedValueOnce(error);

    const { result } = renderHook(() => useGymSearch());

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.error).toBe("検索に失敗しました");
  });

  it("appends additional results when loadNextPage is invoked", async () => {
    const firstPageItems = [
      { id: 1, slug: "gym-1", name: "Gym 1", city: "Shinjuku", prefecture: "Tokyo" },
      { id: 2, slug: "gym-2", name: "Gym 2", city: "Shibuya", prefecture: "Tokyo" },
    ];
    const secondPageItems = [
      { id: 2, slug: "gym-2", name: "Gym 2 (updated)", city: "Shibuya", prefecture: "Tokyo" },
      { id: 3, slug: "gym-3", name: "Gym 3", city: "Meguro", prefecture: "Tokyo" },
    ];

    searchGyms
      .mockResolvedValueOnce({
        items: firstPageItems,
        meta: { total: 5, page: 1, perPage: 20, hasNext: true, hasPrev: false, pageToken: null },
      })
      .mockResolvedValueOnce({
        items: secondPageItems,
        meta: { total: 5, page: 2, perPage: 20, hasNext: false, hasPrev: true, pageToken: null },
      });

    let currentParams = new URLSearchParams();
    useSearchParams.mockImplementation(() => currentParams);
    mockRouter.push.mockImplementation((url: string) => {
      const [, query = ""] = url.split("?");
      currentParams = new URLSearchParams(query);
    });

    const { result, rerender } = renderHook(() => useGymSearch());

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.items).toEqual(firstPageItems);

    await act(async () => {
      result.current.loadNextPage();
    });

    expect(mockRouter.push).toHaveBeenLastCalledWith(
      "/gyms?sort=rating&order=desc&page=2",
      { scroll: false },
    );

    await act(async () => {
      rerender();
      await Promise.resolve();
    });

    expect(result.current.items.map((item) => item.id)).toEqual([1, 2, 3]);
    expect(result.current.meta.hasNext).toBe(false);
    expect(searchGyms).toHaveBeenCalledTimes(2);
  });

  it("does not navigate when requesting the next page without additional results", async () => {
    const { result } = renderHook(() => useGymSearch());

    await act(async () => {
      await Promise.resolve();
    });

    mockRouter.push.mockClear();

    await act(async () => {
      result.current.loadNextPage();
    });

    expect(mockRouter.push).not.toHaveBeenCalled();
  });
});
