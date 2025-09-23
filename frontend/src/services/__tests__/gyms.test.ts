import { searchGyms } from "@/services/gyms";

jest.mock("@/lib/apiClient", () => ({
  apiRequest: jest.fn(),
}));

const { apiRequest } = jest.requireMock("@/lib/apiClient") as {
  apiRequest: jest.Mock;
};

describe("searchGyms", () => {
  beforeEach(() => {
    apiRequest.mockReset();
  });

  it("calls the gyms search endpoint with normalized parameters", async () => {
    apiRequest.mockResolvedValue({
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
      sort: "fresh",
      page: 2,
      limit: 24,
      lat: 34.7,
      lng: 135.5,
      distance: 9,
    });

    expect(apiRequest).toHaveBeenCalledWith("/gyms/search", {
      method: "GET",
      query: {
        q: "bench press",
        pref: "tokyo",
        city: "shinjuku",
        equipments: "squat-rack,dumbbell",
        sort: "freshness",
        page: 2,
        per_page: 24,
        page_token: undefined,
        lat: expect.any(Number),
        lng: expect.any(Number),
        distance: 9,
      },
      signal: undefined,
    });
  });

  it("normalizes the response payload into GymSummary items", async () => {
    apiRequest.mockResolvedValue({
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
        },
      ],
      meta: {
        total: 1,
        page: 1,
        perPage: 20,
        hasNext: false,
        hasPrev: false,
        pageToken: null,
      },
    });
  });

  it("throws the error received from the client", async () => {
    const error = new Error("Request failed");
    apiRequest.mockRejectedValue(error);

    await expect(searchGyms()).rejects.toBe(error);
  });
});
