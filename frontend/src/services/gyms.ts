import { apiRequest } from "@/lib/apiClient";
import { encodeOnce } from "@/lib/url";
import {
  fetchGyms as fetchGymsApi,
  normalizeGymSummary,
  type ApiSortKey,
  type FetchGymsParams,
  type RawGymSummary,
} from "@/lib/api";
import type { SortOption, SortOrder } from "@/lib/searchParams";
import type { GymDetail, GymEquipmentDetail, GymSearchResponse } from "@/types/gym";

type RawGymDetail = RawGymSummary & {
  description?: string | null;
  phone?: string | null;
  website?: string | null;
  website_url?: string | null;
  opening_hours?: string | null;
  openingHours?: string | null;
  fees?: string | null;
  price?: string | null;
  main_image_url?: string | null;
  hero_image_url?: string | null;
  images?: unknown;
  image_urls?: unknown;
  gallery?: unknown;
  equipment_details?: unknown;
  equipmentDetails?: unknown;
  main_equipment_details?: unknown;
  mainEquipmentDetails?: unknown;
  lat?: number | string | null;
  lng?: number | string | null;
  latitude?: number | string | null;
  longitude?: number | string | null;
  location?: unknown;
  // Category-specific fields
  category?: string | null;
  pool_lanes?: number | null;
  pool_length_m?: number | null;
  pool_heated?: boolean | null;
  court_type?: string | null;
  court_count?: number | null;
  court_surface?: string | null;
  court_lighting?: boolean | null;
  hall_sports?: string[] | null;
  hall_area_sqm?: number | null;
  field_type?: string | null;
  field_count?: number | null;
  field_lighting?: boolean | null;
  // Archery fields
  archery_type?: string | null;
  archery_rooms?: number | null;
  // Categories and official URL
  categories?: string[] | null;
  official_url?: string | null;
};

