import { act, renderHook } from "@testing-library/react";
import { vi } from "vitest";

import { ApiError } from "@/lib/apiClient";
import { DEFAULT_DISTANCE_KM, DEFAULT_FILTER_STATE } from "@/lib/searchParams";
import { FALLBACK_LOCATION, useGymSearch } from "@/hooks/useGymSearch";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import type { ReadonlyURLSearchParams } from "next/navigation";
import { searchGyms } from "@/services/gyms";
import { getPrefectures, getEquipmentCategories, getCities } from "@/services/meta";

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
  useSearchParams: vi.fn(),
  usePathname: vi.fn(),
}));

vi.mock("@/services/gyms", () => ({
  searchGyms: vi.fn(),
}));

vi.mock("@/services/meta", () => ({
  getPrefectures: vi.fn(),
  getEquipmentCategories: vi.fn(),
  getCities: vi.fn(),
}));

const mockedUseRouter = vi.mocked(useRouter);
const mockedUseSearchParams = vi.mocked(useSearchParams);
const mockedUsePathname = vi.mocked(usePathname);
const mockedSearchGyms = vi.mocked(searchGyms);
const mockedGetPrefectures = vi.mocked(getPrefectures);
const mockedGetEquipmentCategories = vi.mocked(getEquipmentCategories);
const mockedGetCities = vi.mocked(getCities);

class TestReadonlyURLSearchParams extends URLSearchParams {
  append(): void {
    throw new Error("append is not supported in tests");
  }

  delete(): void {
    throw new Error("delete is not supported in tests");
  }

  set(): void {
    throw new Error("set is not supported in tests");
  }

  sort(): void {
    super.sort();
  }
}

const createSearchParams = (init: string = ""): ReadonlyURLSearchParams => {
  return new TestReadonlyURLSearchParams(init) as unknown as ReadonlyURLSearchParams;
};

