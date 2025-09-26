import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { vi } from "vitest";
import type { ReadonlyURLSearchParams } from "next/navigation";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { server } from "../msw/server";
import { defaultGymSearchResponse } from "../msw/handlers";
import { GymsPage } from "@/features/gyms/GymsPage";
import { Toaster } from "@/components/ui/toaster";
import { FALLBACK_LOCATION } from "@/hooks/useGymSearch";
import { useSearchStore } from "@/store/searchStore";
import { DEFAULT_FILTER_STATE, filterStateToQueryString } from "@/lib/searchParams";

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
}

const createSearchParams = (init: string = ""): ReadonlyURLSearchParams => {
  return new TestReadonlyURLSearchParams(init) as unknown as ReadonlyURLSearchParams;
};

let mockSearchParams = createSearchParams();

const updateSearchParamsFromUrl = (url: string) => {
  const queryIndex = url.indexOf("?");
  const query = queryIndex >= 0 ? url.slice(queryIndex + 1) : "";
  mockSearchParams = createSearchParams(query);
};

const mockRouter = {
  push: vi.fn((url: string) => {
    updateSearchParamsFromUrl(url);
  }),
  replace: vi.fn((url: string) => {
    updateSearchParamsFromUrl(url);
  }),
};

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  usePathname: () => "/gyms",
  useSearchParams: () => mockSearchParams,
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60_000,
        gcTime: 5 * 60_000,
        refetchOnWindowFocus: false,
        refetchOnReconnect: false,
        retry: false,
      },
    },
  });

const renderGymsPage = () => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <>
        <GymsPage />
        <Toaster />
      </>
    </QueryClientProvider>,
  );
};

const setSearchParams = (query: string) => {
  mockSearchParams = createSearchParams(query);
};

type GeolocationMock = Pick<Geolocation, "getCurrentPosition" | "watchPosition" | "clearWatch">;

const applyGeolocationMock = (mock: GeolocationMock) => {
  Object.defineProperty(navigator, "geolocation", {
    configurable: true,
    value: mock as Geolocation,
  });
  return mock;
};

const createSuccessGeolocation = (lat: number, lng: number) => {
  const mock: GeolocationMock = {
    getCurrentPosition: vi.fn(success => {
      success({
        coords: {
          accuracy: 5,
          altitude: null,
          altitudeAccuracy: null,
          heading: null,
          latitude: lat,
          longitude: lng,
          speed: null,
        },
        timestamp: Date.now(),
      } as GeolocationPosition);
    }),
    watchPosition: vi.fn(),
    clearWatch: vi.fn(),
  };
  return applyGeolocationMock(mock);
};

const createPermissionDeniedGeolocation = () => {
  const error = {
    code: 1,
    PERMISSION_DENIED: 1,
    POSITION_UNAVAILABLE: 2,
    TIMEOUT: 3,
    message: "Permission denied",
  } as GeolocationPositionError;
  const mock: GeolocationMock = {
    getCurrentPosition: vi.fn((_, errorCallback) => {
      errorCallback?.(error);
    }),
    watchPosition: vi.fn(),
    clearWatch: vi.fn(),
  };
  return applyGeolocationMock(mock);
};

