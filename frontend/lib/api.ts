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

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

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
