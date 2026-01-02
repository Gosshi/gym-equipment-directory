import { apiRequest, ApiError } from "./apiClient";

export class AdminApiError extends Error {
  readonly status?: number;
  readonly detail?: unknown;
  constructor(message: string, status?: number, detail?: unknown) {
    super(message);
    this.name = "AdminApiError";
    this.status = status;
    this.detail = detail;
  }
}

// Candidate list types
export interface AdminCandidateSource {
  id?: number | string | null;
  title?: string | null;
  url?: string | null;
}

export interface AdminCandidateItem {
  id: number;
  status: string;
  name_raw?: string | null;
  address_raw?: string | null;
  pref_slug?: string | null;
  city_slug?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  categories?: string[]; // gym, pool, court, hall, field, martial_arts, archery
  category?: string | null; // Computed alias for categories[0], backward compat
  fetched_at?: string | null;
  updated_at?: string | null;
  source?: AdminCandidateSource | null;
  official_url?: string | null; // 手動入稿時などに付与される公式URL
  parsed_json?: Record<string, unknown> | null;
}

export interface AdminCandidateDetail extends AdminCandidateItem {
  parsed_json?: Record<string, unknown> | null;
  scraped_page: {
    url: string;
    fetched_at?: string | null;
    http_status?: number | null;
  };
  similar?: Array<{ gym_id: number; gym_slug: string; gym_name: string }>;
  gym_id?: number | null;
}

export interface AdminCandidateListParams {
  status?: "new" | "reviewing" | "approved" | "rejected" | undefined;
  source?: string | undefined;
  q?: string | undefined;
  pref?: string | undefined;
  city?: string | undefined;
  category?: string | undefined; // gym, pool, court, hall, field, martial_arts, archery
  has_coords?: boolean | undefined; // lat/lon有無フィルター
  cursor?: string | undefined;
}

export interface AdminCandidateListResponse {
  items: AdminCandidateItem[];
  next_cursor?: string | null;
  count?: number | null;
}

// Approve/Reject types
export interface ApproveOverride {
  name?: string;
  pref_slug?: string;
  city_slug?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  official_url?: string;
}

export interface ApproveEquipmentsSummary {
  inserted: number;
  updated: number;
  total: number;
}

