import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { NearbyGymsPage } from "../NearbyGymsPage";
import { resetMapSelectionStoreForTests } from "@/state/mapSelection";

const gyms = [
  {
    id: 1,
    slug: "alpha-gym",
    name: "Alpha Gym",
    prefecture: "東京都",
    city: "千代田区",
    latitude: 35.6895,
    longitude: 139.6917,
    distanceKm: 0.5,
  },
  {
    id: 2,
    slug: "beta-gym",
    name: "Beta Gym",
    prefecture: "東京都",
    city: "港区",
    latitude: 35.6581,
    longitude: 139.7516,
    distanceKm: 1.2,
  },
];

const createMatchMedia = (matches: boolean) =>
  vi.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));

const mockSearchParams = new URLSearchParams();

const mockRouter = {
  replace: vi.fn(),
  push: vi.fn(),
};

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  usePathname: () => "/gyms/nearby",
  useSearchParams: () => mockSearchParams,
}));

vi.mock("../components/NearbyMap", () => ({
  NearbyMap: ({
    markers,
    onSelect,
  }: {
    markers: typeof gyms;
    onSelect: (id: number | null, source: "map" | "list") => void;
  }) => (
    <div data-testid="nearby-map">
      {markers.map(gym => (
        <button
          key={gym.id}
          data-panel-anchor="pin"
          data-testid={`map-pin-${gym.id}`}
          onClick={() => onSelect(gym.id, "map")}
          type="button"
        >
          {gym.name}
        </button>
      ))}
      <button data-testid="map-clear" onClick={() => onSelect(null, "map")} type="button">
        背景
      </button>
    </div>
  ),
}));

vi.mock("next/dynamic", () => ({
  __esModule: true,
  default: (factory: () => Promise<any>) => {
    return function DynamicComponent(props: unknown) {
      const [Component, setComponent] = React.useState<React.ComponentType | null>(null);

      React.useEffect(() => {
        let cancelled = false;
        factory().then(mod => {
          if (!cancelled) {
            setComponent(() => mod.default ?? mod.NearbyMap ?? mod);
          }
        });
        return () => {
          cancelled = true;
        };
      }, []);

      if (!Component) {
        return null;
      }

      return <Component {...(props as Record<string, unknown>)} />;
    };
  },
}));

vi.mock("@/components/gyms/GymDetailPanel", () => ({
  GymDetailPanel: ({ slug, onClose }: { slug: string | null; onClose: () => void }) => (
    <div data-testid="detail-panel">
      <p>Slug: {slug}</p>
      <button onClick={onClose} type="button">
        閉じる
      </button>
    </div>
  ),
}));

vi.mock("../useNearbyGyms", () => ({
  useNearbyGyms: () => ({
    items: gyms,
    meta: { total: gyms.length, page: 1, pageSize: gyms.length, hasMore: false, hasPrev: false },
    isInitialLoading: false,
    isLoading: false,
    error: null,
    reload: vi.fn(),
  }),
}));

vi.mock("@/hooks/useVisibleGyms", () => ({
  useVisibleGyms: () => ({
    gyms,
    status: "success",
    error: null,
    isLoading: false,
    isInitialLoading: false,
    updateViewport: vi.fn(),
    reload: vi.fn(),
  }),
}));

vi.mock("../useNearbySearchController", () => ({
  useNearbySearchController: () => ({
    applied: { lat: 35.68, lng: 139.76, radiusKm: 3, page: 1 },
    formState: { latInput: "35.680000", lngInput: "139.760000", radiusKm: 3 },
    manualError: null,
    location: {
      status: "success",
      error: null,
      isSupported: true,
      hasResolvedSupport: true,
      mode: "url",
      hasExplicitLocation: true,
    },
    radiusBounds: { min: 1, max: 10, step: 1 },
    setLatInput: vi.fn(),
    setLngInput: vi.fn(),
    updateRadius: vi.fn(),
    submitManualCoordinates: vi.fn(),
    updateCenterFromMap: vi.fn(),
    requestCurrentLocation: vi.fn(),
    setPage: vi.fn(),
  }),
}));

vi.mock("@/components/ui/use-toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

describe("NearbyGymsPage selection flow", () => {
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    resetMapSelectionStoreForTests();
    mockRouter.replace.mockClear();
    mockRouter.push.mockClear();
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: createMatchMedia(true),
    });
    user = userEvent.setup();
  });

  const renderPage = () => render(<NearbyGymsPage />);

  it("opens the detail panel when a map pin is clicked", async () => {
    renderPage();

    const pin = await screen.findByTestId("map-pin-1");
    await user.click(pin);

    const panels = screen.getAllByTestId("detail-panel");
    expect(panels[0]).toHaveTextContent("Slug: alpha-gym");
  });

  it("closes the detail panel when the same map pin is clicked again", async () => {
    renderPage();

    const pin = await screen.findByTestId("map-pin-1");
    await user.click(pin);
    expect(screen.getAllByTestId("detail-panel")[0]).toHaveTextContent("Slug: alpha-gym");

    await user.click(pin);

    expect(screen.queryAllByTestId("detail-panel")).toHaveLength(0);
  });

  it("closes the panel when clicking outside the detail area", async () => {
    renderPage();

    const pin = await screen.findByTestId("map-pin-1");
    await user.click(pin);
    expect(screen.getAllByTestId("detail-panel")[0]).toHaveTextContent("Slug: alpha-gym");

    await user.click(document.body);

    expect(screen.queryAllByTestId("detail-panel")).toHaveLength(0);
  });
});
