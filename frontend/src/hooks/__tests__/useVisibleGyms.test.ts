import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useVisibleGyms, type MapViewport } from "@/hooks/useVisibleGyms";

const fetchNearbyGymsMock = vi.fn().mockResolvedValue({
  items: [],
  total: 0,
  page: 1,
  pageSize: 0,
  hasMore: false,
  hasPrev: false,
  pageToken: null,
});

vi.mock("@/services/gymNearby", () => ({
  fetchNearbyGyms: (...args: unknown[]) => fetchNearbyGymsMock(...args),
}));

describe("useVisibleGyms", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    fetchNearbyGymsMock.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("clamps perPage to the API maximum to avoid validation errors", async () => {
    const viewport: MapViewport = {
      bounds: {
        north: 35.7,
        south: 35.6,
        east: 139.8,
        west: 139.5,
      },
      center: { lat: 35.65, lng: 139.65 },
      zoom: 12,
    };

    const { result } = renderHook(() =>
      useVisibleGyms({ debounceMs: 0, limit: 300, maxRadiusKm: 10 }),
    );

    await act(async () => {
      result.current.updateViewport(viewport);
      vi.runAllTimers();
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(fetchNearbyGymsMock).toHaveBeenCalledTimes(1);
    });

    const [params] = fetchNearbyGymsMock.mock.calls[0];
    expect(params).toMatchObject({ perPage: 100 });
  });
});