describe("useGymSearch", () => {
  const mockRouter = {
    push: vi.fn(),
    replace: vi.fn(),
  };
  let originalGeolocation: Geolocation | undefined;

  beforeEach(() => {
    vi.useFakeTimers();
    originalGeolocation = navigator.geolocation;
    const geolocationError = {
      code: 1,
      PERMISSION_DENIED: 1,
      POSITION_UNAVAILABLE: 2,
      TIMEOUT: 3,
      message: "Permission denied",
    } as GeolocationPositionError;
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: {
        getCurrentPosition: vi.fn((_, error) => {
          error?.(geolocationError);
        }),
        watchPosition: vi.fn(),
        clearWatch: vi.fn(),
      } as Geolocation,
    });
    mockedUseRouter.mockReturnValue(mockRouter as unknown as ReturnType<typeof useRouter>);
    mockedUsePathname.mockReturnValue("/gyms");
    mockedUseSearchParams.mockReturnValue(createSearchParams());
    mockedSearchGyms.mockResolvedValue({
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
    });
    mockedGetPrefectures.mockResolvedValue([
      { value: "tokyo", label: "Tokyo" },
      { value: "chiba", label: "Chiba" },
    ]);
    mockedGetEquipmentCategories.mockResolvedValue([
      { value: "free-weight", label: "Free Weight" },
    ]);
    mockedGetCities.mockResolvedValue([{ value: "shinjuku", label: "Shinjuku" }]);
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
    vi.clearAllMocks();
    if (originalGeolocation) {
      Object.defineProperty(navigator, "geolocation", {
        configurable: true,
        value: originalGeolocation,
      });
    } else {
      // read-only プロパティで delete 不可のため、undefined で再定義
      Object.defineProperty(navigator, "geolocation", {
        configurable: true,
        value: undefined,
      });
    }
  });

  it("derives the initial state from query parameters", async () => {
    mockedUseSearchParams.mockReturnValue(
      createSearchParams(
        "q=bench&pref=tokyo&city=shinjuku&cats=squat-rack&sort=name&order=asc&page=2&per_page=30&radius_km=15",
      ),
    );

    const { result } = renderHook(() => useGymSearch());

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.formState.q).toBe("bench");
    expect(result.current.formState.prefecture).toBe("tokyo");
    expect(result.current.formState.city).toBe("shinjuku");
    expect(result.current.formState.categories).toEqual(["squat-rack"]);
    expect(result.current.formState.sort).toBe("name");
    expect(result.current.formState.order).toBe("asc");
    expect(result.current.formState.distance).toBe(15);
    expect(result.current.formState.lat).toBeCloseTo(FALLBACK_LOCATION.lat);
    expect(result.current.formState.lng).toBeCloseTo(FALLBACK_LOCATION.lng);
    expect(result.current.page).toBe(1);
    expect(result.current.limit).toBe(30);
  });

  it("updates the keyword with debounce and pushes a new URL", async () => {
    const { result } = renderHook(() => useGymSearch({ debounceMs: 200 }));

    await act(async () => {
      await Promise.resolve();
    });

    mockRouter.push.mockClear();

    await act(async () => {
      result.current.updateKeyword("bench");
    });

    expect(mockRouter.push).not.toHaveBeenCalled();

    await act(async () => {
      vi.advanceTimersByTime(200);
      await Promise.resolve();
    });

    expect(mockRouter.push).toHaveBeenCalledWith(
      `/gyms?q=bench&sort=rating&order=desc&radius_km=${DEFAULT_DISTANCE_KM}&lat=${FALLBACK_LOCATION.lat.toFixed(6)}&lng=${FALLBACK_LOCATION.lng.toFixed(6)}`,
      {
        scroll: false,
      },
    );
  });

  it("updates form state when search params change after navigation", async () => {
    let currentParams = createSearchParams(
      `lat=${FALLBACK_LOCATION.lat}&lng=${FALLBACK_LOCATION.lng}&radius_km=${DEFAULT_DISTANCE_KM}`,
    );
    mockedUseSearchParams.mockImplementation(() => currentParams);

    const { result, rerender } = renderHook(() => useGymSearch({ debounceMs: 0 }));

    await act(async () => {
      await Promise.resolve();
    });

    mockRouter.push.mockClear();

    await act(async () => {
      result.current.updateKeyword("bench");
    });

    await act(async () => {
      vi.runOnlyPendingTimers();
      await Promise.resolve();
    });

    expect(mockRouter.push).toHaveBeenCalledWith(
      `/gyms?q=bench&sort=rating&order=desc&radius_km=${DEFAULT_DISTANCE_KM}&lat=${FALLBACK_LOCATION.lat.toFixed(6)}&lng=${FALLBACK_LOCATION.lng.toFixed(6)}`,
      { scroll: false },
    );

    currentParams = createSearchParams(
      `q=bench&sort=rating&order=desc&radius_km=${DEFAULT_DISTANCE_KM}&lat=${FALLBACK_LOCATION.lat.toFixed(6)}&lng=${FALLBACK_LOCATION.lng.toFixed(6)}`,
    );

    await act(async () => {
      rerender();
      await Promise.resolve();
    });

    expect(result.current.formState.q).toBe("bench");
    expect(result.current.formState.lat).toBeCloseTo(FALLBACK_LOCATION.lat);
    expect(result.current.formState.lng).toBeCloseTo(FALLBACK_LOCATION.lng);
    expect(mockedSearchGyms).toHaveBeenLastCalledWith(
      expect.objectContaining({
        q: "bench",
        page: 1,
        order: "desc",
        radiusKm: DEFAULT_DISTANCE_KM,
        lat: expect.any(Number),
        lng: expect.any(Number),
      }),
      { signal: expect.any(AbortSignal) },
    );
  });

  it("changes page immediately without debounce", async () => {
    let currentParams = createSearchParams(
      `lat=${FALLBACK_LOCATION.lat}&lng=${FALLBACK_LOCATION.lng}&radius_km=${DEFAULT_DISTANCE_KM}`,
    );
    mockedUseSearchParams.mockImplementation(() => currentParams);
    mockRouter.push.mockImplementation((url: string) => {
      const [, query = ""] = url.split("?");
      currentParams = createSearchParams(query);
    });

    const { result } = renderHook(() => useGymSearch());

    await act(async () => {
      await Promise.resolve();
    });

    mockRouter.push.mockClear();

    await act(async () => {
      result.current.setPage(3);
    });

    const lastPush = mockRouter.push.mock.calls.at(-1);
    expect(lastPush).toBeDefined();
    const [pageUrl, options] = lastPush!;
    expect(pageUrl).toContain("sort=rating");
    expect(pageUrl).toContain("order=desc");
    expect(pageUrl).toContain("page=3");
    expect(pageUrl).toContain(`radius_km=${DEFAULT_DISTANCE_KM}`);
    expect(pageUrl).toContain(`lat=${FALLBACK_LOCATION.lat.toFixed(6)}`);
    expect(pageUrl).toContain(`lng=${FALLBACK_LOCATION.lng.toFixed(6)}`);
    expect(options).toEqual({ scroll: false });
  });

  it("updates sort and order while resetting the page", async () => {
    let currentParams = createSearchParams("page=3&sort=rating&order=desc");
    mockedUseSearchParams.mockImplementation(() => currentParams);
    mockRouter.push.mockImplementation((url: string) => {
      const [, query = ""] = url.split("?");
      currentParams = createSearchParams(query);
    });

    const { result, rerender } = renderHook(() => useGymSearch({ debounceMs: 0 }));

    await act(async () => {
      await Promise.resolve();
    });

    mockRouter.push.mockClear();

    await act(async () => {
      result.current.updateSort("reviews", "desc");
    });

    await act(async () => {
      vi.runOnlyPendingTimers();
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
    expect(mockedSearchGyms).toHaveBeenLastCalledWith(
      expect.objectContaining({
        sort: "reviews",
        order: "desc",
        page: 1,
        radiusKm: DEFAULT_DISTANCE_KM,
        lat: expect.any(Number),
        lng: expect.any(Number),
      }),
      { signal: expect.any(AbortSignal) },
    );

    mockRouter.push.mockImplementation(() => {});
  });

  it("clears filters and keeps the current per-page value", async () => {
    mockedUseSearchParams.mockReturnValue(
      createSearchParams("q=bench&pref=tokyo&cats=squat-rack&page=2&per_page=24&radius_km=10"),
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
    expect(mockRouter.push).toHaveBeenCalledWith(expect.stringContaining("page_size=24"), {
      scroll: false,
    });
    const [url] = mockRouter.push.mock.calls[0];
    expect(url).toContain("sort=rating");
    expect(url).toContain("order=desc");
    expect(url).toContain(`radius_km=${DEFAULT_DISTANCE_KM}`);
    expect(url).toContain(`lat=${FALLBACK_LOCATION.lat.toFixed(6)}`);
    expect(url).toContain(`lng=${FALLBACK_LOCATION.lng.toFixed(6)}`);
    expect(result.current.formState).toEqual({
      q: "",
      prefecture: "",
      city: "",
      categories: [],
      sort: DEFAULT_FILTER_STATE.sort,
      order: DEFAULT_FILTER_STATE.order,
      distance: DEFAULT_DISTANCE_KM,
      lat: FALLBACK_LOCATION.lat,
      lng: FALLBACK_LOCATION.lng,
    });
  });

  it("applies location coordinates from query parameters", async () => {
    mockedUseSearchParams.mockReturnValue(
      createSearchParams("lat=35.1234&lng=139.9876&radius_km=8"),
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
    expect(mockedSearchGyms).toHaveBeenCalledWith(
      expect.objectContaining({
        lat: 35.1234,
        lng: 139.9876,
        radiusKm: 8,
      }),
      { signal: expect.any(AbortSignal) },
    );
  });

  it("retains location information when clearing filters", async () => {
    mockedUseSearchParams.mockReturnValue(
      createSearchParams("lat=34&lng=135&per_page=24&radius_km=12"),
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
    expect(url).toContain("page_size=24");
    expect(url).toContain("lat=34.000000");
    expect(url).toContain("lng=135.000000");
    expect(url).toContain("sort=rating");
    expect(url).toContain("order=desc");
    expect(url).toContain(`radius_km=${DEFAULT_DISTANCE_KM}`);
    expect(options).toEqual({ scroll: false });
    expect(result.current.formState.lat).toBeCloseTo(34);
    expect(result.current.formState.lng).toBeCloseTo(135);
    expect(result.current.formState.distance).toBe(DEFAULT_DISTANCE_KM);
    expect(result.current.formState.order).toBe(DEFAULT_FILTER_STATE.order);
  });

  it("clears coordinates and resets sorting when the current location is cleared", async () => {
    let currentParams = createSearchParams(
      "sort=distance&order=asc&lat=35.6&lng=139.7&radius_km=5",
    );
    mockedUseSearchParams.mockImplementation(() => currentParams);
    mockRouter.push.mockImplementation((url: string) => {
      const [, query = ""] = url.split("?");
      currentParams = createSearchParams(query);
    });

    const { result, rerender } = renderHook(() => useGymSearch({ debounceMs: 0 }));

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.appliedFilters.sort).toBe("distance");
    expect(result.current.appliedFilters.lat).toBeCloseTo(35.6);

    mockRouter.push.mockClear();
    mockedSearchGyms.mockClear();

    await act(async () => {
      result.current.clearLocation();
    });

    expect(mockRouter.push).toHaveBeenCalledTimes(1);
    const [url, options] = mockRouter.push.mock.calls[0];
    expect(url).toContain(`sort=${DEFAULT_FILTER_STATE.sort}`);
    expect(url).toContain(`order=${DEFAULT_FILTER_STATE.order}`);
    expect(url).not.toContain("lat=");
    expect(url).not.toContain("lng=");
    expect(url).not.toContain("radius_km=");
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

    expect(mockedSearchGyms).toHaveBeenCalledTimes(1);
    const firstCall = mockedSearchGyms.mock.calls[0]!;
    const params = firstCall[0]!;
    expect(params.sort).toBe(DEFAULT_FILTER_STATE.sort);
    expect(params.lat ?? null).toBeNull();
    expect(params.lng ?? null).toBeNull();

    mockRouter.push.mockImplementation(() => {});
  });

  it("updates the search radius and resets the page", async () => {
    let currentParams = createSearchParams("lat=35.6&lng=139.7&radius_km=5&page=3");
    mockedUseSearchParams.mockImplementation(() => currentParams);
    mockRouter.push.mockImplementation((url: string) => {
      const [, query = ""] = url.split("?");
      currentParams = createSearchParams(query);
    });

    const { result, rerender } = renderHook(() => useGymSearch({ debounceMs: 0 }));

    await act(async () => {
      await Promise.resolve();
    });

    mockRouter.push.mockClear();

    await act(async () => {
      result.current.updateDistance(12);
    });

    await act(async () => {
      vi.runOnlyPendingTimers();
      await Promise.resolve();
    });

    expect(mockRouter.push).toHaveBeenLastCalledWith(
      `/gyms?sort=rating&order=desc&radius_km=12&lat=35.600000&lng=139.700000`,
      { scroll: false },
    );

    await act(async () => {
      rerender();
      await Promise.resolve();
    });

    expect(result.current.appliedFilters.page).toBe(1);
    expect(result.current.appliedFilters.distance).toBe(12);
    expect(result.current.appliedFilters.lat).toBeCloseTo(35.6);
    expect(result.current.appliedFilters.lng).toBeCloseTo(139.7);

    mockRouter.push.mockImplementation(() => {});
  });

  it("restores fallback coordinates when distance sorting lacks an explicit location", async () => {
    let currentParams = createSearchParams("sort=distance&order=asc");
    mockedUseSearchParams.mockImplementation(() => currentParams);
    mockRouter.push.mockImplementation((url: string) => {
      const [, query = ""] = url.split("?");
      currentParams = createSearchParams(query);
    });

    mockedSearchGyms.mockClear();

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

    expect(mockedSearchGyms).toHaveBeenCalledTimes(1);
    const firstCall = mockedSearchGyms.mock.calls[0]!;
    const params = firstCall[0]!;
    expect(params.lat).toBeCloseTo(FALLBACK_LOCATION.lat);
    expect(params.lng).toBeCloseTo(FALLBACK_LOCATION.lng);
    expect(params.radiusKm).toBe(DEFAULT_DISTANCE_KM);

    mockRouter.push.mockImplementation(() => {});
  });

  it("surfaces API errors from searchGyms as error state", async () => {
    const error = new ApiError("検索に失敗しました", 500);
    mockedSearchGyms.mockRejectedValue(error);

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

    mockedSearchGyms
      .mockResolvedValueOnce({
        items: firstPageItems,
        meta: {
          total: 5,
          page: 1,
          perPage: 20,
          hasNext: true,
          hasPrev: false,
          hasMore: true,
          pageToken: null,
        },
      })
      .mockResolvedValueOnce({
        items: secondPageItems,
        meta: {
          total: 5,
          page: 2,
          perPage: 20,
          hasNext: false,
          hasPrev: true,
          hasMore: false,
          pageToken: null,
        },
      });

    let currentParams = createSearchParams(
      `lat=${FALLBACK_LOCATION.lat}&lng=${FALLBACK_LOCATION.lng}&radius_km=${DEFAULT_DISTANCE_KM}`,
    );
    mockedUseSearchParams.mockImplementation(() => currentParams);
    mockRouter.push.mockImplementation((url: string) => {
      const [, query = ""] = url.split("?");
      currentParams = createSearchParams(query);
    });

    const { result, rerender } = renderHook(() => useGymSearch());

    await act(async () => {
      await Promise.resolve();
    });

    mockRouter.push.mockClear();

    expect(result.current.items).toEqual(firstPageItems);

    await act(async () => {
      result.current.loadNextPage();
    });

    const pushArgs = mockRouter.push.mock.calls.at(-1);
    expect(pushArgs).toBeDefined();
    const [nextUrl, nextOptions] = pushArgs!;
    expect(nextUrl).toContain("sort=rating");
    expect(nextUrl).toContain("order=desc");
    expect(nextUrl).toContain("page=2");
    expect(nextUrl).toContain(`radius_km=${DEFAULT_DISTANCE_KM}`);
    expect(nextUrl).toContain(`lat=${FALLBACK_LOCATION.lat.toFixed(6)}`);
    expect(nextUrl).toContain(`lng=${FALLBACK_LOCATION.lng.toFixed(6)}`);
    expect(nextOptions).toEqual({ scroll: false });

    await act(async () => {
      rerender();
      await Promise.resolve();
    });

    expect(result.current.items.map(item => item.id)).toEqual([1, 2, 3]);
    expect(result.current.meta.hasNext).toBe(false);
    expect(mockedSearchGyms).toHaveBeenCalledTimes(2);
  });

  it("does not navigate when requesting the next page without additional results", async () => {
    let standaloneParams = createSearchParams(
      `lat=${FALLBACK_LOCATION.lat}&lng=${FALLBACK_LOCATION.lng}&radius_km=${DEFAULT_DISTANCE_KM}`,
    );
    mockedUseSearchParams.mockImplementation(() => standaloneParams);
    mockRouter.push.mockImplementation((url: string) => {
      const [, query = ""] = url.split("?");
      standaloneParams = createSearchParams(query);
    });

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
