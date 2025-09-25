import { vi } from "vitest";

import { fetchGyms, buildGymSearchQuery } from "@/lib/api";
import { apiRequest } from "@/lib/apiClient";

vi.mock("@/lib/apiClient", () => ({
  apiRequest: vi.fn(),
}));

const mockedApiRequest = vi.mocked(apiRequest);

describe("lib/api", () => {
  beforeEach(() => {
    mockedApiRequest.mockReset();
  });

  it("builds a query with CSV categories and clamped pagination", () => {
    const query = buildGymSearchQuery({
      q: "bench",
      pref: "tokyo",
      city: "shinjuku",
      cats: ["squat-rack", "", "barbell", "barbell"],
      sort: "name",
      order: "asc",
      page: -10,
      limit: 200,
    });

    expect(query).toEqual({
      q: "bench",
      pref: "tokyo",
      city: "shinjuku",
      equipments: "squat-rack,barbell",
      sort: "gym_name",
      order: "asc",
      page: 1,
      page_size: 100,
      per_page: 100,
      page_token: undefined,
    });
  });

  it("includes location filters when coordinates are provided", () => {
    const query = buildGymSearchQuery({
      lat: 91,
      lng: -200,
      radiusKm: 2,
    });

    expect(query.lat).toBeCloseTo(90);
    expect(query.lng).toBeCloseTo(-180);
    expect(query.radius_km).toBe(2);
  });

  it("delegates to the gyms search endpoint", async () => {
    mockedApiRequest.mockResolvedValue({
      items: [
        {
          id: 1,
          slug: "dummy-gym",
          name: "Dummy Gym",
          city: "chiyoda",
          pref: "tokyo",
          equipments: ["Squat Rack"],
          thumbnail_url: null,
          score: 0.5,
          last_verified_at: "2024-09-01T12:00:00Z",
        },
      ],
      total: 1,
      page: 2,
      per_page: 30,
      has_next: true,
      has_prev: true,
      page_token: "next",
    });

    const response = await fetchGyms({
      q: "deadlift",
      pref: "tokyo",
      city: "chiyoda",
      cats: ["squat-rack"],
      sort: "rating",
      order: "desc",
      page: 2,
      limit: 30,
      pageToken: "token-1",
      lat: 35.6895,
      lng: 139.6917,
      radiusKm: 7,
    });

    expect(mockedApiRequest).toHaveBeenCalledWith("/gyms/search", {
      method: "GET",
      query: {
        q: "deadlift",
        pref: "tokyo",
        city: "chiyoda",
        equipments: "squat-rack",
        sort: "score",
        order: "desc",
        page: 2,
        page_size: 30,
        per_page: 30,
        page_token: "token-1",
        lat: expect.any(Number),
        lng: expect.any(Number),
        radius_km: 7,
      },
      signal: undefined,
    });

    expect(response).toEqual({
      items: [
        {
          id: 1,
          slug: "dummy-gym",
          name: "Dummy Gym",
          city: "chiyoda",
          prefecture: "tokyo",
          address: undefined,
          equipments: ["Squat Rack"],
          thumbnailUrl: null,
          score: 0.5,
          lastVerifiedAt: "2024-09-01T12:00:00Z",
          latitude: null,
          longitude: null,
        },
      ],
      meta: {
        total: 1,
        page: 2,
        perPage: 30,
        hasNext: true,
        hasPrev: true,
        hasMore: true,
        pageToken: "next",
      },
    });
  });
});
