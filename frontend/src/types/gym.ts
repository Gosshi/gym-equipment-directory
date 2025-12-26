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
  latitude?: number | null;
  longitude?: number | null;
  tags?: string[];
  category?: string | null;
}

export interface GymSearchMeta {
  total: number | null;
  page: number;
  perPage: number;
  hasNext: boolean;
  hasPrev: boolean;
  hasMore: boolean;
  pageToken?: string | null;
}

export interface GymSearchResponse {
  items: GymSummary[];
  meta: GymSearchMeta;
}

export interface GymEquipmentDetail {
  id?: string | number;
  name: string;
  category?: string | null;
  description?: string | null;
}

export interface GymDetail {
  id: number;
  slug: string;
  name: string;
  prefecture: string;
  city: string;
  address?: string;
  latitude?: number | null;
  longitude?: number | null;
  equipments: string[];
  equipmentDetails?: GymEquipmentDetail[];
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
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
  hasPrev: boolean;
  pageToken: string | null;
}
