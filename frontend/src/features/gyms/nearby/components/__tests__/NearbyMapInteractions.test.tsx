import type { ComponentProps } from "react";

import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NearbyMap } from "../NearbyMap";
import { resetMapSelectionStoreForTests, useMapSelectionStore } from "@/state/mapSelection";
import type { NearbyGym } from "@/types/gym";

interface MockMapHandle {
  emit: (event: string, ...args: unknown[]) => void;
}

const mockState = {
  easeToCalls: [] as Array<{ center?: [number, number]; zoom?: number; duration?: number }>,
  latestMap: null as MockMapHandle | null,
};

vi.mock("maplibre-gl", () => {
  class MockMap {
    container: HTMLElement;
    center: { lng: number; lat: number };
    zoom: number;
    handlers: Map<string, Set<(...args: unknown[]) => void>> = new Map();

    constructor(options: { container: HTMLElement; center: [number, number]; zoom?: number }) {
      this.container = options.container;
      this.center = { lng: options.center[0], lat: options.center[1] };
      this.zoom = options.zoom ?? 13;
      mockState.latestMap = this;
    }

    addControl() {
      return this;
    }

    resize() {}

    remove() {}

    on(event: string, handler: (...args: unknown[]) => void) {
      if (!this.handlers.has(event)) {
        this.handlers.set(event, new Set());
      }
      this.handlers.get(event)!.add(handler);
    }

    off(event: string, handler: (...args: unknown[]) => void) {
      const listeners = this.handlers.get(event);
      if (!listeners) {
        return;
      }
      listeners.delete(handler);
    }

    emit(event: string, ...args: unknown[]) {
      const listeners = this.handlers.get(event);
      if (!listeners) {
        return;
      }
      listeners.forEach(listener => listener(...args));
    }

    getCenter() {
      return { ...this.center };
    }

    getZoom() {
      return this.zoom;
    }

    easeTo(options: { center: [number, number]; zoom?: number; duration?: number }) {
      mockState.easeToCalls.push(options);
      this.center = { lng: options.center[0], lat: options.center[1] };
      if (typeof options.zoom === "number") {
        this.zoom = options.zoom;
      }
      this.emit("moveend");
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
    },
    Map: MockMap,
    Marker: MockMarker,
    NavigationControl: MockNavigationControl,
  };
});

const gyms: NearbyGym[] = [
  {
    id: 1,
    slug: "gym-one",
    name: "ジムワン",
    prefecture: "東京都",
    city: "千代田区",
    latitude: 35.6895,
    longitude: 139.6917,
    distanceKm: 0.5,
  },
  {
    id: 2,
    slug: "gym-two",
    name: "ジムツー",
    prefecture: "東京都",
    city: "港区",
    latitude: 35.6581,
    longitude: 139.7516,
    distanceKm: 1.1,
  },
];

const TestNearbyMap = (
  props: Partial<ComponentProps<typeof NearbyMap>> & { markers?: NearbyGym[] } = {},
) => {
  const selectedId = useMapSelectionStore(state => state.selectedId);
  const hoveredId = useMapSelectionStore(state => state.hoveredId);
  const lastSelectionSource = useMapSelectionStore(state => state.lastSelectionSource);
  const lastSelectionAt = useMapSelectionStore(state => state.lastSelectionAt);
  const setSelected = useMapSelectionStore(state => state.setSelected);
  const setHovered = useMapSelectionStore(state => state.setHovered);

  const {
    markers = gyms,
    onRequestDetail = () => undefined,
    onCenterChange = () => undefined,
    ...rest
  } = props;

  return (
    <NearbyMap
      center={{ lat: 35.68, lng: 139.76 }}
      markers={markers}
      hoveredGymId={hoveredId}
      selectedGymId={selectedId}
      lastSelectionSource={lastSelectionSource}
      lastSelectionAt={lastSelectionAt}
      onSelect={(id, source) => setSelected(id, source)}
      onPreview={(id, source) => setHovered(id, source)}
      onRequestDetail={onRequestDetail}
      onCenterChange={onCenterChange}
      {...rest}
    />
  );
};

const renderMap = (props?: Partial<ComponentProps<typeof NearbyMap>>) => render(
  <TestNearbyMap {...props} />,
);

beforeEach(() => {
  mockState.easeToCalls.length = 0;
  mockState.latestMap = null;
  resetMapSelectionStoreForTests();
  vi.useFakeTimers();
});

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
});

describe("NearbyMap interactions", () => {
  it("updates marker state when hover changes", async () => {
    const { container } = renderMap();
    await act(async () => {});

    const mapContainer = container.firstElementChild as HTMLElement;
    const marker = mapContainer.querySelector('[data-gym-id="2"]') as HTMLButtonElement | null;
    expect(marker).not.toBeNull();
    if (!marker) {
      throw new Error("Marker was not created");
    }

    act(() => {
      useMapSelectionStore.getState().setHovered(2, "list");
    });

    expect(marker.dataset.state).toBe("hovered");

    act(() => {
      useMapSelectionStore.getState().setSelected(2, "list");
    });

    expect(marker.dataset.state).toBe("selected");
  });

  it("pans to the selected gym with controlled zoom", async () => {
    renderMap({ zoom: 10 });
    await act(async () => {});

    act(() => {
      useMapSelectionStore.getState().setSelected(2, "list");
    });

    act(() => {
      vi.advanceTimersByTime(200);
    });

    expect(mockState.easeToCalls).toHaveLength(1);
    const [{ center, zoom, duration }] = mockState.easeToCalls;
    expect(center).toEqual([gyms[1].longitude, gyms[1].latitude]);
    expect(zoom).toBe(12);
    expect(duration).toBe(500);
  });

  it("debounces repeated selections", async () => {
    renderMap();
    await act(async () => {});

    act(() => {
      useMapSelectionStore.getState().setSelected(2, "list");
      useMapSelectionStore.getState().setSelected(2, "list");
    });

    act(() => {
      vi.runOnlyPendingTimers();
    });

    expect(mockState.easeToCalls).toHaveLength(1);
  });

  it("skips auto-pan when selection originates from the map", async () => {
    renderMap();
    await act(async () => {});

    act(() => {
      useMapSelectionStore.getState().setSelected(2, "map");
    });

    act(() => {
      vi.advanceTimersByTime(200);
      useMapSelectionStore.getState().setSelected(2, "list");
    });

    act(() => {
      vi.runOnlyPendingTimers();
    });

    expect(mockState.easeToCalls).toHaveLength(0);
  });

  it("does not pan while the user is dragging", async () => {
    const { container } = renderMap();
    await act(async () => {});

    const mapContainer = container.firstElementChild as HTMLElement;
    const marker = mapContainer.querySelector('[data-gym-id="1"]');
    expect(marker).not.toBeNull();

    act(() => {
      mockState.latestMap?.emit("dragstart");
      useMapSelectionStore.getState().setSelected(2, "list");
    });

    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(mockState.easeToCalls).toHaveLength(0);

    act(() => {
      mockState.latestMap?.emit("dragend");
      useMapSelectionStore.getState().setSelected(2, "list");
    });

    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(mockState.easeToCalls).toHaveLength(1);
  });
});
