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
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (baseUrl && !baseUrl.startsWith("http")) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must be an absolute URL, including protocol");
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

export async function apiRequest<TResponse>(
  path: string,
  { timeoutMs = DEFAULT_TIMEOUT_MS, query, headers, ...init }: ApiRequestOptions = {},
): Promise<TResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  const url = `${getApiBaseUrl()}${path}${buildQueryString(query)}`;

  try {
    const response = await fetch(url, {
      ...init,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(headers || {}),
      },
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
