export type SearchParams = {
  pref?: string;
  city?: string;
  equipments?: string[]; // array of equipment slugs/ids
  sort?: string; // e.g. relevance | name_asc | name_desc
  per_page?: number;
  page_token?: string;
};

export type GymSummary = {
  slug: string;
  name?: string;
  address?: string;
  equipments?: string[] | { name?: string; slug?: string }[];
  [k: string]: unknown;
};

export type GymDetail = GymSummary & {
  description?: string;
};

export type SearchResponse = {
  items?: GymSummary[];
  gyms?: GymSummary[]; // fallback if API uses a different key
  total?: number;
  has_next?: boolean;
  page_token?: string | null;
  [k: string]: unknown;
};

export type Equipment = { slug?: string; name?: string; id?: string | number };

// Default to Next.js proxy path to avoid cross-origin issues in the browser
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api";

function toQuery(params: Record<string, unknown>): string {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === "") return;
    if (Array.isArray(v)) {
      // join as comma for simple backend parsing
      if (v.length > 0) q.set(k, v.join(","));
    } else {
      q.set(k, String(v));
    }
  });
  const s = q.toString();
  return s ? `?${s}` : "";
}

async function fetchJson<T>(path: string, query?: Record<string, unknown>): Promise<T> {
  const url = `${API_BASE}${path}${toQuery(query ?? {})}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    if (typeof window !== "undefined") {
      // Help debugging by showing failing URL and response body in console
      // eslint-disable-next-line no-console
      console.error("API error", { url, status: res.status, body: text });
    }
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }
  return (await res.json()) as T;
}

export async function getEquipments(): Promise<Equipment[]> {
  return fetchJson<Equipment[]>("/equipments");
}

export async function searchGyms(params: SearchParams): Promise<SearchResponse> {
  return fetchJson<SearchResponse>("/gyms/search", params);
}

export async function getGymBySlug(slug: string): Promise<GymDetail> {
  return fetchJson<GymDetail>(`/gyms/${encodeURIComponent(slug)}`);
}

// Nearby gyms (by geolocation)
export type NearbyParams = {
  lat: number;
  lng: number;
  radius_km?: number;
  per_page?: number;
  page_token?: string | null;
};

export type NearbyItem = {
  id?: string | number;
  slug: string;
  name?: string;
  pref?: string;
  city?: string;
  distance_km?: number;
  last_verified_at?: string | null;
};

export type NearbyResponse = {
  items?: NearbyItem[];
  gyms?: NearbyItem[]; // some backends may use this key
  has_next?: boolean;
  page_token?: string | null;
};

export async function getNearbyGyms(params: NearbyParams): Promise<NearbyResponse> {
  return fetchJson<NearbyResponse>("/gyms/nearby", params as Record<string, unknown>);
}

// Suggest APIs
export type GymSuggestItem = { slug: string; name: string; pref?: string | null; city?: string | null };

export async function suggestEquipments(q: string, limit = 5): Promise<string[]> {
  return fetchJson<string[]>("/suggest/equipments", { q, limit });
}

export async function suggestGyms(q: string, pref?: string, limit = 10): Promise<GymSuggestItem[]> {
  const params: Record<string, unknown> = { q, limit };
  if (pref) params.pref = pref;
  return fetchJson<GymSuggestItem[]>("/suggest/gyms", params);
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
  return fetchJson<FavoriteItem[]>("/me/favorites", { device_id });
}

export async function addFavorite(device_id: string, gym_id: number): Promise<void> {
  const url = `${API_BASE}/me/favorites`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ device_id, gym_id }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}

export async function removeFavorite(device_id: string, gym_id: number): Promise<void> {
  const url = `${API_BASE}/me/favorites/${encodeURIComponent(String(gym_id))}?device_id=${encodeURIComponent(device_id)}`;
  const res = await fetch(url, { method: "DELETE" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}
