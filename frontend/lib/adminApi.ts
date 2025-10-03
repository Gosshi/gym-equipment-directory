import { ApiError, getApiBaseUrl } from "@/lib/apiClient";
import type {
  AdminCandidateDetail,
  AdminCandidateItem,
  AdminCandidateListParams,
  AdminCandidateListResponse,
  AdminCandidatePatchPayload,
  ApprovePreviewResponse,
  ApproveRequest,
  ApproveResultResponse,
  ApproveResponse,
} from "@/lib/types";

const MAX_RETRY_ATTEMPTS = 8;
const BASE_BACKOFF_MS = 500;

type QueryValue = string | number | boolean | null | undefined;
type QueryParams = Record<string, QueryValue | QueryValue[]>;

type RequestOptions = RequestInit & {
  query?: QueryParams;
};

const getAdminToken = (): string | null => {
  if (typeof document === "undefined") {
    return null;
  }
  const match = document.cookie.match(/(?:^|; )admin_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
};

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

const buildQueryString = (query: QueryParams | undefined) => {
  if (!query) {
    return "";
  }
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }
    if (Array.isArray(value)) {
      if (value.length > 0) {
        params.set(key, value.join(","));
      }
      return;
    }
    params.set(key, String(value));
  });
  const serialized = params.toString();
  return serialized ? `?${serialized}` : "";
};

const parseRetryAfterHeader = (value: string | null): number | null => {
  if (!value) {
    return null;
  }
  const seconds = Number(value);
  if (!Number.isNaN(seconds)) {
    return Math.max(0, seconds) * 1000;
  }
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) {
    return null;
  }
  const delay = timestamp - Date.now();
  return delay > 0 ? delay : 0;
};

export class AdminApiError extends ApiError {
  constructor(
    message: string,
    status?: number,
    public readonly detail?: unknown,
  ) {
    super(message, status, detail);
    this.name = "AdminApiError";
  }
}

async function request<TResponse>(path: string, { query, headers, ...init }: RequestOptions = {}) {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${path}${buildQueryString(query)}`;
  const finalHeaders = new Headers({
    Accept: "application/json",
    "Content-Type": "application/json",
  });
  if (headers) {
    const provided = new Headers(headers as HeadersInit);
    provided.forEach((value, key) => {
      finalHeaders.set(key, value);
    });
  }
  if (!finalHeaders.has("Authorization")) {
    const token = getAdminToken();
    if (token) {
      finalHeaders.set("Authorization", `Bearer ${token}`);
    }
  }

  for (let attempt = 0; attempt < MAX_RETRY_ATTEMPTS; attempt += 1) {
    const response = await fetch(url, {
      ...init,
      headers: finalHeaders,
      credentials: init.credentials ?? "include",
    });

    if (response.status === 429) {
      const retryAfter = parseRetryAfterHeader(response.headers.get("Retry-After"));
      const fallbackDelay = Math.min(16000, BASE_BACKOFF_MS * 2 ** attempt);
      const delay = retryAfter ?? fallbackDelay;
      if (attempt === MAX_RETRY_ATTEMPTS - 1) {
        const text = await response.text().catch(() => "Too Many Requests");
        throw new AdminApiError(text || "Too Many Requests", 429);
      }
      await sleep(delay);
      continue;
    }

    if (!response.ok) {
      let detail: unknown;
      let message = response.statusText;
      const contentType = response.headers.get("Content-Type") ?? "";
      if (contentType.includes("application/json")) {
        detail = await response.json().catch(() => undefined);
        if (detail && typeof detail === "object" && "detail" in detail) {
          const detailMessage = (detail as { detail?: unknown }).detail;
          if (typeof detailMessage === "string") {
            message = detailMessage;
          }
        }
      } else {
        message = await response.text().catch(() => response.statusText);
      }
      throw new AdminApiError(message || "Request failed", response.status, detail);
    }

    if (response.status === 204) {
      return undefined as TResponse;
    }

    const contentType = response.headers.get("Content-Type") ?? "";
    if (contentType.includes("application/json")) {
      return (await response.json()) as TResponse;
    }
    const text = await response.text();
    return JSON.parse(text) as TResponse;
  }

  throw new AdminApiError("Request retry limit reached", 429);
}

export const listCandidates = (params: AdminCandidateListParams = {}) => {
  const query: QueryParams = {};
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }
    query[key] = value as QueryValue | QueryValue[];
  });
  return request<AdminCandidateListResponse>("/admin/candidates", {
    query,
  });
};

export const getCandidate = (id: number) =>
  request<AdminCandidateDetail>(`/admin/candidates/${id}`);

export const patchCandidate = (id: number, payload: AdminCandidatePatchPayload) =>
  request<AdminCandidateItem>(`/admin/candidates/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

export const approveCandidate = (id: number, payload: ApproveRequest) =>
  request<ApproveResponse>(`/admin/candidates/${id}/approve`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const rejectCandidate = (id: number, reason: string) =>
  request<AdminCandidateItem>(`/admin/candidates/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });

export type {
  AdminCandidateDetail,
  AdminCandidateItem,
  AdminCandidateListParams,
  AdminCandidateListResponse,
  AdminCandidatePatchPayload,
  ApproveOverride,
  ApprovePreviewResponse,
  ApproveRequest,
  ApproveResponse,
  ApproveResultResponse,
  ApproveSummary,
  EquipmentAssign,
} from "@/lib/types";
