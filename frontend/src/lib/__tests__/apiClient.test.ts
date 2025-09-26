import { vi } from "vitest";

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
    vi.resetAllMocks();
  });

  it("fetches favorites from the API", async () => {
    const mockJson = vi.fn().mockResolvedValue([]);

    global.fetch = vi.fn().mockResolvedValue({
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

  it("returns an empty array when favorites endpoint responds 404", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      text: vi.fn().mockResolvedValue('{"detail":"Not Found"}'),
    } as unknown as Response);

    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    try {
      await expect(getFavorites("dev-1")).resolves.toEqual([]);
      expect(consoleErrorSpy).not.toHaveBeenCalled();
    } finally {
      consoleErrorSpy.mockRestore();
    }
  });

  it("posts a new favorite", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: vi.fn(),
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
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: vi.fn(),
    } as unknown as Response);

    await removeFavorite("dev-1", 42);

    expect(global.fetch).toHaveBeenCalledWith(
      "http://example.com/me/favorites/42?device_id=dev-1",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("fetches history entries", async () => {
    const mockJson = vi.fn().mockResolvedValue({ items: [] });

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: mockJson,
    } as unknown as Response);

    await getHistory();

    expect(global.fetch).toHaveBeenCalledWith("http://example.com/me/history", expect.any(Object));
  });

  it("returns empty history when the endpoint responds 404", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      text: vi.fn().mockResolvedValue('{"detail":"Not Found"}'),
    } as unknown as Response);

    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    try {
      await expect(getHistory()).resolves.toEqual({ items: [] });
      expect(consoleErrorSpy).not.toHaveBeenCalled();
    } finally {
      consoleErrorSpy.mockRestore();
    }
  });

  it("appends history entries with gymIds", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: vi.fn(),
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

  it("silently ignores missing history endpoints", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      text: vi.fn().mockResolvedValue("{\"detail\":\"Not Found\"}"),
    } as unknown as Response);

    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    try {
      await expect(addHistory({ gymId: 1 })).resolves.toBeUndefined();
      expect(consoleErrorSpy).not.toHaveBeenCalled();
    } finally {
      consoleErrorSpy.mockRestore();
    }
  });

  it("appends a single history entry with gymId", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: vi.fn(),
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
