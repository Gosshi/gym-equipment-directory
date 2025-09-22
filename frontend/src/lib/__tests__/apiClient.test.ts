import { getFavorites, addFavorite, removeFavorite, getHistory, addHistory } from "@/lib/apiClient";

describe("apiClient favorites/history endpoints", () => {
  const originalEnvUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  const originalEnvBase = process.env.NEXT_PUBLIC_API_BASE;
  const originalFetch = global.fetch;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://example.com";
    process.env.NEXT_PUBLIC_API_BASE = "http://example.com";
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = originalEnvUrl;
    process.env.NEXT_PUBLIC_API_BASE = originalEnvBase;
    global.fetch = originalFetch;
    jest.resetAllMocks();
  });

  it("fetches favorites from the API", async () => {
    const mockJson = jest.fn().mockResolvedValue([]);

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: mockJson,
    } as unknown as Response);

    await getFavorites("dev-1");

    expect(global.fetch).toHaveBeenCalledWith(
      "http://example.com/me/favorites?device_id=dev-1",
      expect.any(Object),
    );
  });

  it("posts a new favorite", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: jest.fn(),
    } as unknown as Response);

  await addFavorite("dev-1", 42);

    expect(global.fetch).toHaveBeenCalledWith(
      "http://example.com/me/favorites",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ device_id: "dev-1", gym_id: 42 }),
      }),
    );
  });

  it("removes a favorite", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: jest.fn(),
    } as unknown as Response);

  await removeFavorite("dev-1", 42);

    expect(global.fetch).toHaveBeenCalledWith(
      "http://example.com/me/favorites/42?device_id=dev-1",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("fetches history entries", async () => {
    const mockJson = jest.fn().mockResolvedValue({ items: [] });

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: mockJson,
    } as unknown as Response);

    await getHistory();

    expect(global.fetch).toHaveBeenCalledWith("http://example.com/me/history", expect.any(Object));
  });

  it("appends history entries with gymIds", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: jest.fn(),
    } as unknown as Response);

    await addHistory({ gymIds: [1, 2, 3] });

    expect(global.fetch).toHaveBeenCalledWith(
      "http://example.com/me/history",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ gymIds: [1, 2, 3] }),
      }),
    );
  });

  it("appends a single history entry with gymId", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: jest.fn(),
    } as unknown as Response);

    await addHistory({ gymId: 7 });

    expect(global.fetch).toHaveBeenCalledWith(
      "http://example.com/me/history",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ gymId: 7 }),
      }),
    );
  });

  it("throws when history payload is empty", () => {
    expect(() => addHistory({ gymIds: [] })).toThrow(/must include gymId or non-empty gymIds/i);
  });
});
