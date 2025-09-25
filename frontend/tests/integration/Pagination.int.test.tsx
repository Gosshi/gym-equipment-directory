import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { vi } from "vitest";
import type { ReadonlyURLSearchParams } from "next/navigation";

import { server } from "../msw/server";
import { GymsPage } from "@/features/gyms/GymsPage";
import { Toaster } from "@/components/ui/toaster";

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
};

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  usePathname: () => "/gyms",
  useSearchParams: () => mockSearchParams,
}));

const renderGymsPage = () =>
  render(
    <>
      <GymsPage />
      <Toaster />
    </>,
  );

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

describe("Pagination integration", () => {
  let originalGeolocation: Geolocation | undefined;

  beforeEach(() => {
    originalGeolocation = navigator.geolocation;
    setSearchParams("");
    mockRouter.push.mockClear();
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

  it("loads the next page and updates the query parameters", async () => {
    createSuccessGeolocation(35.68, 139.76);

    const searchRequests: URL[] = [];
    const pageOneResponse = {
      items: [
        {
          id: 201,
          slug: "page-one-alpha",
          name: "ページ1・アルファジム",
          city: "shinjuku",
          pref: "tokyo",
          equipments: ["パワーラック"],
          thumbnail_url: null,
          last_verified_at: "2024-02-01T09:00:00Z",
        },
        {
          id: 202,
          slug: "page-one-beta",
          name: "ページ1・ベータジム",
          city: "shibuya",
          pref: "tokyo",
          equipments: ["マシン"],
          thumbnail_url: null,
          last_verified_at: "2024-02-05T12:00:00Z",
        },
      ],
      total: 4,
      page: 1,
      page_size: 2,
      per_page: 2,
      has_next: true,
      has_prev: false,
      has_more: true,
      page_token: null,
    };
    const pageTwoResponse = {
      items: [
        {
          id: 203,
          slug: "page-two-gamma",
          name: "ページ2・ガンマジム",
          city: "chiyoda",
          pref: "tokyo",
          equipments: ["フリーウェイト"],
          thumbnail_url: null,
          last_verified_at: "2024-02-10T09:00:00Z",
        },
        {
          id: 204,
          slug: "page-two-delta",
          name: "ページ2・デルタジム",
          city: "meguro",
          pref: "tokyo",
          equipments: ["ストレッチ"],
          thumbnail_url: null,
          last_verified_at: "2024-02-12T09:00:00Z",
        },
      ],
      total: 4,
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
        const page = url.searchParams.get("page") ?? "1";
        if (page === "2") {
          return HttpResponse.json(pageTwoResponse);
        }
        return HttpResponse.json(pageOneResponse);
      }),
    );

    renderGymsPage();

    expect(await screen.findByText("ページ1・アルファジム")).toBeInTheDocument();
    expect(screen.getByText("ページ1・ベータジム")).toBeInTheDocument();

    const nextButton = screen.getByRole("button", { name: "次のページ" });
    expect(nextButton).not.toBeDisabled();

    const initialPushCount = mockRouter.push.mock.calls.length;
    await userEvent.click(nextButton);

    await waitFor(() => expect(mockRouter.push).toHaveBeenCalledTimes(initialPushCount + 1));
    await waitFor(() => expect(searchRequests.length).toBeGreaterThan(2));
    await waitFor(() =>
      expect(searchRequests.some(url => url.searchParams.get("page") === "2")).toBe(true),
    );

    await screen.findByText("ページ2・ガンマジム");
    expect(screen.getByText("ページ2・デルタジム")).toBeInTheDocument();
    const currentPageButton = await screen.findByRole("button", { name: "ページ 2" });
    expect(currentPageButton).toHaveAttribute("aria-current", "page");

    expect(searchRequests.at(-1)?.searchParams.get("page")).toBe("2");
  });

  it("changes the page size when a new limit is selected", async () => {
    createSuccessGeolocation(35.68, 139.76);

    const searchRequests: URL[] = [];
    const limitTwentyResponse = {
      items: [
        {
          id: 301,
          slug: "twenty-alpha",
          name: "20件表示・アルファジム",
          city: "shibuya",
          pref: "tokyo",
          equipments: ["パワーラック"],
          thumbnail_url: null,
          last_verified_at: "2024-01-15T09:00:00Z",
        },
      ],
      total: 20,
      page: 1,
      page_size: 20,
      per_page: 20,
      has_next: true,
      has_prev: false,
      has_more: true,
      page_token: null,
    };
    const limitTenResponse = {
      items: [
        {
          id: 302,
          slug: "ten-alpha",
          name: "10件表示・アルファジム",
          city: "setagaya",
          pref: "tokyo",
          equipments: ["ランニングマシン"],
          thumbnail_url: null,
          last_verified_at: "2024-01-20T09:00:00Z",
        },
      ],
      total: 10,
      page: 1,
      page_size: 10,
      per_page: 10,
      has_next: true,
      has_prev: false,
      has_more: true,
      page_token: null,
    };

    server.use(
      http.get("*/gyms/search", ({ request }) => {
        const url = new URL(request.url);
        searchRequests.push(url);
        const limit = url.searchParams.get("page_size") ?? url.searchParams.get("per_page");
        if (limit === "10") {
          return HttpResponse.json(limitTenResponse);
        }
        return HttpResponse.json(limitTwentyResponse);
      }),
    );

    renderGymsPage();

    expect(await screen.findByText("20件表示・アルファジム")).toBeInTheDocument();

    const limitSelect = screen.getByLabelText("表示件数");
    await userEvent.selectOptions(limitSelect, "10");

    await screen.findByText("10件表示・アルファジム");
    await waitFor(() =>
      expect(screen.queryByText("20件表示・アルファジム")).not.toBeInTheDocument(),
    );

    expect(
      searchRequests.some(
        url =>
          url.searchParams.get("page_size") === "10" || url.searchParams.get("per_page") === "10",
      ),
    ).toBe(true);
    const lastRequest = searchRequests.at(-1);
    expect(
      lastRequest?.searchParams.get("page_size") ?? lastRequest?.searchParams.get("per_page"),
    ).toBe("10");
  });
});
