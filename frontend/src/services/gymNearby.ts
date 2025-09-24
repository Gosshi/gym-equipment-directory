import { apiRequest } from "@/lib/apiClient";
import type { GymNearbyResponse, NearbyGym } from "@/types/gym";

export interface FetchNearbyGymsParams {
  lat: number;
  lng: number;
  radiusKm: number;
  perPage?: number;
  pageToken?: string | null;
  signal?: AbortSignal;
}

type RawNearbyGym = {
  id: number;
  slug: string;
  name: string;
  pref?: string;
  city: string;
  latitude: number;
  longitude: number;
  distance_km: number;
  last_verified_at?: string | null;
};

type RawNearbyResponse = {
  items: RawNearbyGym[];
  total?: number;
  page?: number;
  page_size?: number;
  has_more?: boolean; // preferred flag name
  has_prev?: boolean;
  page_token?: string | null;
  // legacy or alternate names intentionally NOT typed (e.g., has_next) to surface if backend changes
};

const normalizeNearbyGym = (input: RawNearbyGym): NearbyGym => ({
  id: input.id,
  slug: input.slug,
  name: input.name,
  prefecture: input.pref ?? "",
  city: input.city,
  latitude: Number.parseFloat(String(input.latitude)),
  longitude: Number.parseFloat(String(input.longitude)),
  distanceKm: Number.parseFloat(String(input.distance_km)),
  lastVerifiedAt: input.last_verified_at ?? null,
});

export async function fetchNearbyGyms({
  lat,
  lng,
  radiusKm,
  perPage = 20,
  pageToken,
  signal,
}: FetchNearbyGymsParams): Promise<GymNearbyResponse> {
  const parsedToken =
    pageToken != null && pageToken !== "" ? Number.parseInt(pageToken, 10) : Number.NaN;
  const targetPage = Number.isFinite(parsedToken) && parsedToken > 0 ? parsedToken : 1;
  const query: Record<string, unknown> = {
    lat,
    lng,
    radius_km: radiusKm,
    page: targetPage,
    page_size: perPage,
  };

  const response = await apiRequest<RawNearbyResponse>("/gyms/nearby", {
    method: "GET",
    query,
    signal,
  });

  const currentPage = Number.isFinite(response.page) ? Number(response.page) : targetPage;
  const pageSize = Number.isFinite(response.page_size) ? Number(response.page_size) : perPage;
  const hasMore =
    typeof response.has_more === "boolean" ? response.has_more : response.items.length === pageSize;
  const hasPrev = response.has_prev ?? currentPage > 1;
  const total = typeof response.total === "number" ? response.total : response.items.length;
  const nextPageToken = hasMore ? String(currentPage + 1) : null;

  return {
    items: response.items.map(normalizeNearbyGym),
    total,
    page: currentPage,
    pageSize,
    hasMore: Boolean(hasMore),
    hasPrev,
    pageToken: nextPageToken,
  };
}
