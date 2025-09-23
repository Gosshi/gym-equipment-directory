import { fetchGyms, buildGymSearchQuery } from "@/lib/api";

jest.mock("@/lib/apiClient", () => ({
  apiRequest: jest.fn(),
}));

const { apiRequest } = jest.requireMock("@/lib/apiClient") as {
  apiRequest: jest.Mock;
};

describe("lib/api", () => {
  beforeEach(() => {
    apiRequest.mockReset();
  });

  it("builds a query with CSV categories and clamped pagination", () => {
    const query = buildGymSearchQuery({
      q: "bench",
      pref: "tokyo",
      city: "shinjuku",
      cats: ["squat-rack", "", "barbell", "barbell"],
      sort: "fresh",
      page: -10,
      limit: 200,
    });

    expect(query).toEqual({
      q: "bench",
      pref: "tokyo",
      city: "shinjuku",
      equipments: "squat-rack,barbell",
      sort: "freshness",
      page: 1,
      per_page: 50,
      page_token: undefined,
    });
  });

  it("delegates to the gyms search endpoint", async () => {
    apiRequest.mockResolvedValue({
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
      sort: "popular",
      page: 2,
      limit: 30,
      pageToken: "token-1",
    });

    expect(apiRequest).toHaveBeenCalledWith("/gyms/search", {
      method: "GET",
      query: {
        q: "deadlift",
        pref: "tokyo",
        city: "chiyoda",
        equipments: "squat-rack",
        sort: "score",
        page: 2,
        per_page: 30,
        page_token: "token-1",
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
        },
      ],
      meta: {
        total: 1,
        page: 2,
        perPage: 30,
        hasNext: true,
        hasPrev: true,
        pageToken: "next",
      },
    });
  });
});
