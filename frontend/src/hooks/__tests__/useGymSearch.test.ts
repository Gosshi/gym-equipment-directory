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
        "q=bench&pref=tokyo&city=shinjuku&cats=squat-rack&sort=newest&page=2&limit=30&distance=15",
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
    expect(searchGyms).toHaveBeenCalledWith(
      {
        q: "bench",
        prefecture: "tokyo",
        city: "shinjuku",
        categories: ["squat-rack"],
        sort: "newest",
        page: 2,
        limit: 30,
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

    expect(mockRouter.push).toHaveBeenCalledWith("/gyms?q=bench", { scroll: false });
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

    expect(mockRouter.push).toHaveBeenCalledWith("/gyms?q=bench", { scroll: false });

    currentParams = new URLSearchParams("q=bench");

    await act(async () => {
      rerender();
      await Promise.resolve();
    });

    expect(result.current.formState.q).toBe("bench");
    expect(searchGyms).toHaveBeenLastCalledWith(
      expect.objectContaining({ q: "bench", page: 1 }),
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

    expect(mockRouter.push).toHaveBeenCalledWith("/gyms?page=3", { scroll: false });
  });

  it("clears filters and keeps the current per-page value", async () => {
    useSearchParams.mockReturnValue(
      new URLSearchParams(
        "q=bench&pref=tokyo&cats=squat-rack&page=2&limit=24&distance=10",
      ),
    );

    const { result } = renderHook(() => useGymSearch());

    await act(async () => {
      await Promise.resolve();
    });

    await act(async () => {
      result.current.clearFilters();
    });

    expect(mockRouter.push).toHaveBeenCalledWith("/gyms?limit=24", { scroll: false });
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
        meta: { total: 5, hasNext: true, pageToken: null },
      })
      .mockResolvedValueOnce({
        items: secondPageItems,
        meta: { total: 5, hasNext: false, pageToken: null },
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

    expect(mockRouter.push).toHaveBeenLastCalledWith("/gyms?page=2", { scroll: false });

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
