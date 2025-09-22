import { ApiError } from "@/lib/apiClient";
import { addFavorite, listFavorites, removeFavorite } from "@/services/favorites";

describe("favorites service", () => {
  const originalEnv = process.env.NEXT_PUBLIC_API_BASE_URL;
  const originalFetch = global.fetch;

  beforeEach(() => {
  process.env.NEXT_PUBLIC_API_BASE_URL = undefined; // デフォルト (127.0.0.1:8000) 利用
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = originalEnv;
    global.fetch = originalFetch;
    jest.resetAllMocks();
  });

  it("fetches and normalises favorites", async () => {
    const mockJson = jest.fn().mockResolvedValue([
      {
        gym_id: 10,
        slug: "tokyo-gym",
        name: "Tokyo Gym",
        pref: "tokyo",
        city: "shibuya",
        address: "東京都渋谷区1-2-3",
        thumbnail_url: "https://example.com/thumb.jpg",
        last_verified_at: "2024-09-01T12:00:00Z",
        created_at: "2024-09-10T09:30:00Z",
      },
    ]);

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: mockJson,
    } as unknown as Response);

    const result = await listFavorites("device-123");

    expect(global.fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/me/favorites?device_id=device-123",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          Accept: "application/json",
          "Content-Type": "application/json",
        }),
      }),
    );

    expect(result).toEqual([
      {
        createdAt: "2024-09-10T09:30:00Z",
        gym: {
          id: 10,
          slug: "tokyo-gym",
          name: "Tokyo Gym",
          prefecture: "tokyo",
          city: "shibuya",
          address: "東京都渋谷区1-2-3",
          thumbnailUrl: "https://example.com/thumb.jpg",
          lastVerifiedAt: "2024-09-01T12:00:00Z",
        },
      },
    ]);
  });

  it("throws an ApiError when listFavorites fails", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Server Error",
      text: jest.fn().mockResolvedValue("Internal error"),
    } as unknown as Response);

    await expect(listFavorites("device-123")).rejects.toBeInstanceOf(ApiError);
  });

  it("sends a POST request to add a favorite", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: jest.fn(),
    } as unknown as Response);

    await addFavorite(42, "device-xyz");

    expect(global.fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/me/favorites",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ device_id: "device-xyz", gym_id: 42 }),
      }),
    );
  });

  it("sends a DELETE request to remove a favorite", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: jest.fn(),
    } as unknown as Response);

    await removeFavorite(42, "device-xyz");

    expect(global.fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/me/favorites/42?device_id=device-xyz",
      expect.objectContaining({
        method: "DELETE",
      }),
    );
  });
});
