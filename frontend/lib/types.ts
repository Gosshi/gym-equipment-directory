export type CandidateStatus = "new" | "reviewing" | "approved" | "rejected";

export type JsonRecord = Record<string, unknown>;

export interface AdminSourceRef {
  id: number;
  title?: string | null;
  url?: string | null;
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

export interface AdminCandidateItem {
  id: number;
  status: CandidateStatus;
  name_raw: string;
  address_raw?: string | null;
  pref_slug?: string | null;
  city_slug?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  parsed_json?: JsonRecord | null;
  official_url?: string | null;
  source: AdminSourceRef;
  fetched_at?: string | null;
  created_at: string;
  updated_at: string;
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
  status?: CandidateStatus | "" | null;
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

export interface AdminCandidateCreatePayload {
  name_raw: string;
  address_raw?: string | null;
  pref_slug: string;
  city_slug: string;
  latitude?: number | null;
  longitude?: number | null;
  parsed_json?: JsonRecord | null;
  official_url?: string | null;
}

export type EquipmentAvailability = "present" | "absent" | "unknown";

export interface EquipmentAssign {
  slug: string;
  availability?: EquipmentAvailability;
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

export interface ApproveRequest {
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

export type ApproveResponse = ApprovePreviewResponse | ApproveResultResponse;

export interface RejectRequest {
  reason: string;
}
