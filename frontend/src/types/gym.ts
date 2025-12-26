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

  // Category and category-specific fields
  category?: string | null;
  // Pool
  poolLanes?: number | null;
  poolLengthM?: number | null;
  poolHeated?: boolean | null;
  // Court
  courtType?: string | null;
  courtCount?: number | null;
  courtSurface?: string | null;
  courtLighting?: boolean | null;
  // Hall
  hallSports?: string[];
  hallAreaSqm?: number | null;
  // Field
  fieldType?: string | null;
  fieldCount?: number | null;
  fieldLighting?: boolean | null;
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
