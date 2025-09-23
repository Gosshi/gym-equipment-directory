import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { GymsPage } from "@/features/gyms/GymsPage";
import type { UseGymSearchResult } from "@/hooks/useGymSearch";

jest.mock("@/hooks/useGymSearch", () => ({
  useGymSearch: jest.fn(),
}));

const { useGymSearch } = jest.requireMock("@/hooks/useGymSearch") as {
  useGymSearch: jest.Mock;
};

const buildHookState = (overrides: Partial<UseGymSearchResult> = {}) => {
  const defaultState: UseGymSearchResult = {
    formState: {
      q: "",
      prefecture: "",
      city: "",
      categories: [],
      sort: "rating",
      order: "desc",
      distance: 5,
      lat: null,
      lng: null,
    },
    appliedFilters: {
      q: "",
      pref: null,
      city: null,
      categories: [],
      sort: "rating",
      order: "desc",
      page: 1,
      limit: 20,
      distance: 5,
      lat: null,
      lng: null,
    },
    updateKeyword: jest.fn(),
    updatePrefecture: jest.fn(),
    updateCity: jest.fn(),
    updateCategories: jest.fn(),
    updateSort: jest.fn(),
    updateDistance: jest.fn(),
    clearFilters: jest.fn(),
    location: {
      lat: null,
      lng: null,
      mode: "off",
      status: "idle",
      error: null,
      isSupported: true,
    },
    requestLocation: jest.fn(),
    clearLocation: jest.fn(),
    setManualLocation: jest.fn(),
    page: 1,
    limit: 20,
    setPage: jest.fn(),
    setLimit: jest.fn(),
    loadNextPage: jest.fn(),
    items: [
      {
        id: 1,
        slug: "test-gym",
        name: "テストジム",
        prefecture: "tokyo",
        city: "shinjuku",
        equipments: ["Squat Rack"],
        thumbnailUrl: null,
        score: undefined,
        address: undefined,
        lastVerifiedAt: "2024-09-01T12:00:00Z",
      },
    ],
    meta: { total: 1, page: 1, perPage: 20, hasNext: false, hasPrev: false, pageToken: null },
    isLoading: false,
    isInitialLoading: false,
    error: null,
    retry: jest.fn(),
    prefectures: [
      { value: "tokyo", label: "Tokyo" },
      { value: "chiba", label: "Chiba" },
    ],
    cities: [{ value: "shinjuku", label: "Shinjuku" }],
    equipmentCategories: [
      { value: "free-weight", label: "Free Weight" },
      { value: "cardio", label: "Cardio" },
    ],
    isMetaLoading: false,
    metaError: null,
    reloadMeta: jest.fn(),
    isCityLoading: false,
    cityError: null,
    reloadCities: jest.fn(),
  };

  return { ...defaultState, ...overrides };
};

describe("GymsPage", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("renders the search filters and results", () => {
    useGymSearch.mockReturnValue(buildHookState());

    render(<GymsPage />);

    expect(screen.getByLabelText("キーワード")).toBeInTheDocument();
    expect(screen.getByLabelText("都道府県")).toBeInTheDocument();
    expect(screen.getByText("テストジム")).toBeInTheDocument();
    expect(screen.getByText("1–1 / 1件")).toBeInTheDocument();
  });

  it("navigates between pages via pagination controls", async () => {
    const setPage = jest.fn();
    useGymSearch.mockReturnValue(
      buildHookState({
        setPage,
        meta: { total: 30, page: 1, perPage: 20, hasNext: true, hasPrev: false, pageToken: null },
      }),
    );

    render(<GymsPage />);

    await userEvent.click(screen.getByRole("button", { name: "次のページ" }));

    expect(setPage).toHaveBeenCalledWith(2);
  });

  it("changes the page size when the select value updates", async () => {
    const setLimit = jest.fn();
    useGymSearch.mockReturnValue(buildHookState({ setLimit }));

    render(<GymsPage />);

    await userEvent.selectOptions(screen.getByLabelText("表示件数"), "50");

    expect(setLimit).toHaveBeenCalledWith(50);
  });

  it("disables pagination buttons when there is no previous or next page", () => {
    useGymSearch.mockReturnValue(
      buildHookState({
        meta: { total: 40, page: 2, perPage: 20, hasNext: false, hasPrev: true, pageToken: null },
      }),
    );

    const { rerender } = render(<GymsPage />);

    expect(screen.getByRole("button", { name: "前のページ" })).not.toBeDisabled();
    expect(screen.getByRole("button", { name: "次のページ" })).toBeDisabled();

    useGymSearch.mockReturnValue(
      buildHookState({
        meta: { total: 40, page: 1, perPage: 20, hasNext: true, hasPrev: false, pageToken: null },
      }),
    );

    rerender(<GymsPage />);

    expect(screen.getByRole("button", { name: "前のページ" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "次のページ" })).not.toBeDisabled();
  });

  it("clears filters when the reset button is clicked", async () => {
    const clearFilters = jest.fn();
    useGymSearch.mockReturnValue(buildHookState({ clearFilters }));

    render(<GymsPage />);

    await userEvent.click(screen.getByRole("button", { name: "条件をクリア" }));

    expect(clearFilters).toHaveBeenCalled();
  });
});
