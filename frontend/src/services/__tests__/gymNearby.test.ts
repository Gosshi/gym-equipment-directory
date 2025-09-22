import { apiRequest } from "@/lib/apiClient";
import { fetchNearbyGyms } from "@/services/gymNearby";

jest.mock("@/lib/apiClient", () => ({
  apiRequest: jest.fn(),
}));

describe("fetchNearbyGyms", () => {
  beforeEach(() => {
    (apiRequest as jest.Mock).mockResolvedValue({
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
      has_next: true,
      page_token: "next",
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("requests the nearby gyms endpoint with the expected query", async () => {
    const result = await fetchNearbyGyms({
      lat: 35.681236,
      lng: 139.767125,
      radiusKm: 3,
      perPage: 20,
      pageToken: null,
    });

    expect(apiRequest).toHaveBeenCalledWith("/gyms/nearby", expect.objectContaining({
      method: "GET",
      query: {
        lat: 35.681236,
        lng: 139.767125,
        radius_km: 3,
        per_page: 20,
        page_token: undefined,
      },
      signal: undefined,
    }));

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
      hasNext: true,
      pageToken: "next",
    });
  });

  it("passes through a provided AbortSignal", async () => {
    const controller = new AbortController();

    await fetchNearbyGyms({
      lat: 10,
      lng: 20,
      radiusKm: 5,
      perPage: 10,
      pageToken: "token",
      signal: controller.signal,
    });

    expect(apiRequest).toHaveBeenLastCalledWith("/gyms/nearby", expect.objectContaining({
      signal: controller.signal,
      query: expect.objectContaining({ page_token: "token" }),
    }));
  });
});
