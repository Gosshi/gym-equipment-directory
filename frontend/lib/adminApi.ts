import { ApiError, getApiBaseUrl } from "@/lib/apiClient";

const MAX_RETRY_ATTEMPTS = 8;
const BASE_BACKOFF_MS = 500;

type JsonRecord = Record<string, unknown>;

type RequestOptions = RequestInit & {
  query?: Record<string, unknown>;
};

const getAdminToken = (): string | null => {
  if (typeof document === "undefined") {
    return null;
  }
  const match = document.cookie.match(/(?:^|; )admin_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
};

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

const buildQueryString = (query: Record<string, unknown> | undefined) => {
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
      const fallbackDelay = BASE_BACKOFF_MS * 2 ** attempt;
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

export interface AdminSourceRef {
  id: number;
  title?: string | null;
  url?: string | null;
}

export interface AdminCandidateItem {
  id: number;
  status: string;
  name_raw: string;
  address_raw?: string | null;
  pref_slug?: string | null;
  city_slug?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  parsed_json?: JsonRecord | null;
  source: AdminSourceRef;
  fetched_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScrapedPageInfo {
  url: string;
  fetched_at: string;
  http_status?: number | null;
}

export interface SimilarGymInfo {
  gym_id: number;
  gym_slug: string;
  gym_name: string;
}

export interface AdminCandidateDetail extends AdminCandidateItem {
  scraped_page: ScrapedPageInfo;
  similar?: SimilarGymInfo[] | null;
}

export interface AdminCandidateListResponse {
  items: AdminCandidateItem[];
  next_cursor?: string | null;
  count: number;
}

export interface AdminCandidateListParams {
  status?: string | null;
  source?: string | null;
  q?: string | null;
  pref?: string | null;
  city?: string | null;
  cursor?: string | null;
  limit?: number;
}

export interface AdminCandidatePatchPayload {
  name_raw?: string | null;
  address_raw?: string | null;
  pref_slug?: string | null;
  city_slug?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  parsed_json?: JsonRecord | null;
}

export interface EquipmentAssign {
  slug: string;
  availability?: "present" | "absent" | "unknown";
  count?: number | null;
  max_weight_kg?: number | null;
}

export interface ApproveOverride {
  name?: string | null;
  pref_slug?: string | null;
  city_slug?: string | null;
  address?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

export interface ApproveRequestPayload {
  dry_run: boolean;
  override?: ApproveOverride | null;
  equipments?: EquipmentAssign[] | null;
}

export interface GymUpsertPreview {
  slug: string;
  name: string;
  canonical_id: string;
  pref_slug?: string | null;
  city_slug?: string | null;
  address?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

export interface EquipmentUpsertSummary {
  inserted: number;
  updated: number;
  total: number;
}

export interface ApproveSummary {
  gym: GymUpsertPreview;
  equipments: EquipmentUpsertSummary;
}

export interface ApprovePreviewResponse {
  preview: ApproveSummary;
}

export interface ApproveResultResponse {
  result: ApproveSummary;
}

export interface RejectRequestPayload {
  reason: string;
}

export const listCandidates = (params: AdminCandidateListParams = {}) =>
  request<AdminCandidateListResponse>("/admin/candidates", {
    query: params,
  });

export const getCandidate = (id: number) =>
  request<AdminCandidateDetail>(`/admin/candidates/${id}`);

export const patchCandidate = (id: number, payload: AdminCandidatePatchPayload) =>
  request<AdminCandidateItem>(`/admin/candidates/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

export const approveCandidate = (id: number, payload: ApproveRequestPayload) =>
  request<ApprovePreviewResponse | ApproveResultResponse>(`/admin/candidates/${id}/approve`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const rejectCandidate = (id: number, payload: RejectRequestPayload) =>
  request<AdminCandidateItem>(`/admin/candidates/${id}/reject`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
