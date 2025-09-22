const DEFAULT_TIMEOUT_MS = 8000;
const DEFAULT_BASE_URL = "http://127.0.0.1:8000";

export class ApiError extends Error {
  readonly status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

interface ApiFetchOptions extends RequestInit {
  timeoutMs?: number;
}

export const getApiBaseUrl = () => {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (baseUrl && !baseUrl.startsWith("http")) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must be an absolute URL, including protocol");
  }
  return (baseUrl || DEFAULT_BASE_URL).replace(/\/$/, "");
};

export async function apiFetch<TResponse>(path: string, options: ApiFetchOptions = {}) {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${getApiBaseUrl()}${path}`, {
      ...options,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      const message = await response.text();
      throw new ApiError(message || response.statusText, response.status);
    }

    return (await response.json()) as TResponse;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("Request timed out", 408);
    }

    if (error instanceof ApiError) {
      throw error;
    }

    throw new ApiError(error instanceof Error ? error.message : "Unknown error");
  } finally {
    clearTimeout(timeout);
  }
}
