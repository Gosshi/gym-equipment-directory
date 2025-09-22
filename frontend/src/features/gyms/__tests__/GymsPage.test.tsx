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
  const defaultState = {
    formState: { q: "", prefecture: "", equipments: [] as string[] },
    appliedFilters: {
      q: "",
      prefecture: null as string | null,
      equipments: [] as string[],
      page: 1,
      perPage: 12,
    },
    updateKeyword: jest.fn(),
    updatePrefecture: jest.fn(),
    updateEquipments: jest.fn(),
    clearFilters: jest.fn(),
    page: 1,
    perPage: 12,
    setPage: jest.fn(),
    setPerPage: jest.fn(),
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
    equipmentCategories: [
      { value: "free-weight", label: "Free Weight" },
      { value: "cardio", label: "Cardio" },
    ],
    isMetaLoading: false,
    metaError: null,
    reloadMeta: jest.fn(),
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

    expect(screen.getByLabelText("検索キーワード")).toBeInTheDocument();
    expect(screen.getByLabelText("都道府県")).toBeInTheDocument();
    expect(screen.getByText("テストジム")).toBeInTheDocument();
  });

  it("navigates between pages via pagination controls", async () => {
    const setPage = jest.fn();
    useGymSearch.mockReturnValue(
      buildHookState({
        page: 1,
        appliedFilters: { q: "", prefecture: null, equipments: [], page: 1, perPage: 12 },
        meta: { total: 30, hasNext: true, pageToken: null },
        setPage,
      }),
    );

    render(<GymsPage />);

    await userEvent.click(screen.getByRole("button", { name: "次のページ" }));

    expect(setPage).toHaveBeenCalledWith(2);
  });

  it("changes the per-page setting when the select value updates", async () => {
    const setPerPage = jest.fn();
    useGymSearch.mockReturnValue(buildHookState({ setPerPage }));

    render(<GymsPage />);

    await userEvent.selectOptions(screen.getByLabelText("表示件数"), "24");

    expect(setPerPage).toHaveBeenCalledWith(24);
  });

  it("clears filters when the reset button is clicked", async () => {
    const clearFilters = jest.fn();
    useGymSearch.mockReturnValue(buildHookState({ clearFilters }));

    render(<GymsPage />);

    await userEvent.click(screen.getByRole("button", { name: "条件をリセット" }));

    expect(clearFilters).toHaveBeenCalled();
  });
});
