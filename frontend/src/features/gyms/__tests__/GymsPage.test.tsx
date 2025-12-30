import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { GymsPage } from "@/features/gyms/GymsPage";

import { useGymSearch } from "@/hooks/useGymSearch";
import type { UseGymSearchResult } from "@/hooks/useGymSearch";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/hooks/useGymSearch", () => ({
  useGymSearch: vi.fn(),
  FALLBACK_LOCATION: { lat: 35.681236, lng: 139.767125, label: "東京駅" },
}));

vi.mock("next/navigation", () => ({
  usePathname: vi.fn().mockReturnValue("/search"),
  useSearchParams: vi.fn().mockReturnValue(new URLSearchParams()),
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

const renderWithClient = (ui: React.ReactElement) => {
  const testQueryClient = createTestQueryClient();
  const { rerender, ...result } = render(
    <QueryClientProvider client={testQueryClient}>{ui}</QueryClientProvider>,
  );
  return {
    ...result,
    rerender: (rerenderUi: React.ReactElement) =>
      rerender(<QueryClientProvider client={testQueryClient}>{rerenderUi}</QueryClientProvider>),
  };
};

const mockedUseGymSearch = vi.mocked(useGymSearch);

const buildHookState = (overrides: Partial<UseGymSearchResult> = {}): UseGymSearchResult => {
  const defaultState: UseGymSearchResult = {
    formState: {
      q: "",
      prefecture: "",
      city: "",
      categories: [],
      equipments: [],
      conditions: [],
      sort: "name",
      order: "asc",
      distance: 5,
      lat: null,
      lng: null,
      min_lat: null,
      max_lat: null,
      min_lng: null,
      max_lng: null,
    },
    appliedFilters: {
      q: "",
      pref: null,
      city: null,
      categories: [],
      equipments: [],
      conditions: [],
      sort: "name",
      order: "asc",
      page: 1,
      limit: 20,
      distance: 5,
      lat: null,
      lng: null,
      min_lat: null,
      max_lat: null,
      min_lng: null,
      max_lng: null,
    },
    updateKeyword: vi.fn(),
    updatePrefecture: vi.fn(),
    updateCity: vi.fn(),
    updateCategories: vi.fn(),
    updateEquipments: vi.fn(),
    updateConditions: vi.fn(),
    updateSort: vi.fn(),
    updateDistance: vi.fn(),
    updateBoundingBox: vi.fn(),
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
      {
        value: "squat-rack",
        label: "スクワットラック",
        slug: "squat-rack",
        name: "スクワットラック",
        category: "free_weight",
      },
      {
        value: "smith-machine",
        label: "スミスマシン",
        slug: "smith-machine",
        name: "スミスマシン",
        category: "strength",
      },
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
    // No specific setup needed currently
  });

  afterEach(() => {
    vi.clearAllMocks();
    mockedUseGymSearch.mockReset();
    mockedUseGymSearch.mockReset();
  });

  it("renders the search filters and results", () => {
    mockedUseGymSearch.mockReturnValue(buildHookState());

    renderWithClient(<GymsPage />);

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

    renderWithClient(<GymsPage />);

    await userEvent.click(screen.getByRole("button", { name: "次のページ" }));

    expect(setPage).toHaveBeenCalledWith(2);
  });

  it("changes the page size when the select value updates", async () => {
    const setLimit = vi.fn();
    mockedUseGymSearch.mockReturnValue(buildHookState({ setLimit }));

    renderWithClient(<GymsPage />);

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

    const { rerender } = renderWithClient(<GymsPage />);

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

    renderWithClient(<GymsPage />);

    await userEvent.click(screen.getByRole("button", { name: "条件をクリア" }));

    expect(clearFilters).toHaveBeenCalled();
  });

  it("submits the search when the search button is pressed", async () => {
    const submitSearch = vi.fn();
    mockedUseGymSearch.mockReturnValue(buildHookState({ submitSearch }));

    renderWithClient(<GymsPage />);

    const [searchButton] = screen.getAllByRole("button", { name: "検索を実行" });
    await userEvent.click(searchButton);

    expect(submitSearch).toHaveBeenCalled();
  });
});
