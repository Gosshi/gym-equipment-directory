import { apiRequest } from "@/lib/apiClient";
import type { Favorite } from "@/types/favorite";

interface RawFavoriteItem {
  gym_id: number;
  slug: string;
  name: string;
  pref?: string | null;
  city?: string | null;
  address?: string | null;
  thumbnail_url?: string | null;
  thumbnailUrl?: string | null;
  last_verified_at?: string | null;
  created_at?: string | null;
}

const normalizeFavorite = (input: RawFavoriteItem): Favorite => ({
  createdAt: input.created_at ?? null,
  gym: {
    id: input.gym_id,
    slug: input.slug,
    name: input.name,
    prefecture: input.pref ?? "",
    city: input.city ?? "",
    address: input.address ?? undefined,
    thumbnailUrl: input.thumbnailUrl ?? input.thumbnail_url ?? null,
    lastVerifiedAt: input.last_verified_at ?? null,
  },
});

export async function listFavorites(
  deviceId: string,
  options: { signal?: AbortSignal } = {},
): Promise<Favorite[]> {
  const response = await apiRequest<RawFavoriteItem[]>("/me/favorites", {
    method: "GET",
    query: { device_id: deviceId },
    signal: options.signal,
  });

  return response.map(normalizeFavorite);
}

export async function addFavorite(
  gymId: number,
  deviceId: string,
  options: { signal?: AbortSignal } = {},
): Promise<void> {
  await apiRequest("/me/favorites", {
    method: "POST",
    body: JSON.stringify({
      device_id: deviceId,
      gym_id: gymId,
    }),
    signal: options.signal,
  });
}

export async function removeFavorite(
  gymId: number,
  deviceId: string,
  options: { signal?: AbortSignal } = {},
): Promise<void> {
  await apiRequest(`/me/favorites/${gymId}`, {
    method: "DELETE",
    query: { device_id: deviceId },
    signal: options.signal,
  });
}
