import { ApiError } from "@/lib/apiClient";
import { searchGyms } from "@/services/gyms";

describe("searchGyms", () => {
  const originalEnv = process.env.NEXT_PUBLIC_API_BASE_URL;
  const originalFetch = global.fetch;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://example.com";
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = originalEnv;
    global.fetch = originalFetch;
    jest.resetAllMocks();
  });

  it("builds the expected query parameters and normalises the response", async () => {
    const mockJson = jest.fn().mockResolvedValue({
      items: [
        {
          id: 1,
          slug: "test-gym",
          name: "テストジム",
          pref: "tokyo",
          city: "shinjuku",
          equipments: [
            { name: "Squat Rack", slug: "squat-rack" },
            { name: "Dumbbell" },
          ],
          thumbnail_url: "https://example.com/thumb.jpg",
          score: 1.5,
          last_verified_at: "2024-09-01T12:00:00Z",
        },
      ],
      total: 1,
      has_next: false,
      page_token: null,
    });

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: mockJson,
    } as unknown as Response);

    const result = await searchGyms({
      q: "weight",
      prefecture: "tokyo",
      city: "shinjuku",
      equipmentMatch: "any",
      page: 2,
      perPage: 10,
    });

    expect(global.fetch).toHaveBeenCalledWith(
      "http://example.com/gyms/search?q=weight&pref=tokyo&city=shinjuku&equipment_match=any&page=2&per_page=10",
      expect.objectContaining({
        headers: expect.objectContaining({
          Accept: "application/json",
          "Content-Type": "application/json",
        }),
        method: "GET",
      }),
    );

    expect(result.items[0]).toMatchObject({
      id: 1,
      slug: "test-gym",
      name: "テストジム",
      prefecture: "tokyo",
      city: "shinjuku",
      equipments: ["Squat Rack", "Dumbbell"],
      thumbnailUrl: "https://example.com/thumb.jpg",
      score: 1.5,
      lastVerifiedAt: "2024-09-01T12:00:00Z",
    });
    expect(result.meta).toEqual({ total: 1, hasNext: false, pageToken: null });
  });

  it("throws an ApiError when the request fails", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Server Error",
      text: jest.fn().mockResolvedValue("Internal error"),
    } as unknown as Response);

    await expect(searchGyms()).rejects.toBeInstanceOf(ApiError);
  });
});
