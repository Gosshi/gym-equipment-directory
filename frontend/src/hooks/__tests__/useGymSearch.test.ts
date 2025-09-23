import { act, renderHook } from "@testing-library/react";

import { ApiError } from "@/lib/apiClient";
import { DEFAULT_DISTANCE_KM } from "@/lib/searchParams";
import { useGymSearch } from "@/hooks/useGymSearch";

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

const DEFAULT_LOCATION_QUERY = "lat=35.681236&lng=139.767125";
const DEFAULT_LOCATION = { lat: 35.681236, lng: 139.767125 };

describe("useGymSearch", () => {
  const mockRouter = {
    push: jest.fn(),
    replace: jest.fn(),
  };

  beforeEach(() => {
    jest.useFakeTimers();
    useRouter.mockReturnValue(mockRouter);
    usePathname.mockReturnValue("/gyms");
    useSearchParams.mockReturnValue(new URLSearchParams(DEFAULT_LOCATION_QUERY));
    searchGyms.mockResolvedValue({
      items: [],
      meta: { total: 0, hasNext: false, pageToken: null },
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
        `q=bench&pref=tokyo&city=shinjuku&cats=squat-rack&sort=newest&page=2&limit=30&distance_km=15&${DEFAULT_LOCATION_QUERY}`,
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
      sort: "newest",
      distance: 15,
    });
    expect(result.current.page).toBe(2);
    expect(result.current.limit).toBe(30);
    expect(result.current.location).toEqual(DEFAULT_LOCATION);
    expect(searchGyms).toHaveBeenCalledWith(
      {
        q: "bench",
        prefecture: "tokyo",
        city: "shinjuku",
        categories: ["squat-rack"],
        sort: "newest",
        page: 2,
        limit: 30,
        lat: DEFAULT_LOCATION.lat,
        lng: DEFAULT_LOCATION.lng,
        distanceKm: 15,
      },
      { signal: expect.any(AbortSignal) },
    );
  });

  it("shows a location error and skips fetching when coordinates are missing", async () => {
    useSearchParams.mockReturnValue(new URLSearchParams());

    const { result } = renderHook(() => useGymSearch());

    await act(async () => {
      await Promise.resolve();
    });

    expect(searchGyms).not.toHaveBeenCalled();
    expect(result.current.error).toEqual({ message: "位置を指定してください", type: "client" });
    expect(result.current.items).toEqual([]);
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

    expect(mockRouter.push).toHaveBeenCalledWith(
      `/gyms?q=bench&${DEFAULT_LOCATION_QUERY}`,
      { scroll: false },
    );
  });

  it("updates form state when search params change after navigation", async () => {
    let currentParams = new URLSearchParams(DEFAULT_LOCATION_QUERY);
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

    expect(mockRouter.push).toHaveBeenCalledWith(
      `/gyms?q=bench&${DEFAULT_LOCATION_QUERY}`,
      { scroll: false },
    );

    currentParams = new URLSearchParams(`q=bench&${DEFAULT_LOCATION_QUERY}`);

    await act(async () => {
      rerender();
      await Promise.resolve();
    });

    expect(result.current.formState.q).toBe("bench");
    expect(searchGyms).toHaveBeenLastCalledWith(
      expect.objectContaining({
        q: "bench",
        page: 1,
        lat: DEFAULT_LOCATION.lat,
        lng: DEFAULT_LOCATION.lng,
        distanceKm: DEFAULT_DISTANCE_KM,
      }),
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

    expect(mockRouter.push).toHaveBeenCalledWith(
      `/gyms?page=3&${DEFAULT_LOCATION_QUERY}`,
      { scroll: false },
    );
  });

  it("clears filters and keeps the current per-page value", async () => {
    useSearchParams.mockReturnValue(
      new URLSearchParams(
        `q=bench&pref=tokyo&cats=squat-rack&page=2&limit=24&distance_km=10&${DEFAULT_LOCATION_QUERY}`,
      ),
    );

    const { result } = renderHook(() => useGymSearch());

    await act(async () => {
      await Promise.resolve();
    });

    await act(async () => {
      result.current.clearFilters();
    });

    expect(mockRouter.push).toHaveBeenCalledWith(
      `/gyms?limit=24&${DEFAULT_LOCATION_QUERY}`,
      { scroll: false },
    );
    expect(result.current.formState).toEqual({
      q: "",
      prefecture: "",
      city: "",
      categories: [],
      sort: "popular",
      distance: DEFAULT_DISTANCE_KM,
    });
  });

  it("surfaces API errors from searchGyms as error state", async () => {
    const error = new ApiError("検索に失敗しました", 500);
    searchGyms.mockRejectedValueOnce(error);

    const { result } = renderHook(() => useGymSearch());

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.error).toEqual({
      message: "検索に失敗しました",
      status: 500,
      type: "server",
    });
  });

  it("marks 4xx API errors as client errors", async () => {
    const error = new ApiError("無効なリクエスト", 422);
    searchGyms.mockRejectedValueOnce(error);

    const { result } = renderHook(() => useGymSearch());

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.error).toEqual({
      message: "無効なリクエスト",
      status: 422,
      type: "client",
    });
  });

  it("issues a single fetch after rapid keyword changes", async () => {
    let currentParams = new URLSearchParams(DEFAULT_LOCATION_QUERY);
    useSearchParams.mockImplementation(() => currentParams);
    mockRouter.push.mockImplementation((url: string) => {
      const [, query = ""] = url.split("?");
      currentParams = new URLSearchParams(query);
    });

    const { result, rerender } = renderHook(() => useGymSearch({ debounceMs: 150 }));

    await act(async () => {
      await Promise.resolve();
    });

    searchGyms.mockClear();

    await act(async () => {
      result.current.updateKeyword("b");
      result.current.updateKeyword("be");
      result.current.updateKeyword("bench");
    });

    await act(async () => {
      jest.advanceTimersByTime(150);
      await Promise.resolve();
    });

    await act(async () => {
      rerender();
      await Promise.resolve();
    });

    expect(searchGyms).toHaveBeenCalledTimes(1);
    expect(searchGyms).toHaveBeenCalledWith(
      expect.objectContaining({
        q: "bench",
        page: 1,
        lat: DEFAULT_LOCATION.lat,
        lng: DEFAULT_LOCATION.lng,
        distanceKm: DEFAULT_DISTANCE_KM,
      }),
      { signal: expect.any(AbortSignal) },
    );
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
        meta: { total: 5, hasNext: true, pageToken: null },
      })
      .mockResolvedValueOnce({
        items: secondPageItems,
        meta: { total: 5, hasNext: false, pageToken: null },
      });

    let currentParams = new URLSearchParams(DEFAULT_LOCATION_QUERY);
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
      `/gyms?page=2&${DEFAULT_LOCATION_QUERY}`,
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