export interface ApproveGymSummary {
  id: number;
  slug: string;
  canonical_id: number | string;
  name: string;
  address?: string | null;
  pref_slug?: string | null;
  city_slug?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

export interface ApproveSummary {
  gym: ApproveGymSummary;
  equipments: ApproveEquipmentsSummary;
}

export interface ApprovePreviewResponse {
  preview: ApproveSummary;
}

export interface ApproveResultResponse {
  result: ApproveSummary & { gym: ApproveGymSummary };
}

export type ApproveResponse = ApprovePreviewResponse | ApproveResultResponse;

// Bulk responses (approximation of backend schema)
export interface BulkApproveItemResult {
  id: number;
  status: "success" | "error";
  message?: string;
}
export interface BulkApproveResponse {
  success_ids: number[];
  failure_items: BulkApproveItemResult[];
  dry_run: boolean;
}
export interface BulkRejectItemResult {
  id: number;
  status: "success" | "error";
  message?: string;
}
export interface BulkRejectResponse {
  success_ids: number[];
  failure_items: BulkRejectItemResult[];
  dry_run: boolean;
}

export interface BulkScrapeItem {
  candidate_id: number;
  status: "queued" | "success" | "failed";
  failure_reason?: string | null;
}

export interface BulkScrapeJobResponse {
  job_id: string;
  status: "queued" | "running" | "completed";
  total_count: number;
  completed_count: number;
  success_count: number;
  failure_count: number;
  dry_run: boolean;
  items: BulkScrapeItem[];
}

const wrapError = (error: unknown): never => {
  if (error instanceof AdminApiError) {
    throw error;
  }
  if (error instanceof ApiError) {
    throw new AdminApiError(error.message || "Admin API error", error.status, error.details);
  }
  if (error instanceof Error) {
    throw new AdminApiError(error.message);
  }
  throw new AdminApiError("Unknown Admin API error");
};

export async function listCandidates(
  params: AdminCandidateListParams,
): Promise<AdminCandidateListResponse> {
  try {
    // 明示的にクエリオブジェクトへ変換（undefinedは除去）
    const query: Record<string, unknown> = {};
    if (params.status) query.status = params.status;
    if (params.source) query.source = params.source;
    if (params.q) query.q = params.q;
    if (params.pref) query.pref = params.pref;
    if (params.city) query.city = params.city;
    if (params.category) query.category = params.category;
    if (params.has_coords !== undefined) query.has_coords = params.has_coords;
    if (params.cursor) query.cursor = params.cursor;
    return await apiRequest<AdminCandidateListResponse>("/admin/candidates", {
      method: "GET",
      query,
    });
  } catch (err) {
    wrapError(err);
  }
  throw new AdminApiError("Failed to list candidates: unreachable state");
}

export async function getCandidate(id: number): Promise<AdminCandidateDetail> {
  try {
    return await apiRequest<AdminCandidateDetail>(`/admin/candidates/${id}`, {
      method: "GET",
    });
  } catch (err) {
    wrapError(err);
  }
  throw new AdminApiError("Failed to get candidate: unreachable state");
}

// Payload types -------------------------------------------------
export interface AdminCandidateCreatePayload {
  name_raw: string;
  address_raw?: string | null;
  pref_slug: string;
  city_slug: string;
  latitude?: number | null;
  longitude?: number | null;
  parsed_json?: Record<string, unknown> | null;
  official_url?: string | null; // 任意: 公式サイト URL
}

export interface AdminCandidatePatchPayload {
  name_raw?: string | null;
  address_raw?: string | null;
  pref_slug?: string | null;
  city_slug?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  parsed_json?: Record<string, unknown> | null;
  official_url?: string | null;
}

export async function patchCandidate(
  id: number,
  payload: AdminCandidatePatchPayload,
): Promise<AdminCandidateItem> {
  try {
    return await apiRequest<AdminCandidateItem>(`/admin/candidates/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  } catch (err) {
    wrapError(err);
  }
  throw new AdminApiError("Failed to patch candidate: unreachable state");
}

export async function createCandidate(
  payload: AdminCandidateCreatePayload,
): Promise<AdminCandidateItem> {
  try {
    return await apiRequest<AdminCandidateItem>(`/admin/candidates`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  } catch (err) {
    wrapError(err);
  }
  throw new AdminApiError("Failed to create candidate: unreachable state");
}

export async function approveCandidate(
  id: number,
  payload: { dry_run?: boolean; override?: ApproveOverride },
): Promise<ApproveResponse> {
  try {
    return await apiRequest<ApproveResponse>(`/admin/candidates/${id}/approve`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  } catch (err) {
    wrapError(err);
  }
  throw new AdminApiError("Failed to approve candidate: unreachable state");
}

export async function rejectCandidate(id: number, reason: string): Promise<AdminCandidateItem> {
  try {
    return await apiRequest<AdminCandidateItem>(`/admin/candidates/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  } catch (err) {
    wrapError(err);
  }
  throw new AdminApiError("Failed to reject candidate: unreachable state");
}

export async function geocodeCandidate(id: number, address?: string): Promise<AdminCandidateItem> {
  try {
    return await apiRequest<AdminCandidateItem>(`/admin/candidates/${id}/geocode`, {
      method: "POST",
      body: address ? JSON.stringify({ address }) : undefined,
    });
  } catch (err) {
    wrapError(err);
  }
  throw new AdminApiError("Failed to geocode candidate: unreachable state");
}

export async function approveBulkCandidates(
  candidateIds: number[],
  options: { dry_run?: boolean; reason?: string } = {},
): Promise<BulkApproveResponse> {
  try {
    return await apiRequest<BulkApproveResponse>(`/admin/candidates/approve-bulk`, {
      method: "POST",
      body: JSON.stringify({ candidate_ids: candidateIds, ...options }),
    });
  } catch (err) {
    wrapError(err);
  }
  throw new AdminApiError("Failed to bulk approve candidates: unreachable state");
}

export async function rejectBulkCandidates(
  candidateIds: number[],
  options: { reason: string; dry_run?: boolean },
): Promise<BulkRejectResponse> {
  try {
    return await apiRequest<BulkRejectResponse>(`/admin/candidates/reject-bulk`, {
      method: "POST",
      body: JSON.stringify({ candidate_ids: candidateIds, ...options }),
    });
  } catch (err) {
    wrapError(err);
  }
  throw new AdminApiError("Failed to bulk reject candidates: unreachable state");
}

// --- Admin Gyms API ---

export interface ScrapeOfficialUrlResponse {
  gym_id: number;
  official_url: string;
  scraped: boolean;
  message: string;
}

export interface GenerateDescriptionResponse {
  gym_id: number;
  description: string;
  saved: boolean;
}

export async function scrapeGymOfficialUrl(
  gymId: number,
  officialUrl: string,
): Promise<ScrapeOfficialUrlResponse> {
  try {
    return await apiRequest<ScrapeOfficialUrlResponse>(`/admin/gyms/${gymId}/scrape-official-url`, {
      method: "POST",
      body: JSON.stringify({ official_url: officialUrl }),
    });
  } catch (err) {
    wrapError(err);
  }
  throw new AdminApiError("Failed to scrape official URL: unreachable state");
}

export async function generateGymDescription(
  gymId: number,
  options?: { max_length?: number },
): Promise<GenerateDescriptionResponse> {
  try {
    const body =
      options && typeof options.max_length === "number"
        ? JSON.stringify({ max_length: options.max_length })
        : undefined;
    return await apiRequest<GenerateDescriptionResponse>(
      `/admin/gyms/${gymId}/generate-description`,
      {
        method: "POST",
        body,
        timeoutMs: 60000,
      },
    );
  } catch (err) {
    wrapError(err);
  }
  throw new AdminApiError("Failed to generate description: unreachable state");
}

export async function scrapeCandidateOfficialUrl(
  candidateId: number,
  officialUrl?: string,
  dryRun?: boolean,
): Promise<AdminCandidateItem> {
  try {
    return await apiRequest<AdminCandidateItem>(`/admin/candidates/${candidateId}/scrape`, {
      method: "POST",
      body: JSON.stringify({
        official_url: officialUrl || undefined,
        dry_run: dryRun,
      }),
      timeoutMs: 60000,
    });
  } catch (err) {
    wrapError(err);
  }
  throw new AdminApiError("Failed to scrape candidate official URL: unreachable state");
}

export async function scrapeBulkCandidates(
  candidateIds: number[],
  options: { dry_run?: boolean } = {},
): Promise<BulkScrapeJobResponse> {
  try {
    return await apiRequest<BulkScrapeJobResponse>(`/admin/candidates/scrape-bulk`, {
      method: "POST",
      body: JSON.stringify({ candidate_ids: candidateIds, ...options }),
    });
  } catch (err) {
    wrapError(err);
  }
  throw new AdminApiError("Failed to bulk scrape candidates: unreachable state");
}

export async function getScrapeBulkStatus(jobId: string): Promise<BulkScrapeJobResponse> {
  try {
    return await apiRequest<BulkScrapeJobResponse>(`/admin/candidates/scrape-bulk/${jobId}`, {
      method: "GET",
    });
  } catch (err) {
    wrapError(err);
  }
  throw new AdminApiError("Failed to fetch bulk scrape status: unreachable state");
}

// --- URL Ingestion API ---

export interface IngestUrlItem {
  url: string;
  status: "success" | "failed";
  candidate_id: number | null;
  facility_name: string | null;
  error: string | null;
}

export interface IngestUrlsResponse {
  items: IngestUrlItem[];
  success_count: number;
  failure_count: number;
  dry_run: boolean;
}

export interface IngestUrlsPayload {
  urls: string[];
  pref_slug: string;
  city_slug: string;
  dry_run?: boolean;
}

export async function ingestUrls(payload: IngestUrlsPayload): Promise<IngestUrlsResponse> {
  try {
    return await apiRequest<IngestUrlsResponse>(`/admin/candidates/ingest-urls`, {
      method: "POST",
      body: JSON.stringify(payload),
      timeoutMs: 120000, // 2 minutes for batch operation
    });
  } catch (err) {
    wrapError(err);
  }
  throw new AdminApiError("Failed to ingest URLs: unreachable state");
}
