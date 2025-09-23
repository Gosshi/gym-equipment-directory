import { apiRequest } from "@/lib/apiClient";
import type { GymSearchResponse, GymSummary } from "@/types/gym";

import {
  DEFAULT_LIMIT,
  MAX_LIMIT,
  type SortOption,
} from "./searchParams";

export type ApiSortKey = "freshness" | "richness" | "gym_name" | "created_at" | "score";

const API_SORT_KEYS: ApiSortKey[] = [
  "freshness",
  "richness",
  "gym_name",
  "created_at",
  "score",
];

const API_SORT_KEY_SET = new Set<ApiSortKey>(API_SORT_KEYS);

const isApiSortKey = (value: string): value is ApiSortKey =>
  API_SORT_KEY_SET.has(value as ApiSortKey);

const clampPage = (value: number | undefined): number => {
  if (!Number.isFinite(value) || (value ?? 0) <= 0) {
    return 1;
  }
  return Math.trunc(value!);
};

const clampLimit = (value: number | undefined): number => {
  if (!Number.isFinite(value)) {
    return DEFAULT_LIMIT;
  }
  const parsed = Math.trunc(value!);
  if (parsed <= 0) {
    return DEFAULT_LIMIT;
  }
  return Math.min(parsed, MAX_LIMIT);
};

export interface FetchGymsParams {
  q?: string;
  pref?: string | null;
  city?: string | null;
  cats?: string[];
  sort?: SortOption | ApiSortKey | null;
  page?: number;
  limit?: number;
  pageToken?: string | null;
}

export type RawGymSummary = {
  id: number;
  slug: string;
  name: string;
  pref?: string;
  prefecture?: string;
  city: string;
  address?: string | null;
  full_address?: string | null;
  thumbnail_url?: string | null;
  thumbnailUrl?: string | null;
  equipments?: unknown;
  main_equipments?: unknown;
  score?: number | null;
  richness_score?: number | null;
  freshness_score?: number | null;
  last_verified_at?: string | null;
};

type RawSearchGymsResponse = {
  items: RawGymSummary[];
  total: number;
  page?: number;
  per_page?: number;
  has_next: boolean;
  has_prev?: boolean;
  page_token?: string | null;
};

const normalizeEquipments = (source: unknown): string[] | undefined => {
  if (!source) {
    return undefined;
  }

  const values = Array.isArray(source) ? source : [source];

  const normalized = values
    .map((item) => {
      if (item == null) {
        return undefined;
      }
      if (typeof item === "string") {
        return item;
      }
      if (typeof item === "object") {
        const record = item as Record<string, unknown>;
        const name = record.name as string | undefined;
        const label = name || (record.slug as string | undefined);
        return label;
      }
      return String(item);
    })
    .filter((value): value is string => Boolean(value));

  return normalized.length > 0 ? normalized : undefined;
};

export const normalizeGymSummary = (input: RawGymSummary): GymSummary => {
  const equipments =
    normalizeEquipments(input.equipments) ?? normalizeEquipments(input.main_equipments);

  return {
    id: input.id,
    slug: input.slug,
    name: input.name,
    city: input.city,
    prefecture: input.pref ?? input.prefecture ?? "",
    address: input.address ?? input.full_address ?? undefined,
    thumbnailUrl: input.thumbnail_url ?? input.thumbnailUrl ?? null,
    equipments,
    score: input.score ?? input.richness_score ?? undefined,
    lastVerifiedAt: input.last_verified_at ?? undefined,
  };
};

const sortOptionToApiSort = (sort: SortOption | ApiSortKey | null | undefined) => {
  if (!sort) {
    return undefined;
  }
  if (isApiSortKey(sort)) {
    return sort;
  }
  switch (sort) {
    case "distance":
      return undefined;
    case "fresh":
      return "freshness";
    case "newest":
      return "created_at";
    case "popular":
      return "score";
    default:
      return undefined;
  }
};

const normalizeCats = (values: string[] | undefined): string[] | undefined => {
  if (!values) {
    return undefined;
  }
  const sanitized = values
    .map((value) => value.trim())
    .filter(Boolean);
  if (sanitized.length === 0) {
    return undefined;
  }
  return Array.from(new Set(sanitized));
};

export const buildGymSearchQuery = (params: FetchGymsParams = {}) => {
  const page = clampPage(params.page);
  const limit = clampLimit(params.limit);
  const cats = normalizeCats(params.cats);
  const sort = sortOptionToApiSort(params.sort ?? undefined);

  return {
    q: params.q?.trim() || undefined,
    pref: params.pref?.trim() || undefined,
    city: params.city?.trim() || undefined,
    equipments: cats?.join(","),
    sort,
    page,
    per_page: limit,
    page_token: params.pageToken ?? undefined,
  };
};

export async function fetchGyms(
  params: FetchGymsParams = {},
  options: { signal?: AbortSignal } = {},
): Promise<GymSearchResponse> {
  const query = buildGymSearchQuery(params);
  const fallbackPage = clampPage(params.page);
  const fallbackPerPage = clampLimit(params.limit);

  const response = await apiRequest<RawSearchGymsResponse>("/gyms/search", {
    method: "GET",
    query,
    signal: options.signal,
  });

  const page = clampPage(response.page ?? fallbackPage ?? query.page);
  const perPage = clampLimit(response.per_page ?? fallbackPerPage ?? query.per_page);
  const hasNext = Boolean(response.has_next);
  const hasPrev = response.has_prev ?? page > 1;

  return {
    items: response.items.map(normalizeGymSummary),
    meta: {
      total: response.total,
      page,
      perPage,
      hasNext,
      hasPrev,
      pageToken: response.page_token ?? null,
    },
  };
}
