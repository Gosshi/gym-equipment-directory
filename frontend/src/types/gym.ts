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
  categories?: string[];
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

export interface PoolItem {
  lanes?: number | null;
  lengthM?: number | null;
  heated?: boolean | null;
}

export interface CourtItem {
  courtType?: string | null;
  courts?: number | null;
  surface?: string | null;
  lighting?: boolean | null;
}

export interface FieldItem {
  fieldType?: string | null;
  fields?: number | null;
  lighting?: boolean | null;
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
  fees?: string | null;
  phone?: string | null;
  website?: string | null;
  description?: string | null;
  tags?: string[];

  // Category and category-specific fields
  category?: string | null;
  categories?: string[];
  // Pool
  poolLanes?: number | null;
  poolLengthM?: number | null;
  poolHeated?: boolean | null;
  pools?: PoolItem[];
  // Court
  courtType?: string | null;
  courtCount?: number | null;
  courtSurface?: string | null;
  courtLighting?: boolean | null;
  courts?: CourtItem[];
  // Hall
  hallSports?: string[];
  hallAreaSqm?: number | null;
  // Field
  fieldType?: string | null;
  fieldCount?: number | null;
  fieldLighting?: boolean | null;
  fields?: FieldItem[];
  // Archery
  archeryType?: string | null;
  archeryRooms?: number | null;
  // Official URL
  officialUrl?: string | null;
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
