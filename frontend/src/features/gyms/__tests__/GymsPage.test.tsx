import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { GymsPage } from "@/features/gyms/GymsPage";
import { useGymDetail } from "@/hooks/useGymDetail";
import type { UseGymDetailResult } from "@/hooks/useGymDetail";
import { useGymSearch } from "@/hooks/useGymSearch";
import type { UseGymSearchResult } from "@/hooks/useGymSearch";

vi.mock("@/hooks/useGymSearch", () => ({
  useGymSearch: vi.fn(),
  FALLBACK_LOCATION: { lat: 35.681236, lng: 139.767125, label: "東京駅" },
}));

vi.mock("@/hooks/useGymDetail", () => ({
  useGymDetail: vi.fn(),
}));

const mockedUseGymSearch = vi.mocked(useGymSearch);
const mockedUseGymDetail = vi.mocked(useGymDetail);

const buildHookState = (overrides: Partial<UseGymSearchResult> = {}): UseGymSearchResult => {
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
    updateKeyword: vi.fn(),
    updatePrefecture: vi.fn(),
    updateCity: vi.fn(),
    updateCategories: vi.fn(),
    updateSort: vi.fn(),
    updateDistance: vi.fn(),
    clearFilters: vi.fn(),
    submitSearch: vi.fn(),
    location: {
      lat: null,
      lng: null,
      mode: "off",
      status: "idle",
      error: null,
      isSupported: true,
      hasResolvedSupport: true,
      isFallback: false,
      fallbackLabel: null,
    },
    requestLocation: vi.fn(),
    clearLocation: vi.fn(),
    useFallbackLocation: vi.fn(),
    setManualLocation: vi.fn(),
    page: 1,
    limit: 20,
    setPage: vi.fn(),
    setLimit: vi.fn(),
    loadNextPage: vi.fn(),
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
    meta: {
      total: 1,
      page: 1,
      perPage: 20,
      hasNext: false,
      hasPrev: false,
      hasMore: false,
      pageToken: null,
    },
    isLoading: false,
    isInitialLoading: false,
    error: null,
    retry: vi.fn(),
    prefectures: [
      { value: "tokyo", label: "Tokyo" },
      { value: "chiba", label: "Chiba" },
    ],
    cities: [{ value: "shinjuku", label: "Shinjuku" }],
    equipmentOptions: [
      { value: "squat-rack", label: "スクワットラック", slug: "squat-rack", name: "スクワットラック", category: "free_weight" },
      { value: "smith-machine", label: "スミスマシン", slug: "smith-machine", name: "スミスマシン", category: "strength" },
    ],
    isMetaLoading: false,
    metaError: null,
    reloadMeta: vi.fn(),
    isCityLoading: false,
    cityError: null,
    reloadCities: vi.fn(),
  };

  return { ...defaultState, ...overrides };
};

