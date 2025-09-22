import { apiRequest } from "@/lib/apiClient";
import type { GymSearchResponse, GymSummary } from "@/types/gym";

export interface SearchGymsParams {
  q?: string;
  prefecture?: string;
  city?: string;
  equipments?: string[];
  equipmentMatch?: "all" | "any";
  sort?: "freshness" | "richness" | "gym_name" | "created_at" | "score";
  page?: number;
  perPage?: number;
  pageToken?: string | null;
}

type RawGymSummary = {
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
};

type RawSearchGymsResponse = {
  items: RawGymSummary[];
  total: number;
  has_next: boolean;
  page_token?: string | null;
};

const normalizeEquipments = (source: unknown): string[] | undefined => {
  if (!source) {
    return undefined;
  }

  const values = Array.isArray(source) ? source : [source];

  const normalized = values
    .map((item) => {
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

const normalizeGymSummary = (input: RawGymSummary): GymSummary => {
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
    lastVerifiedAt: input.last_verified_at ?? undefined,
  };
};

export async function searchGyms(
  params: SearchGymsParams = {},
  options: { signal?: AbortSignal } = {},
): Promise<GymSearchResponse> {
  const query: Record<string, unknown> = {
    q: params.q,
    pref: params.prefecture,
    city: params.city,
    equipments: params.equipments?.join(","),
    equipment_match: params.equipmentMatch,
    sort: params.sort,
    page: params.page,
    per_page: params.perPage,
    page_token: params.pageToken ?? undefined,
  };

  const response = await apiRequest<RawSearchGymsResponse>("/gyms/search", {
    method: "GET",
    query,
    signal: options.signal,
  });

  return {
    items: response.items.map(normalizeGymSummary),
    meta: {
      total: response.total,
      hasNext: response.has_next,
      pageToken: response.page_token ?? null,
    },
  };
}
