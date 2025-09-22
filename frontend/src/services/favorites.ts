import { apiRequest } from "@/lib/apiClient";

export async function addFavorite(gymId: number, options: { signal?: AbortSignal } = {}) {
  await apiRequest(`/me/favorites/${gymId}`, {
    method: "POST",
    body: JSON.stringify({}),
    signal: options.signal,
  });
}

export async function removeFavorite(gymId: number, options: { signal?: AbortSignal } = {}) {
  await apiRequest(`/me/favorites/${gymId}`, {
    method: "DELETE",
    signal: options.signal,
  });
}
