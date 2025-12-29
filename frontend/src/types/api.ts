export interface GymCategoryApiResponse {
  id?: string | number;
  slug?: string | null;
  name?: string | null;
  label?: string | null;
  title?: string | null;
}

export interface GymFacilityItemApiResponse {
  id?: string | number;
  name?: string | null;
  label?: string | null;
  title?: string | null;
  value?: string | null;
  description?: string | null;
  category?: string | null;
  type?: string | null;
}

export interface GymFacilityCategoryApiResponse {
  id?: string | number;
  category?: string | null;
  name?: string | null;
  label?: string | null;
  title?: string | null;
  group?: string | null;
  items?: unknown;
  equipments?: unknown;
  equipment_details?: unknown;
}

export interface GymEquipmentDetailApiResponse {
  id?: string | number;
  name?: string | null;
  label?: string | null;
  title?: string | null;
  category?: string | null;
  group?: string | null;
  type?: string | null;
  description?: string | null;
  items?: unknown;
}

export interface GymLocationApiResponse {
  lat?: number | null;
  lng?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  address?: string | null;
}

export interface GymDetailMetaApiResponse {
  redirect?: boolean | null;
}

export interface GymDetailGymApiResponse {
  id?: number | null;
  slug?: string | null;
  canonical_id?: string | null;
  name?: string | null;
  address?: string | null;
  prefecture?: string | null;
  parsed_json?: unknown;
}

export interface GymDetailApiResponse {
  requested_slug?: string | null;
  canonical_slug?: string | null;
  meta?: GymDetailMetaApiResponse | null;
  gym?: GymDetailGymApiResponse | null;
  slug?: string | null;
  name?: string | null;
  description?: string | null;
  address?: string | null;
  prefecture?: string | null;
  pref?: string | null;
  city?: string | null;
  categories?: (string | GymCategoryApiResponse)[] | Record<string, unknown> | null;
  opening_hours?: string | null;
  openingHours?: string | null;
  fees?: string | null;
  price?: string | null;
  website?: string | null;
  website_url?: string | null;
  phone?: string | null;
  equipments?: unknown;
  equipment_details?: unknown;
  facilities?: unknown;
  facility_groups?: unknown;
  tags?: string[] | null;
  location?: GymLocationApiResponse | null;
  latitude?: number | null;
  lat?: number | null;
  longitude?: number | null;
  lng?: number | null;
  official_url?: string | null;

  // Category-specific fields
  category?: string | null;
  pool_lanes?: number | null;
  pool_length_m?: number | null;
  pool_heated?: boolean | null;
  court_type?: string | null;
  court_count?: number | null;
  court_surface?: string | null;
  court_lighting?: boolean | null;
  hall_sports?: string[] | null;
  hall_area_sqm?: number | null;
  field_type?: string | null;
  field_count?: number | null;
  field_lighting?: boolean | null;

  // Archery-specific fields
  archery_type?: string | null;
  archery_rooms?: number | null;

  // Meta for structured data
  facility_meta?: Record<string, unknown> | null;
}
