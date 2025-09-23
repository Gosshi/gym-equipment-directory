import { apiRequest } from "@/lib/apiClient";
import {
  fetchGyms as fetchGymsApi,
  normalizeGymSummary,
  type ApiSortKey,
  type FetchGymsParams,
  type RawGymSummary,
} from "@/lib/api";
import type { SortOption } from "@/lib/searchParams";
import type { GymDetail, GymEquipmentDetail, GymSearchResponse } from "@/types/gym";

type RawGymDetail = RawGymSummary & {
  description?: string | null;
  phone?: string | null;
  website?: string | null;
  website_url?: string | null;
  opening_hours?: string | null;
  openingHours?: string | null;
  main_image_url?: string | null;
  hero_image_url?: string | null;
  images?: unknown;
  image_urls?: unknown;
  gallery?: unknown;
  equipment_details?: unknown;
  equipmentDetails?: unknown;
  main_equipment_details?: unknown;
  mainEquipmentDetails?: unknown;
};

export interface SearchGymsParams {
  q?: string;
  prefecture?: string | null;
  city?: string | null;
  categories?: string[];
  equipments?: string[];
  sort?: SortOption | ApiSortKey | null;
  page?: number;
  perPage?: number;
  limit?: number;
  pageToken?: string | null;
  lat?: number | null;
  lng?: number | null;
  distanceKm?: number | null;
}

const normalizeImageUrls = (source: unknown): string[] | undefined => {
  if (!source) {
    return undefined;
  }

  const values = Array.isArray(source) ? source : [source];

  const normalized = values
    .map((item) => {
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
        sanitizeText(record.group) ?? null;
      const description =
        sanitizeText(record.description) ??
        sanitizeText(record.note) ??
        sanitizeText(record.notes) ??
        sanitizeText(record.memo) ??
        sanitizeText(record.detail) ??
        sanitizeText(record.details) ?? null;
      const idRaw = record.id;
      const identifier =
        typeof idRaw === "string" || typeof idRaw === "number"
          ? idRaw
          : sanitizeText(record.key) ?? undefined;
      result.push({ id: identifier, name, category, description });
      continue;
    }
    const coerced = String(item).trim();
    if (coerced) result.push({ name: coerced });
  }
  return result.length > 0 ? result : undefined;
};

const normalizeGymDetail = (input: RawGymDetail): GymDetail => {
  const summary = normalizeGymSummary(input);
  const images =
    normalizeImageUrls(input.images) ??
    normalizeImageUrls(input.image_urls) ??
    normalizeImageUrls(input.gallery);

  const thumbnailUrl =
    input.thumbnail_url ?? input.thumbnailUrl ?? input.main_image_url ?? input.hero_image_url ?? null;

  const equipmentDetails =
    normalizeEquipmentDetails(input.equipment_details) ??
    normalizeEquipmentDetails(input.equipmentDetails) ??
    normalizeEquipmentDetails(input.main_equipment_details) ??
    normalizeEquipmentDetails(input.mainEquipmentDetails) ??
    normalizeEquipmentDetails(input.equipments);

  return {
    id: summary.id,
    slug: summary.slug,
    name: summary.name,
    prefecture: summary.prefecture,
    city: summary.city,
    address: summary.address,
    equipments: summary.equipments ?? [],
    equipmentDetails,
    thumbnailUrl,
    images,
    openingHours: input.openingHours ?? input.opening_hours ?? null,
    phone: input.phone ?? null,
    website: input.website ?? input.website_url ?? null,
    description: input.description ?? null,
  };
};

export async function searchGyms(
  params: SearchGymsParams = {},
  options: { signal?: AbortSignal } = {},
): Promise<GymSearchResponse> {
  const request: FetchGymsParams = {
    q: params.q,
    pref: params.prefecture ?? undefined,
    city: params.city ?? undefined,
    cats: params.categories ?? params.equipments,
    sort: params.sort ?? undefined,
    page: params.page,
    limit: params.limit ?? params.perPage,
    pageToken: params.pageToken ?? undefined,
    lat: params.lat ?? undefined,
    lng: params.lng ?? undefined,
    distanceKm: params.distanceKm ?? undefined,
  };

  return fetchGymsApi(request, options);
}

export async function getGymBySlug(
  slug: string,
  options: { signal?: AbortSignal } = {},
): Promise<GymDetail> {
  const response = await apiRequest<RawGymDetail>(`/gyms/${slug}`, {
    method: "GET",
    signal: options.signal,
  });

  return normalizeGymDetail(response);
}
