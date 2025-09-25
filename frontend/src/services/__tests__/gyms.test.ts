import { vi } from "vitest";

import { apiRequest } from "@/lib/apiClient";
import { searchGyms } from "@/services/gyms";

vi.mock("@/lib/apiClient", () => ({
  apiRequest: vi.fn(),
}));

const mockedApiRequest = vi.mocked(apiRequest);

describe("searchGyms", () => {
  beforeEach(() => {
    mockedApiRequest.mockReset();
  });

  it("calls the gyms search endpoint with normalized parameters", async () => {
    mockedApiRequest.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      per_page: 24,
      has_next: false,
      has_prev: false,
      page_token: null,
    });

    await searchGyms({
      q: "bench press",
      prefecture: "tokyo",
      city: "shinjuku",
      categories: ["squat-rack", "dumbbell"],
      sort: "reviews",
      order: "desc",
      page: 2,
      limit: 24,
      lat: 34.7,
      lng: 135.5,
      radiusKm: 9,
    });

    expect(mockedApiRequest).toHaveBeenCalledWith("/gyms/search", {
      method: "GET",
      query: {
        q: "bench press",
        pref: "tokyo",
        city: "shinjuku",
        equipments: "squat-rack,dumbbell",
        sort: "richness",
        order: "desc",
        page: 2,
        page_size: 24,
        per_page: 24,
        page_token: undefined,
        lat: 34.7,
        lng: 135.5,
        radius_km: 9,
      },
      signal: undefined,
    });
  });

  it("normalizes the response payload into GymSummary items", async () => {
    mockedApiRequest.mockResolvedValue({
      items: [
        {
          id: 1,
          slug: "dummy-gym",
          name: "Dummy Gym",
          city: "shinjuku",
          pref: "tokyo",
          equipments: ["Squat Rack", null, "Barbell"],
          thumbnail_url: "https://example.com/thumb.jpg",
          score: 1.2,
          last_verified_at: "2024-09-01T12:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
      has_next: false,
      has_prev: false,
      page_token: null,
    });

    const response = await searchGyms();

    expect(response).toEqual({
      items: [
        {
          id: 1,
          slug: "dummy-gym",
          name: "Dummy Gym",
          city: "shinjuku",
          prefecture: "tokyo",
          address: undefined,
          equipments: ["Squat Rack", "Barbell"],
          thumbnailUrl: "https://example.com/thumb.jpg",
          score: 1.2,
          lastVerifiedAt: "2024-09-01T12:00:00Z",
          latitude: null,
          longitude: null,
        },
      ],
      meta: {
        total: 1,
        page: 1,
        perPage: 20,
        hasNext: false,
        hasPrev: false,
        hasMore: false,
        pageToken: null,
      },
    });
  });

  it("extracts coordinates from the search response when present", async () => {
    mockedApiRequest.mockResolvedValue({
      items: [
        {
          id: 2,
          slug: "gym-with-coords",
          name: "Gym With Coordinates",
          city: "meguro",
          prefecture: "tokyo",
          lat: "35.652832",
          lng: 139.709389,
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
      has_next: false,
      has_prev: false,
      page_token: null,
    });

    const response = await searchGyms();

    expect(response.items[0]).toMatchObject({
      slug: "gym-with-coords",
      latitude: 35.652832,
      longitude: 139.709389,
    });
  });

  it("throws the error received from the client", async () => {
    const error = new Error("Request failed");
    mockedApiRequest.mockRejectedValue(error);

    await expect(searchGyms()).rejects.toBe(error);
  });
});
