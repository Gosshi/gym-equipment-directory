import { act, renderHook } from "@testing-library/react";

import { ApiError } from "@/lib/apiClient";
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
}));

const { useRouter, useSearchParams, usePathname } = jest.requireMock("next/navigation") as {
  useRouter: jest.Mock;
  useSearchParams: jest.Mock;
  usePathname: jest.Mock;
};

const { searchGyms } = jest.requireMock("@/services/gyms") as {
  searchGyms: jest.Mock;
};

const { getPrefectures, getEquipmentCategories } = jest.requireMock("@/services/meta") as {
  getPrefectures: jest.Mock;
  getEquipmentCategories: jest.Mock;
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
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  it("derives the initial state from query parameters", async () => {
    useSearchParams.mockReturnValue(
      new URLSearchParams(
        "q=bench&prefecture=tokyo&city=funabashi&equipment=squat-rack&sort=richness&page=2&per_page=24",
      ),
    );

    const { result } = renderHook(() => useGymSearch());

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.formState).toEqual({
      q: "bench",
      prefecture: "tokyo",
      city: "funabashi",
      equipments: ["squat-rack"],
      sort: "richness",
    });
    expect(result.current.page).toBe(2);
    expect(result.current.perPage).toBe(24);
    expect(searchGyms).toHaveBeenCalledWith(
      {
        q: "bench",
        prefecture: "tokyo",
        city: "funabashi",
        equipments: ["squat-rack"],
        sort: "richness",
        page: 2,
        perPage: 24,
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
        "q=bench&prefecture=tokyo&city=funabashi&equipment=squat-rack&sort=score&page=2&per_page=24",
      ),
    );

    const { result } = renderHook(() => useGymSearch());

    await act(async () => {
      await Promise.resolve();
    });

    await act(async () => {
      result.current.clearFilters();
    });

    expect(mockRouter.push).toHaveBeenCalledWith("/gyms?per_page=24", { scroll: false });
    expect(result.current.formState).toEqual({
      q: "",
      prefecture: "",
      city: "",
      equipments: [],
      sort: "score",
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

});
