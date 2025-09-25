import userEvent from "@testing-library/user-event";
import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SearchResultsMap } from "@/components/map/Map";
import type { GymSummary } from "@/types/gym";

interface MockMapHandle {
  center: { lng: number; lat: number };
  zoom: number;
}

const mockState = {
  flyToCalls: [] as Array<{ center?: [number, number]; zoom?: number; duration?: number }>,
  fitBoundsCalls: [] as Array<{
    points: Array<[number, number]>;
    options?: Record<string, unknown>;
  }>,
  latestMap: null as MockMapHandle | null,
};

vi.mock("maplibre-gl", () => {
  class MockLngLatBounds {
    points: Array<[number, number]> = [];

    extend(value: [number, number]) {
      this.points.push(value);
      return this;
    }

    isEmpty() {
      return this.points.length === 0;
    }
  }

  class MockMap {
    container: HTMLElement;
    center: { lng: number; lat: number };
    zoom: number;

    constructor(options: { container: HTMLElement; center: [number, number]; zoom?: number }) {
      this.container = options.container;
      this.center = { lng: options.center[0], lat: options.center[1] };
      this.zoom = options.zoom ?? 11;
      mockState.latestMap = this;
    }

    addControl() {
      return this;
    }

    resize() {}

    remove() {}

    getCenter() {
      return { ...this.center };
    }

    getZoom() {
      return this.zoom;
    }

    flyTo(options: { center: [number, number]; zoom?: number; duration?: number }) {
      mockState.flyToCalls.push(options);
      this.center = { lng: options.center[0], lat: options.center[1] };
      if (typeof options.zoom === "number") {
        this.zoom = options.zoom;
      }
    }

    fitBounds(bounds: MockLngLatBounds, options: Record<string, unknown>) {
      mockState.fitBoundsCalls.push({ points: [...bounds.points], options });
    }
  }

  class MockMarker {
    element: HTMLButtonElement;

    constructor(options: { element: HTMLButtonElement }) {
      this.element = options.element;
    }

    setLngLat() {
      return this;
    }

    addTo(map: MockMap) {
      map.container.appendChild(this.element);
      return this;
    }

    remove() {
      if (this.element.parentElement) {
        this.element.parentElement.removeChild(this.element);
      }
    }
  }

  class MockNavigationControl {
    constructor(_options: unknown) {}
  }

  return {
    __esModule: true,
    default: {
      Map: MockMap,
      Marker: MockMarker,
      NavigationControl: MockNavigationControl,
      LngLatBounds: MockLngLatBounds,
    },
    Map: MockMap,
    Marker: MockMarker,
    NavigationControl: MockNavigationControl,
    LngLatBounds: MockLngLatBounds,
    StyleSpecification: {} as never,
  };
});

describe("SearchResultsMap", () => {
  beforeEach(() => {
    mockState.flyToCalls = [];
    mockState.fitBoundsCalls = [];
    mockState.latestMap = null;
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  const buildGym = (overrides: Partial<GymSummary> = {}): GymSummary => ({
    id: overrides.id ?? 1,
    slug: overrides.slug ?? "gym-alpha",
    name: overrides.name ?? "Gym Alpha",
    prefecture: overrides.prefecture ?? "tokyo",
    city: overrides.city ?? "shibuya",
    address: overrides.address,
    equipments: [],
    thumbnailUrl: null,
    lastVerifiedAt: null,
    latitude: overrides.latitude ?? 35.0,
    longitude: overrides.longitude ?? 139.0,
  });

  it("renders markers and triggers selection callbacks", async () => {
    const gyms = [buildGym(), buildGym({ id: 2, slug: "gym-beta", name: "Gym Beta", latitude: 35.1, longitude: 139.1 })];
    const handleSelect = vi.fn();
    const user = userEvent.setup();

    render(
      <SearchResultsMap
        gyms={gyms}
        hoveredGymId={null}
        onHover={() => undefined}
        onSelect={handleSelect}
        selectedGymId={null}
      />,
    );

    const marker = await screen.findByRole("button", { name: "Gym Alpha の詳細を開く" });
    await user.click(marker);

    expect(handleSelect).toHaveBeenCalledWith("gym-alpha");
  });

  it("flies to the selected gym when selectedGymId changes", async () => {
    const gyms = [
      buildGym(),
      buildGym({ id: 2, slug: "gym-beta", name: "Gym Beta", latitude: 35.3, longitude: 139.3 }),
    ];

    const { rerender } = render(
      <SearchResultsMap
        gyms={gyms}
        hoveredGymId={null}
        onHover={() => undefined}
        onSelect={() => undefined}
        selectedGymId={null}
      />,
    );

    await act(async () => {
      rerender(
        <SearchResultsMap
          gyms={gyms}
          hoveredGymId={null}
          onHover={() => undefined}
          onSelect={() => undefined}
          selectedGymId="gym-beta"
        />,
      );
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(mockState.latestMap?.center).toMatchObject({ lng: 139.3, lat: 35.3 });
      expect(mockState.latestMap?.zoom).toBeGreaterThanOrEqual(15);
    });
  });
});
