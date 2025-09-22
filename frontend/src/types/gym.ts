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

export interface GymDetail {
  id: number;
  slug: string;
  name: string;
  prefecture: string;
  city: string;
  address?: string;
  equipments: string[];
  thumbnailUrl?: string | null;
  images?: string[];
  openingHours?: string | null;
  phone?: string | null;
  website?: string | null;
  description?: string | null;
}

export interface NearbyGym {
  id: number;
  slug: string;
  name: string;
  prefecture: string;
  city: string;
  latitude: number;
  longitude: number;
  distanceKm: number;
  lastVerifiedAt?: string | null;
}

export interface GymNearbyResponse {
  items: NearbyGym[];
  hasNext: boolean;
  pageToken: string | null;
}
