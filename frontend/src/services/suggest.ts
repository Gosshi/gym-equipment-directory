import { apiRequest } from "@/lib/apiClient";

export interface GymSuggestItem {
  slug: string;
  name: string;
  pref?: string | null;
  city?: string | null;
}

export async function suggestGyms(
  q: string,
  options: { pref?: string; limit?: number; signal?: AbortSignal } = {},
): Promise<GymSuggestItem[]> {
  const trimmed = q.trim();
  if (!trimmed) {
    return [];
  }

  const params: Record<string, unknown> = { q: trimmed };
  if (options.pref?.trim()) {
    params.pref = options.pref.trim();
  }
  if (typeof options.limit === "number" && Number.isFinite(options.limit)) {
    const normalized = Math.max(Math.min(Math.trunc(options.limit), 20), 1);
    params.limit = normalized;
  }

  return apiRequest<GymSuggestItem[]>("/suggest/gyms", {
    method: "GET",
    query: params,
    signal: options.signal,
  });
}
