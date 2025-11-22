import { authClient } from "@/auth/authClient";
import type { GymSummary } from "@/types/gym";

const DEFAULT_TIMEOUT_MS = 8000;
const DEFAULT_BASE_URL = "http://127.0.0.1:8000";

export class ApiError extends Error {
  readonly status?: number;
  readonly details?: unknown;

  constructor(message: string, status?: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

export interface ApiRequestOptions extends RequestInit {
  timeoutMs?: number;
  query?: Record<string, unknown>;
}

export const getApiBaseUrl = () => {
  const baseUrl =
    process.env.NEXT_PUBLIC_API_URL?.trim() ??
    process.env.NEXT_PUBLIC_API_BASE?.trim() ??
    process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (baseUrl && !baseUrl.startsWith("http")) {
    throw new Error(
      "NEXT_PUBLIC_API_URL (or _BASE / _BASE_URL) must be an absolute URL, including protocol",
    );
  }
  return (baseUrl || DEFAULT_BASE_URL).replace(/\/$/, "");
};

const buildQueryString = (query: Record<string, unknown> | undefined) => {
  if (!query) {
    return "";
  }

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") {
      continue;
    }

    if (Array.isArray(value)) {
      if (value.length > 0) {
        params.set(key, value.join(","));
      }
      continue;
    }

    params.set(key, String(value));
  }

  const serialized = params.toString();
  return serialized ? `?${serialized}` : "";
};

const normalizeHeaders = (input?: HeadersInit): Record<string, string> => {
  if (!input) {
    return {};
  }

  if (input instanceof Headers) {
    const entries: Record<string, string> = {};
    input.forEach((value, key) => {
      entries[key] = value;
    });
    return entries;
  }

  if (Array.isArray(input)) {
    const entries: Record<string, string> = {};
    for (const [key, value] of input) {
      if (key) {
        entries[key] = String(value);
      }
    }
    return entries;
  }

  const entries: Record<string, string> = {};
  for (const [key, value] of Object.entries(input)) {
    if (value !== undefined && value !== null) {
      entries[key] = String(value);
    }
  }
  return entries;
};

const hasHeader = (headers: Record<string, string>, name: string) =>
  Object.keys(headers).some(key => key.toLowerCase() === name.toLowerCase());

const ensureCanonicalHeader = (headers: Record<string, string>, name: string, fallback: string) => {
  const existingKey = Object.keys(headers).find(key => key.toLowerCase() === name.toLowerCase());
  if (existingKey) {
    if (existingKey !== name) {
      const value = headers[existingKey];
      delete headers[existingKey];
      headers[name] = value;
    }
    return;
  }
  headers[name] = fallback;
};

export async function apiRequest<TResponse>(
  path: string,
  { timeoutMs = DEFAULT_TIMEOUT_MS, query, headers, signal, ...init }: ApiRequestOptions = {},
): Promise<TResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  const url = `${getApiBaseUrl()}${path}${buildQueryString(query)}`;

  try {
    if (signal) {
      if (signal.aborted) {
        controller.abort();
      } else {
        signal.addEventListener("abort", () => controller.abort(), { once: true });
      }
    }

    let token: string | null = null;
    try {
      token = await authClient.getToken();
    } catch (error) {
      if (process.env.NODE_ENV !== "production" && typeof window !== "undefined") {
        // eslint-disable-next-line no-console
        console.warn("Failed to obtain auth token", error);
      }
    }

    const headersObject = normalizeHeaders(headers);
    ensureCanonicalHeader(headersObject, "Accept", "application/json");
    ensureCanonicalHeader(headersObject, "Content-Type", "application/json");
    if (token && !hasHeader(headersObject, "Authorization")) {
      headersObject.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      ...init,
      headers: headersObject,
      signal: controller.signal,
    });

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      if (typeof window !== "undefined") {
        // eslint-disable-next-line no-console
        console.error("API error", { url, status: response.status, body: text });
      }
      throw new ApiError(text || response.statusText, response.status);
    }

    if (response.status === 204) {
      return undefined as TResponse;
    }

    return (await response.json()) as TResponse;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("Request timed out", 408);
    }

    if (error instanceof ApiError) {
      throw error;
    }

    const message = error instanceof Error ? error.message : "Unknown error";
    throw new ApiError(message);
  } finally {
    clearTimeout(timeout);
  }
}

export async function apiFetch<TResponse>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<TResponse> {
  return apiRequest<TResponse>(path, options);
}

// Favorites エンドポイントは配列 (FavoriteItem[]) を直接返す。
export type FavoritesArrayResponse = unknown[];

export interface HistoryResponse {
  items: GymSummary[];
}

export const getFavorites = async (deviceId: string) => {
  try {
    return await apiRequest<FavoritesArrayResponse>(
      `/me/favorites?device_id=${encodeURIComponent(deviceId)}`,
      {
        method: "GET",
      },
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return [];
    }
    throw error;
  }
};

export const addFavorite = (deviceId: string, gymId: number) =>
  apiRequest<void>("/me/favorites", {
    method: "POST",
    body: JSON.stringify({ device_id: deviceId, gym_id: gymId }),
  });

export const removeFavorite = (deviceId: string, gymId: number) =>
  apiRequest<void>(`/me/favorites/${gymId}?device_id=${encodeURIComponent(deviceId)}`, {
    method: "DELETE",
  });

type HistoryPayload = { gymId: number; gymIds?: never } | { gymIds: number[]; gymId?: never };

export const getHistory = async () => {
  try {
    return await apiRequest<HistoryResponse>("/me/history", { method: "GET" });
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return { items: [] };
    }
    throw error;
  }
};

export const addHistory = (payload: HistoryPayload) => {
  const hasGymId = typeof payload.gymId === "number";
  const hasGymIds = Array.isArray(payload.gymIds) && payload.gymIds.length > 0;

  if (!hasGymId && !hasGymIds) {
    throw new Error("History payload must include gymId or non-empty gymIds.");
  }

  return apiRequest<void>("/me/history", {
    method: "POST",
    body: JSON.stringify(payload),
  });
};