export interface SearchGymsParams {
  q?: string;
  prefecture?: string | null;
  city?: string | null;
  categories?: string[];
  conditions?: string[];
  equipments?: string[];
  sort?: SortOption | ApiSortKey | null;
  order?: SortOrder | null;
  page?: number;
  perPage?: number;
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

const normalizeImageUrls = (source: unknown): string[] | undefined => {
  if (!source) {
    return undefined;
  }

  const values = Array.isArray(source) ? source : [source];

  const normalized = values
    .map(item => {
      if (!item) {
        return undefined;
      }

      if (typeof item === "string") {
        return item;
      }

      if (typeof item === "object") {
        const record = item as Record<string, unknown>;
        const url = record.url ?? record.src ?? record.image_url ?? record.thumbnail_url;
        return typeof url === "string" ? url : undefined;
      }

      return undefined;
    })
    .filter((value): value is string => Boolean(value));

  return normalized.length > 0 ? normalized : undefined;
};

const sanitizeText = (value: unknown): string | undefined => {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
};

const normalizeEquipmentDetails = (source: unknown): GymEquipmentDetail[] | undefined => {
  if (!source) return undefined;
  const values = Array.isArray(source) ? source : [source];
  const result: GymEquipmentDetail[] = [];
  for (const item of values) {
    if (item == null) continue;
    if (typeof item === "string") {
      const name = sanitizeText(item);
      if (!name) continue;
      result.push({ name });
      continue;
    }
    if (typeof item === "object") {
      const record = item as Record<string, unknown>;
      const name =
        sanitizeText(record.name) ??
        sanitizeText(record.label) ??
        sanitizeText(record.title) ??
        sanitizeText(record.slug) ??
        sanitizeText(record.value);
      if (!name) continue;
      const category =
        sanitizeText(record.category) ??
        sanitizeText(record.type) ??
        sanitizeText(record.category_name) ??
        sanitizeText(record.group) ??
        null;
      const description =
        sanitizeText(record.description) ??
        sanitizeText(record.note) ??
        sanitizeText(record.notes) ??
        sanitizeText(record.memo) ??
        sanitizeText(record.detail) ??
        sanitizeText(record.details) ??
        null;
      const idRaw = record.id;
      const identifier =
        typeof idRaw === "string" || typeof idRaw === "number"
          ? idRaw
          : (sanitizeText(record.key) ?? undefined);
      result.push({ id: identifier, name, category, description });
      continue;
    }
    const coerced = String(item).trim();
    if (coerced) result.push({ name: coerced });
  }
  return result.length > 0 ? result : undefined;
};

const toFiniteNumber = (value: unknown): number | null => {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    const parsed = Number.parseFloat(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const extractCoordinates = (
  input: RawGymDetail,
): {
  latitude: number | null;
  longitude: number | null;
} => {
  const location =
    input.location && typeof input.location === "object"
      ? (input.location as Record<string, unknown>)
      : undefined;

  const latitude =
    toFiniteNumber(input.latitude) ??
    toFiniteNumber(input.lat) ??
    (location ? (toFiniteNumber(location.latitude) ?? toFiniteNumber(location.lat)) : null);

  const longitude =
    toFiniteNumber(input.longitude) ??
    toFiniteNumber(input.lng) ??
    (location ? (toFiniteNumber(location.longitude) ?? toFiniteNumber(location.lng)) : null);

  return { latitude, longitude };
};

const normalizeGymDetail = (input: RawGymDetail): GymDetail => {
  const summary = normalizeGymSummary(input);
  const images =
    normalizeImageUrls(input.images) ??
    normalizeImageUrls(input.image_urls) ??
    normalizeImageUrls(input.gallery);

  const thumbnailUrl =
    input.thumbnail_url ??
    input.thumbnailUrl ??
    input.main_image_url ??
    input.hero_image_url ??
    null;

  const equipmentDetails =
    normalizeEquipmentDetails(input.equipment_details) ??
    normalizeEquipmentDetails(input.equipmentDetails) ??
    normalizeEquipmentDetails(input.main_equipment_details) ??
    normalizeEquipmentDetails(input.mainEquipmentDetails) ??
    normalizeEquipmentDetails(input.equipments);

  const { latitude, longitude } = extractCoordinates(input);

  return {
    id: summary.id,
    slug: summary.slug,
    name: summary.name,
    prefecture: summary.prefecture,
    city: summary.city,
    address: summary.address,
    latitude,
    longitude,
    equipments: summary.equipments ?? [],
    equipmentDetails,
    thumbnailUrl,
    images,
    openingHours: input.openingHours ?? input.opening_hours ?? null,
    fees: input.fees ?? input.price ?? null,
    phone: input.phone ?? null,
    website: input.official_url ?? input.website ?? input.website_url ?? null,
    description: input.description ?? null,
    // Category-specific fields
    category: input.category ?? null,
    poolLanes: input.pool_lanes ?? null,
    poolLengthM: input.pool_length_m ?? null,
    poolHeated: input.pool_heated ?? null,
    courtType: input.court_type ?? null,
    courtCount: input.court_count ?? null,
    courtSurface: input.court_surface ?? null,
    courtLighting: input.court_lighting ?? null,
    hallSports: input.hall_sports ?? [],
    hallAreaSqm: input.hall_area_sqm ?? null,
    fieldType: input.field_type ?? null,
    fieldCount: input.field_count ?? null,
    fieldLighting: input.field_lighting ?? null,
    // Archery fields
    archeryType: input.archery_type ?? null,
    archeryRooms: input.archery_rooms ?? null,
    // Categories and official URL
    categories: input.categories ?? [],
    officialUrl: input.official_url ?? null,
  };
};

export async function searchGyms(
  params: SearchGymsParams = {},
  options: { signal?: AbortSignal } = {},
): Promise<GymSearchResponse> {
  const hasLocation =
    typeof params.lat === "number" &&
    Number.isFinite(params.lat) &&
    typeof params.lng === "number" &&
    Number.isFinite(params.lng);

  const request: FetchGymsParams = {
    q: params.q,
    pref: params.prefecture ?? undefined,
    city: params.city ?? undefined,
    cats: params.categories ?? params.equipments,
    conditions: params.conditions,
    sort: params.sort ?? undefined,
    order: params.order ?? undefined,
    page: params.page,
    limit: params.limit ?? params.perPage,
    pageToken: params.pageToken ?? undefined,
    ...(hasLocation
      ? {
          lat: params.lat!,
          lng: params.lng!,
          radiusKm: params.radiusKm ?? params.distance ?? undefined,
        }
      : {}),
    min_lat: params.min_lat,
    max_lat: params.max_lat,
    min_lng: params.min_lng,
    max_lng: params.max_lng,
  };

  return fetchGymsApi(request, options);
}

export async function getGymBySlug(
  slug: string,
  options: { signal?: AbortSignal } = {},
): Promise<GymDetail> {
  const response = await apiRequest<RawGymDetail>(`/gyms/${encodeOnce(slug)}`, {
    method: "GET",
    signal: options.signal,
  });

  return normalizeGymDetail(response);
}