describe("GymsPage", () => {
  beforeEach(() => {
    mockedUseGymDetail.mockReturnValue({
      data: null,
      error: null,
      isLoading: false,
      reload: vi.fn(),
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    mockedUseGymSearch.mockReset();
    mockedUseGymDetail.mockReset();
  });

  it("renders the search filters and results", () => {
    mockedUseGymSearch.mockReturnValue(buildHookState());

    render(<GymsPage />);

    expect(screen.getByLabelText("キーワード")).toBeInTheDocument();
    expect(screen.getByLabelText("都道府県")).toBeInTheDocument();
    expect(screen.getByText("テストジム")).toBeInTheDocument();
    expect(screen.getByText("1–1 / 1件")).toBeInTheDocument();
  });

  it("navigates between pages via pagination controls", async () => {
    const setPage = vi.fn();
    mockedUseGymSearch.mockReturnValue(
      buildHookState({
        setPage,
        meta: {
          total: 30,
          page: 1,
          perPage: 20,
          hasNext: true,
          hasPrev: false,
          hasMore: true,
          pageToken: null,
        },
      }),
    );

    render(<GymsPage />);

    await userEvent.click(screen.getByRole("button", { name: "次のページ" }));

    expect(setPage).toHaveBeenCalledWith(2);
  });

  it("changes the page size when the select value updates", async () => {
    const setLimit = vi.fn();
    mockedUseGymSearch.mockReturnValue(buildHookState({ setLimit }));

    render(<GymsPage />);

    await userEvent.selectOptions(screen.getByLabelText("表示件数"), "50");

    expect(setLimit).toHaveBeenCalledWith(50);
  });

  it("disables pagination buttons when there is no previous or next page", () => {
    mockedUseGymSearch.mockReturnValue(
      buildHookState({
        meta: {
          total: 40,
          page: 2,
          perPage: 20,
          hasNext: false,
          hasPrev: true,
          hasMore: false,
          pageToken: null,
        },
      }),
    );

    const { rerender } = render(<GymsPage />);

    expect(screen.getByRole("button", { name: "前のページ" })).not.toBeDisabled();
    expect(screen.getByRole("button", { name: "次のページ" })).toBeDisabled();

    mockedUseGymSearch.mockReturnValue(
      buildHookState({
        meta: {
          total: 40,
          page: 1,
          perPage: 20,
          hasNext: true,
          hasPrev: false,
          hasMore: true,
          pageToken: null,
        },
      }),
    );

    rerender(<GymsPage />);

    expect(screen.getByRole("button", { name: "前のページ" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "次のページ" })).not.toBeDisabled();
  });

  it("clears filters when the reset button is clicked", async () => {
    const clearFilters = vi.fn();
    mockedUseGymSearch.mockReturnValue(buildHookState({ clearFilters }));

    render(<GymsPage />);

    await userEvent.click(screen.getByRole("button", { name: "条件をクリア" }));

    expect(clearFilters).toHaveBeenCalled();
  });

  it("submits the search when the search button is pressed", async () => {
    const submitSearch = vi.fn();
    mockedUseGymSearch.mockReturnValue(buildHookState({ submitSearch }));

    render(<GymsPage />);

    const [searchButton] = screen.getAllByRole("button", { name: "検索を実行" });
    await userEvent.click(searchButton);

    expect(submitSearch).toHaveBeenCalled();
  });

  it("opens and closes the detail modal when a gym is selected", async () => {
    const detailResult: UseGymDetailResult = {
      data: {
        id: 99,
        slug: "test-gym",
        name: "テストジム詳細",
        prefecture: "tokyo",
        city: "shinjuku",
        address: "東京都新宿区1-2-3",
        latitude: 35.6895,
        longitude: 139.6917,
        equipments: [],
        website: "https://example.com",
      },
      error: null,
      isLoading: false,
      reload: vi.fn(),
    };
    mockedUseGymDetail.mockReturnValue(detailResult);
    mockedUseGymSearch.mockReturnValue(buildHookState());

    render(<GymsPage />);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("link", { name: "テストジムの詳細を見る" }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "テストジム詳細" })).toBeInTheDocument();
    expect(screen.getByText("東京都新宿区1-2-3")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "詳細パネルを閉じる" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("clears the selected gym when it disappears from the current page", async () => {
    const initialState = buildHookState();
    const updatedState = buildHookState({
      items: [
        {
          id: 2,
          slug: "another-gym",
          name: "別のジム",
          prefecture: "tokyo",
          city: "shinjuku",
          equipments: ["Bench Press"],
          thumbnailUrl: null,
          score: undefined,
          address: "東京都新宿区2-3-4",
          lastVerifiedAt: "2024-09-02T08:00:00Z",
        },
      ],
      meta: {
        total: 1,
        page: 2,
        perPage: 20,
        hasNext: false,
        hasPrev: true,
        hasMore: false,
        pageToken: null,
      },
    });
    let currentState = initialState;
    mockedUseGymSearch.mockImplementation(() => currentState);

    const detailResult: UseGymDetailResult = {
      data: {
        id: 2,
        slug: "another-gym",
        name: "別のジム",
        prefecture: "tokyo",
        city: "shinjuku",
        address: "東京都新宿区2-3-4",
        latitude: 35.6895,
        longitude: 139.6917,
        equipments: [],
      },
      error: null,
      isLoading: false,
      reload: vi.fn(),
    };
    mockedUseGymDetail.mockReturnValue(detailResult);

    const { rerender } = render(<GymsPage />);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("link", { name: "テストジムの詳細を見る" }));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();

    currentState = updatedState;
    rerender(<GymsPage />);

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });
});
