import { vi } from "vitest";

import { apiRequest } from "@/lib/apiClient";
import { fetchNearbyGyms } from "@/services/gymNearby";

vi.mock("@/lib/apiClient", () => ({
  apiRequest: vi.fn(),
}));

const mockedApiRequest = vi.mocked(apiRequest);

describe("fetchNearbyGyms", () => {
  beforeEach(() => {
    mockedApiRequest.mockResolvedValue({
      items: [
        {
          id: 1,
          slug: "tokyo-gym",
          name: "Tokyo Gym",
          pref: "tokyo",
          city: "chiyoda",
          latitude: 35.681236,
          longitude: 139.767125,
          distance_km: 0.3,
          last_verified_at: "2024-09-01T12:00:00Z",
        },
      ],
      total: 5,
      page: 1,
      page_size: 20,
      has_more: true,
      has_prev: false,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("requests the nearby gyms endpoint with the expected query", async () => {
    const result = await fetchNearbyGyms({
      lat: 35.681236,
      lng: 139.767125,
      radiusKm: 3,
      perPage: 20,
      pageToken: null,
    });

    expect(mockedApiRequest).toHaveBeenCalledWith(
      "/gyms/nearby",
      expect.objectContaining({
        method: "GET",
        query: {
          lat: 35.681236,
          lng: 139.767125,
          radius_km: 3,
          page: 1,
          page_size: 20,
        },
        signal: undefined,
      }),
    );

    expect(result).toEqual({
      items: [
        {
          id: 1,
          slug: "tokyo-gym",
          name: "Tokyo Gym",
          prefecture: "tokyo",
          city: "chiyoda",
          latitude: 35.681236,
          longitude: 139.767125,
          distanceKm: 0.3,
          lastVerifiedAt: "2024-09-01T12:00:00Z",
        },
      ],
      total: 5,
      page: 1,
      pageSize: 20,
      hasMore: true,
      hasPrev: false,
      pageToken: "2",
    });
  });

  it("passes through a provided AbortSignal", async () => {
    const controller = new AbortController();

    await fetchNearbyGyms({
      lat: 10,
      lng: 20,
      radiusKm: 5,
      perPage: 10,
      pageToken: "3",
      signal: controller.signal,
    });

    expect(mockedApiRequest).toHaveBeenLastCalledWith(
      "/gyms/nearby",
      expect.objectContaining({
        signal: controller.signal,
        query: expect.objectContaining({ page: 3 }),
      }),
    );
  });
});
