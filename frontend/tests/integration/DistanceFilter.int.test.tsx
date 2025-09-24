import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

describe("Distance filter integration", () => {
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

  it("applies the selected radius to the API query and updates the list", async () => {
    createSuccessGeolocation(35.68, 139.76);

    const searchRequests: URL[] = [];
    const radiusFiveResponse = {
      items: [
        {
          id: 101,
          slug: "five-km-gym",
          name: "半径5kmトレーニングジム",
          city: "chiyoda",
          pref: "tokyo",
          equipments: ["ダンベル"],
          thumbnail_url: null,
          last_verified_at: "2024-03-15T10:00:00Z",
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
    const radiusTenResponse = {
      items: [
        {
          id: 102,
          slug: "ten-km-gym",
          name: "半径10kmフィットネスセンター",
          city: "setagaya",
          pref: "tokyo",
          equipments: ["ランニングマシン"],
          thumbnail_url: null,
          last_verified_at: "2024-04-20T08:00:00Z",
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
        const radius = url.searchParams.get("radius_km");
        if (radius === "10") {
          return HttpResponse.json(radiusTenResponse);
        }
        return HttpResponse.json(radiusFiveResponse);
      }),
    );

    renderGymsPage();

    expect(await screen.findByText("半径5kmトレーニングジム")).toBeInTheDocument();

    const distanceSlider = screen.getByLabelText("検索半径（キロメートル）") as HTMLInputElement;
    expect(distanceSlider).not.toBeDisabled();

    await userEvent.click(distanceSlider);
    fireEvent.change(distanceSlider, { target: { value: "10" } });

    await screen.findByText("半径10kmフィットネスセンター");
    expect(distanceSlider.value).toBe("10");
    await waitFor(() =>
      expect(screen.queryByText("半径5kmトレーニングジム")).not.toBeInTheDocument(),
    );

    expect(searchRequests.some(url => url.searchParams.get("radius_km") === "10")).toBe(true);
    expect(searchRequests.at(-1)?.searchParams.get("radius_km")).toBe("10");
  });
});
