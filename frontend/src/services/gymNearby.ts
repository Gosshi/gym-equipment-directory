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
  has_next: boolean;
  page_token?: string | null;
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
  const query: Record<string, unknown> = {
    lat,
    lng,
    radius_km: radiusKm,
    per_page: perPage,
    page_token: pageToken ?? undefined,
  };

  const response = await apiRequest<RawNearbyResponse>("/gyms/nearby", {
    method: "GET",
    query,
    signal,
  });

  return {
    items: response.items.map(normalizeNearbyGym),
    hasNext: response.has_next,
    pageToken: response.page_token ?? null,
  };
}
