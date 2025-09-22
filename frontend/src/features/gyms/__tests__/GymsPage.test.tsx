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
      sort: "popular",
      distance: 5,
    },
    appliedFilters: {
      q: "",
      pref: null,
      city: null,
      categories: [],
      sort: "popular",
      page: 1,
      limit: 20,
      distance: 5,
    },
    updateKeyword: jest.fn(),
    updatePrefecture: jest.fn(),
    updateCity: jest.fn(),
    updateCategories: jest.fn(),
    updateSort: jest.fn(),
    updateDistance: jest.fn(),
    clearFilters: jest.fn(),
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
    meta: { total: 1, hasNext: false, pageToken: null },
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
  });

  it("navigates between pages via pagination controls", async () => {
    const setPage = jest.fn();
    useGymSearch.mockReturnValue(
      buildHookState({
        setPage,
        meta: { total: 30, hasNext: true, pageToken: null },
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

    await userEvent.selectOptions(screen.getByLabelText("表示件数"), "40");

    expect(setLimit).toHaveBeenCalledWith(40);
  });

  it("clears filters when the reset button is clicked", async () => {
    const clearFilters = jest.fn();
    useGymSearch.mockReturnValue(buildHookState({ clearFilters }));

    render(<GymsPage />);

    await userEvent.click(screen.getByRole("button", { name: "条件をクリア" }));

    expect(clearFilters).toHaveBeenCalled();
  });
});
