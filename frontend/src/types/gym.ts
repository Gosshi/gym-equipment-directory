export interface GymSummary {
  id: number;
  slug: string;
  name: string;
  city: string;
  prefecture: string;
  address?: string;
  equipments?: string[];
  thumbnailUrl?: string | null;
  score?: number;
  lastVerifiedAt?: string | null;
}

export interface GymSearchMeta {
  total: number;
  hasNext: boolean;
  pageToken?: string | null;
}

export interface GymSearchResponse {
  items: GymSummary[];
  meta: GymSearchMeta;
}
