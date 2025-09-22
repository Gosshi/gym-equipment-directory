import { ApiError } from "@/lib/apiClient";
import { getGymBySlug, searchGyms } from "@/services/gyms";

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

describe("getGymBySlug", () => {
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

  it("normalises the response data", async () => {
    const mockJson = jest.fn().mockResolvedValue({
      id: 42,
      slug: "tokyo-gym",
      name: "Tokyo Gym",
      pref: "tokyo",
      city: "shibuya",
      full_address: "東京都渋谷区1-2-3",
      equipments: [{ name: "Squat Rack" }, "Dumbbells"],
      main_image_url: "https://example.com/hero.jpg",
      images: [
        "https://example.com/hero.jpg",
        { url: "https://example.com/inside.jpg" },
      ],
      opening_hours: "10:00-22:00",
      phone: "03-1234-5678",
      website_url: "https://gym.example.com",
      description: "テスト用のジムです。",
    });

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: mockJson,
    } as unknown as Response);

    const result = await getGymBySlug("tokyo-gym");

    expect(global.fetch).toHaveBeenCalledWith(
      "http://example.com/gyms/tokyo-gym",
      expect.objectContaining({
        headers: expect.objectContaining({
          Accept: "application/json",
          "Content-Type": "application/json",
        }),
        method: "GET",
      }),
    );

    expect(result).toEqual({
      id: 42,
      slug: "tokyo-gym",
      name: "Tokyo Gym",
      prefecture: "tokyo",
      city: "shibuya",
      address: "東京都渋谷区1-2-3",
      equipments: ["Squat Rack", "Dumbbells"],
      thumbnailUrl: "https://example.com/hero.jpg",
      images: ["https://example.com/hero.jpg", "https://example.com/inside.jpg"],
      openingHours: "10:00-22:00",
      phone: "03-1234-5678",
      website: "https://gym.example.com",
      description: "テスト用のジムです。",
    });
  });

  it("throws an ApiError on 404", async () => {
    const mockText = jest.fn().mockResolvedValue("Not found");

    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      text: mockText,
    } as unknown as Response);

    await expect(getGymBySlug("missing"))
      .rejects.toEqual(expect.objectContaining({ status: 404 }));
  });

  it("throws an ApiError on server errors", async () => {
    const mockText = jest.fn().mockResolvedValue("Server error");

    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Server Error",
      text: mockText,
    } as unknown as Response);

    await expect(getGymBySlug("tokyo-gym"))
      .rejects.toEqual(expect.objectContaining({ status: 500 }));
  });
});