describe("Search flow integration", () => {
  let originalGeolocation: Geolocation | undefined;

  beforeEach(() => {
    originalGeolocation = navigator.geolocation;
    setSearchParams("");
    mockRouter.push.mockClear();
    mockRouter.replace.mockClear();
    useSearchStore.setState({
      filters: DEFAULT_FILTER_STATE,
      queryString: filterStateToQueryString(DEFAULT_FILTER_STATE),
      navigationSource: "initial",
      scrollPositions: {},
    });
  });

  afterEach(() => {
    if (originalGeolocation) {
      Object.defineProperty(navigator, "geolocation", {
        configurable: true,
        value: originalGeolocation,
      });
    } else {
      Object.defineProperty(navigator, "geolocation", {
        configurable: true,
        value: undefined,
      });
    }
  });

  it("performs a keyword search and renders the matching gyms", async () => {
    createSuccessGeolocation(35.68, 139.76);

    const searchRequests: URL[] = [];
    const keywordResponse = {
      items: [
        {
          id: 10,
          slug: "powerhouse",
          name: "パワーハウスジム",
          city: "meguro",
          pref: "tokyo",
          equipments: ["パワーラック"],
          thumbnail_url: null,
          last_verified_at: "2024-04-12T10:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
      per_page: 20,
      has_next: false,
      has_prev: false,
      has_more: false,
      page_token: null,
    };

    server.use(
      http.get("*/gyms/search", ({ request }) => {
        const url = new URL(request.url);
        searchRequests.push(url);
        const keyword = url.searchParams.get("q");
        if (keyword && keyword.toLowerCase().includes("power")) {
          return HttpResponse.json(keywordResponse);
        }
        return HttpResponse.json(defaultGymSearchResponse);
      }),
    );

    renderGymsPage();

    const skeletons = await screen.findAllByTestId("search-result-skeleton");
    expect(skeletons.length).toBeGreaterThan(0);

    expect(await screen.findByText("東京フィットジム")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.queryByTestId("search-result-skeleton")).not.toBeInTheDocument(),
    );

    const user = userEvent.setup();
    const keywordInput = screen.getByLabelText("キーワード");
    await user.clear(keywordInput);
    await user.type(keywordInput, "power");

    await screen.findByText("パワーハウスジム");
    await waitFor(() => expect(screen.queryByText("東京フィットジム")).not.toBeInTheDocument());

    expect(searchRequests.some(url => url.searchParams.get("q")?.toLowerCase() === "power")).toBe(
      true,
    );
  });

  it("displays an empty state when no gyms match the filters", async () => {
    createSuccessGeolocation(35.68, 139.76);

    const emptyResponse = {
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      per_page: 20,
      has_next: false,
      has_prev: false,
      has_more: false,
      page_token: null,
    };

    server.use(http.get("*/gyms/search", () => HttpResponse.json(emptyResponse)));

    renderGymsPage();

    const emptyMessage = await screen.findByText("該当するジムが見つかりませんでした");
    const emptyState = emptyMessage.closest('[role="status"]');
    expect(emptyState).not.toBeNull();
    expect(
      within(emptyState as HTMLElement).getByRole("button", { name: "条件をクリア" }),
    ).toBeInTheDocument();
  });

  it("shows an error state when the API request fails and allows retrying", async () => {
    applyGeolocationMock({
      getCurrentPosition: vi.fn(),
      watchPosition: vi.fn(),
      clearWatch: vi.fn(),
    });

    let requestCount = 0;
    server.use(
      http.get("*/gyms/search", () => {
        requestCount += 1;
        if (requestCount === 1) {
          return HttpResponse.json({ message: "Server error" }, { status: 500 });
        }
        return HttpResponse.json(defaultGymSearchResponse);
      }),
    );

    renderGymsPage();

    const alert = await screen.findByRole("alert");
    const retryButton = within(alert).getByRole("button", { name: "再試行" });

    const user = userEvent.setup();
    await user.click(retryButton);

    expect(await screen.findByText("東京フィットジム")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
    expect(requestCount).toBeGreaterThanOrEqual(2);
  });

  it("requests the current position and includes coordinates in the search query", async () => {
    const geolocation = createSuccessGeolocation(35.68, 139.76);

    const searchRequests: URL[] = [];
    const nearbyResponse = {
      items: [
        {
          id: 20,
          slug: "nearby-fitness",
          name: "現在地フィットネス",
          city: "chiyoda",
          pref: "tokyo",
          equipments: ["ランニングマシン"],
          thumbnail_url: null,
          last_verified_at: "2024-05-01T08:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
      per_page: 20,
      has_next: false,
      has_prev: false,
      has_more: false,
      page_token: null,
    };

    server.use(
      http.get("*/gyms/search", ({ request }) => {
        const url = new URL(request.url);
        searchRequests.push(url);
        if (url.searchParams.has("lat")) {
          return HttpResponse.json(nearbyResponse);
        }
        return HttpResponse.json(defaultGymSearchResponse);
      }),
    );

    renderGymsPage();

    await waitFor(() => expect(geolocation.getCurrentPosition).toHaveBeenCalled());

    await screen.findByText("現在地フィットネス");

    expect(
      searchRequests.some(
        url => url.searchParams.get("lat") === "35.68" && url.searchParams.get("lng") === "139.76",
      ),
    ).toBe(true);
    expect(await screen.findByText(/現在地を使用中/)).toBeInTheDocument();
  });

  it("falls back to the default location when geolocation is denied", async () => {
    const geolocation = createPermissionDeniedGeolocation();

    const searchRequests: URL[] = [];
    const fallbackResponse = {
      items: [
        {
          id: 30,
          slug: "tokyo-station-gym",
          name: "東京駅トレーニングセンター",
          city: "chiyoda",
          pref: "tokyo",
          equipments: ["マシン", "ストレッチ"],
          thumbnail_url: null,
          last_verified_at: "2024-05-20T09:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
      per_page: 20,
      has_next: false,
      has_prev: false,
      has_more: false,
      page_token: null,
    };

    server.use(
      http.get("*/gyms/search", ({ request }) => {
        const url = new URL(request.url);
        searchRequests.push(url);
        if (
          url.searchParams.get("lat") === FALLBACK_LOCATION.lat.toString() &&
          url.searchParams.get("lng") === FALLBACK_LOCATION.lng.toString()
        ) {
          return HttpResponse.json(fallbackResponse);
        }
        return HttpResponse.json(defaultGymSearchResponse);
      }),
    );

    renderGymsPage();

    await waitFor(() => expect(geolocation.getCurrentPosition).toHaveBeenCalled());

    await screen.findByText("東京駅トレーニングセンター");

    expect(
      searchRequests.some(
        url =>
          url.searchParams.get("lat") === FALLBACK_LOCATION.lat.toString() &&
          url.searchParams.get("lng") === FALLBACK_LOCATION.lng.toString(),
      ),
    ).toBe(true);

    expect(await screen.findByText(/デフォルト地点（東京駅）を使用中/)).toBeInTheDocument();

    const guidanceButton = await screen.findByRole("button", { name: "住所や駅名で検索する" });
    expect(guidanceButton).toBeInTheDocument();

    const user = userEvent.setup();
    const keywordInput = screen.getByLabelText("キーワード");
    await user.click(guidanceButton);
    await waitFor(() => expect(keywordInput).toHaveFocus());
  });

  it("updates results when distance changes, paginates, and routes to detail", async () => {
    createSuccessGeolocation(35.68, 139.76);

    const searchRequests: URL[] = [];
    const radiusResponse = {
      items: [
        {
          id: 101,
          slug: "central-fit",
          name: "Central Fit 新宿",
          city: "shinjuku",
          pref: "tokyo",
          equipments: ["パワーラック", "ダンベル"],
          thumbnail_url: null,
          last_verified_at: "2024-06-10T09:00:00Z",
        },
        {
          id: 102,
          slug: "harbor-fitness",
          name: "Harbor Fitness 品川",
          city: "minato",
          pref: "tokyo",
          equipments: ["マシン", "カーディオ"],
          thumbnail_url: null,
          last_verified_at: "2024-06-12T09:00:00Z",
        },
      ],
      total: 3,
      page: 1,
      page_size: 2,
      per_page: 2,
      has_next: true,
      has_prev: false,
      has_more: true,
      page_token: null,
    };

    const nextPageResponse = {
      items: [
        {
          id: 103,
          slug: "river-side-gym",
          name: "River Side Gym 中野",
          city: "nakano",
          pref: "tokyo",
          equipments: ["ケーブルマシン"],
          thumbnail_url: null,
          last_verified_at: "2024-06-15T09:00:00Z",
        },
      ],
      total: 3,
      page: 2,
      page_size: 2,
      per_page: 2,
      has_next: false,
      has_prev: true,
      has_more: false,
      page_token: null,
    };

    server.use(
      http.get("*/gyms/search", ({ request }) => {
        const url = new URL(request.url);
        searchRequests.push(url);
        const radius = Number(
          url.searchParams.get("radius_km") ?? url.searchParams.get("distance"),
        );
        const page = Number(url.searchParams.get("page") ?? "1");
        if (page >= 2) {
          return HttpResponse.json(nextPageResponse);
        }
        if (!Number.isNaN(radius) && radius > 5) {
          return HttpResponse.json(radiusResponse);
        }
        return HttpResponse.json(defaultGymSearchResponse);
      }),
    );

    renderGymsPage();

    expect(await screen.findByText("東京フィットジム")).toBeInTheDocument();

    const distanceSlider = screen.getByLabelText("検索半径（キロメートル）");
    fireEvent.change(distanceSlider, { target: { value: "10" } });

    await screen.findByText("Central Fit 新宿");
    expect(screen.getByText("Harbor Fitness 品川")).toBeInTheDocument();

    const detailLink = screen.getByRole("link", { name: "Central Fit 新宿の詳細を見る" });
    expect(detailLink).toHaveAttribute("href", "/gyms/central-fit");
    expect(detailLink).toHaveAttribute("aria-label", "Central Fit 新宿の詳細を見る");

    expect(
      searchRequests.some(url => {
        const radiusParam = url.searchParams.get("radius_km") ?? url.searchParams.get("distance");
        return radiusParam === "10";
      }),
    ).toBe(true);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "次のページ" }));

    await waitFor(() =>
      expect(searchRequests.some(url => url.searchParams.get("page") === "2")).toBe(true),
    );

    await waitFor(() => expect(mockRouter.replace).toHaveBeenCalled());
    expect(
      mockRouter.replace.mock.calls.some(([url]) => typeof url === "string" && url.includes("page=2")),
    ).toBe(true);

  });
});
