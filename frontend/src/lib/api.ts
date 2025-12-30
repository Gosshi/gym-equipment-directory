import { apiRequest } from "@/lib/apiClient";
import type { GymSearchResponse, GymSummary } from "@/types/gym";

import {
  DEFAULT_DISTANCE_KM,
  DEFAULT_LIMIT,
  MAX_LIMIT,
  MIN_DISTANCE_KM,
  MAX_DISTANCE_KM,
  clampLatitude,
  clampLongitude,
  type SortOption,
  type SortOrder,
} from "./searchParams";

export type ApiSortKey = "freshness" | "richness" | "gym_name" | "created_at" | "score";

const API_SORT_KEYS: ApiSortKey[] = ["freshness", "richness", "gym_name", "created_at", "score"];

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

const clampRadiusKm = (value: number | null | undefined): number | undefined => {
  if (value == null) {
    return undefined;
  }
  if (!Number.isFinite(value)) {
    return undefined;
  }
  const rounded = Math.round(value);
  return Math.min(Math.max(rounded, MIN_DISTANCE_KM), MAX_DISTANCE_KM);
};

export interface FetchGymsParams {
  q?: string;
  pref?: string | null;
  city?: string | null;
  cats?: string[];
  conditions?: string[];
  sort?: SortOption | ApiSortKey | null;
  order?: SortOrder | null;
  page?: number;
  limit?: number;
  pageToken?: string | null;
  lat?: number | null;
  lng?: number | null;
  radiusKm?: number | null;
  min_lat?: number | null;
  max_lat?: number | null;
  min_lng?: number | null;
  max_lng?: number | null;
  /** @deprecated Use radiusKm instead. */
  distance?: number | null;
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
  latitude?: number | null;
  longitude?: number | null;
  tags?: string[];
  category?: string | null;
  categories?: string[];
};

type RawSearchGymsResponse =
  | RawGymSummary[]
  | {
      items: RawGymSummary[];
      total?: number;
      page?: number;
      page_size?: number;
      per_page?: number;
      has_more?: boolean;
      has_next?: boolean;
      has_prev?: boolean;
      page_token?: string | null;
    };

const normalizeEquipments = (source: unknown): string[] | undefined => {
  if (!source) {
    return undefined;
  }

  const values = Array.isArray(source) ? source : [source];

  const normalized = values
    .map(item => {
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
    latitude: input.latitude,
    longitude: input.longitude,
    tags: input.tags,
    lastVerifiedAt: input.last_verified_at ?? undefined,
    category: input.category ?? undefined,
    categories: input.categories ?? undefined,
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
      // TODO: distance sort is not yet supported by the search API; omit the key so the
      // backend falls back to its default order instead of returning 422.
      return undefined;
    case "name":
      return "gym_name";
    case "rating":
      return "score";
    case "reviews":
      // TODO: API does not expose review-count sorting; use richness as the closest match.
      return "richness";
    default:
      return undefined;
  }
};

const normalizeCats = (values: string[] | undefined): string[] | undefined => {
  if (!values) {
    return undefined;
  }
  const sanitized = values.map(value => value.trim()).filter(Boolean);
  if (sanitized.length === 0) {
    return undefined;
  }
  return Array.from(new Set(sanitized));
};

export const buildGymSearchQuery = (params: FetchGymsParams = {}) => {
  const page = clampPage(params.page);
  const limit = clampLimit(params.limit);
  const cats = normalizeCats(params.cats);
  const conditions = normalizeCats(params.conditions);
  const sort = sortOptionToApiSort(params.sort ?? undefined);
  const order = params.order && typeof params.order === "string" ? params.order : undefined;
  const latInput =
    typeof params.lat === "number" && Number.isFinite(params.lat) ? params.lat : undefined;
  const lngInput =
    typeof params.lng === "number" && Number.isFinite(params.lng) ? params.lng : undefined;
  const hasLocation = latInput !== undefined && lngInput !== undefined;
  const lat = hasLocation ? clampLatitude(latInput!) : undefined;
  const lng = hasLocation ? clampLongitude(lngInput!) : undefined;
  const radiusKm = hasLocation ? clampRadiusKm(params.radiusKm ?? params.distance) : undefined;
  const minLat =
    params.min_lat != null && Number.isFinite(params.min_lat) ? params.min_lat : undefined;
  const maxLat =
    params.max_lat != null && Number.isFinite(params.max_lat) ? params.max_lat : undefined;
  const minLng =
    params.min_lng != null && Number.isFinite(params.min_lng) ? params.min_lng : undefined;
  const maxLng =
    params.max_lng != null && Number.isFinite(params.max_lng) ? params.max_lng : undefined;

  return {
    q: params.q?.trim() || undefined,
    pref: params.pref?.trim() || undefined,
    city: params.city?.trim() || undefined,
    equipments: cats?.join(","),
    conditions: conditions?.join(","),
    sort,
    ...(order ? { order } : {}),
    page,
    page_size: limit,
    per_page: limit,
    page_token: params.pageToken ?? undefined,
    ...(hasLocation && lat !== undefined && lng !== undefined
      ? {
          lat,
          lng,
          ...(radiusKm !== undefined ? { radius_km: radiusKm } : {}),
        }
      : {}),
    ...(minLat != null ? { min_lat: minLat } : {}),
    ...(maxLat != null ? { max_lat: maxLat } : {}),
    ...(minLng != null ? { min_lng: minLng } : {}),
    ...(maxLng != null ? { max_lng: maxLng } : {}),
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

  if (Array.isArray(response)) {
    const page = fallbackPage;
    const perPage = fallbackPerPage;
    const items = response.map(normalizeGymSummary);
    const hasMore = perPage > 0 ? items.length === perPage : false;
    return {
      items,
      meta: {
        total: items.length,
        page,
        perPage,
        hasNext: hasMore,
        hasPrev: page > 1,
        hasMore,
        pageToken: null,
      },
    };
  }

  const rawItems = response.items ?? [];
  const page = clampPage(response.page ?? fallbackPage ?? query.page);
  const pageSizeRaw = response.page_size ?? response.per_page ?? fallbackPerPage ?? query.per_page;
  const perPage = clampLimit(pageSizeRaw);
  const hasMoreFlag =
    response.has_more ?? response.has_next ?? (perPage > 0 && rawItems.length === perPage);
  const hasPrev = response.has_prev ?? page > 1;
  const total = typeof response.total === "number" ? response.total : null;

  return {
    items: rawItems.map(normalizeGymSummary),
    meta: {
      total,
      page,
      perPage,
      hasNext: Boolean(hasMoreFlag),
      hasPrev,
      hasMore: Boolean(hasMoreFlag),
      pageToken: response.page_token ?? null,
    },
  };
}

// Favorites APIs
export type FavoriteItem = {
  gym_id: number;
  slug: string;
  name: string;
  pref?: string | null;
  city?: string | null;
  last_verified_at?: string | null;
};

export async function listFavorites(device_id: string): Promise<FavoriteItem[]> {
  return apiRequest<FavoriteItem[]>("/me/favorites", {
    method: "GET",
    query: { device_id },
  });
}

export async function addFavorite(device_id: string, gym_id: number): Promise<void> {
  await apiRequest("/me/favorites", {
    method: "POST",
    body: JSON.stringify({ device_id, gym_id }),
  });
}

export async function removeFavorite(device_id: string, gym_id: number): Promise<void> {
  await apiRequest(`/me/favorites/${gym_id}`, {
    method: "DELETE",
    query: { device_id },
  });
}
