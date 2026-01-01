import type { FacilityGroup } from "@/components/gym/GymFacilities";
import type {
  GymDetailApiResponse,
  GymEquipmentDetailApiResponse,
  GymFacilityCategoryApiResponse,
  GymLocationApiResponse,
} from "@/types/api";

export interface PoolItem {
  lanes?: number;
  lengthM?: number;
  heated?: boolean;
}

export interface CourtItem {
  courtType?: string;
  courts?: number;
  surface?: string;
  lighting?: boolean;
}

export interface NormalizedGymDetail {
  id: number;
  slug: string;
  name: string;
  description?: string;
  address?: string;
  prefecture?: string;
  city?: string;
  categories: string[];
  openingHours?: string;
  fees?: string;
  website?: string;
  facilities: FacilityGroup[];
  latitude?: number;
  longitude?: number;
  tags: string[];

  // Category and category-specific fields
  category?: string;
  poolLanes?: number;
  poolLengthM?: number;
  poolHeated?: boolean;
  pools?: PoolItem[];
  courtType?: string;
  courtCount?: number;
  courtSurface?: string;
  courtLighting?: boolean;
  courts?: CourtItem[];
  hallSports?: string[];
  hallAreaSqm?: number;
  fieldType?: string;
  fieldCount?: number;
  fieldLighting?: boolean;
  archeryType?: string;
  archeryRooms?: number;
  facility_meta?: Record<string, unknown>;
}

export const sanitizeText = (value: unknown): string | undefined => {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
};

const formatRegion = (value?: string | null): string | undefined => {
  const sanitized = sanitizeText(value);
  if (!sanitized) {
    return undefined;
  }

  return sanitized
    .split("-")
    .map(part => (part ? part.charAt(0).toUpperCase() + part.slice(1) : part))
    .join(" ");
};

const extractCategoryNames = (input: unknown): string[] => {
  const result: string[] = [];
  const seen = new Set<string>();

  const add = (value?: string) => {
    if (!value) {
      return;
    }
    if (seen.has(value)) {
      return;
    }
    seen.add(value);
    result.push(value);
  };

  const visit = (value: unknown) => {
    if (!value) {
      return;
    }
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (typeof value === "string") {
      add(sanitizeText(value));
      return;
    }
    if (typeof value === "object") {
      const record = value as Record<string, unknown>;
      const label =
        sanitizeText(record.name) ??
        sanitizeText(record.label) ??
        sanitizeText(record.title) ??
        sanitizeText(record.slug);

      if (label) {
        add(label);
        return;
      }

      for (const nested of Object.values(record)) {
        visit(nested);
      }
    }
  };

  visit(input);
  return result;
};

const extractFacilityItems = (input: unknown): string[] => {
  if (!input) {
    return [];
  }
  if (Array.isArray(input)) {
    const collected: string[] = [];
    for (const item of input) {
      collected.push(...extractFacilityItems(item));
    }
    return collected;
  }
  if (typeof input === "string") {
    const sanitized = sanitizeText(input);
    return sanitized ? [sanitized] : [];
  }
  if (typeof input === "object") {
    const record = input as Record<string, unknown>;
    const label =
      sanitizeText(record.name) ??
      sanitizeText(record.label) ??
      sanitizeText(record.title) ??
      sanitizeText(record.value) ??
      sanitizeText(record.slug);

    const results: string[] = [];
    if (label) {
      results.push(label);
    }

    const nestedKeys = [
      "items",
      "equipments",
      "equipment_details",
      "equipmentDetails",
      "values",
      "list",
    ];
    for (const key of nestedKeys) {
      if (record[key] !== undefined) {
        results.push(...extractFacilityItems(record[key]));
      }
    }

    return results;
  }
  return [];
};

const extractFacilityGroups = (data: GymDetailApiResponse): FacilityGroup[] => {
  const groups = new Map<string, { items: string[]; set: Set<string> }>();

  const ensureGroup = (category?: string | null) => {
    const label = sanitizeText(category) ?? "設備";
    const key = label.length > 0 ? label : "設備";
    if (!groups.has(key)) {
      groups.set(key, { items: [], set: new Set<string>() });
    }
    return groups.get(key)!;
  };

  const addItemsToGroup = (category: string | null | undefined, values: string[]) => {
    if (values.length === 0) {
      return;
    }
    const group = ensureGroup(category);
    for (const value of values) {
      const sanitized = sanitizeText(value);
      if (!sanitized || group.set.has(sanitized)) {
        continue;
      }
      group.set.add(sanitized);
      group.items.push(sanitized);
    }
  };

  const visitCategoryEntry = (entry: unknown) => {
    if (!entry) {
      return;
    }
    if (Array.isArray(entry)) {
      entry.forEach(visitCategoryEntry);
      return;
    }
    if (typeof entry === "string") {
      addItemsToGroup("設備", [entry]);
      return;
    }
    if (typeof entry === "object") {
      const record = entry as GymFacilityCategoryApiResponse & Record<string, unknown>;
      const category =
        record.category ?? record.name ?? record.label ?? record.title ?? record.group ?? undefined;

      const aggregated: string[] = [];
      if (record.items !== undefined) {
        aggregated.push(...extractFacilityItems(record.items));
      }
      if (record.equipments !== undefined) {
        aggregated.push(...extractFacilityItems(record.equipments));
      }
      if (record.equipment_details !== undefined) {
        aggregated.push(...extractFacilityItems(record.equipment_details));
      }
      if (aggregated.length === 0) {
        const fallback = sanitizeText(record.name) ?? sanitizeText(record.label);
        if (fallback) {
          aggregated.push(fallback);
        }
      }

      addItemsToGroup(category, aggregated);
      return;
    }
  };

  visitCategoryEntry(data.facilities);
  visitCategoryEntry(data.facility_groups);

  const equipmentDetails = data.equipment_details;
  if (Array.isArray(equipmentDetails)) {
    for (const item of equipmentDetails) {
      if (!item) {
        continue;
      }
      if (typeof item === "string") {
        addItemsToGroup("設備", [item]);
        continue;
      }
      if (typeof item === "object") {
        const record = item as GymEquipmentDetailApiResponse & Record<string, unknown>;
        const category = record.category ?? record.group ?? record.type ?? undefined;
        const label =
          sanitizeText(record.name) ?? sanitizeText(record.label) ?? sanitizeText(record.title);
        const nested = extractFacilityItems(record.items);
        const combined = [...(label ? [label] : []), ...nested];
        addItemsToGroup(category, combined);
      }
    }
  } else if (equipmentDetails) {
    addItemsToGroup("設備", extractFacilityItems(equipmentDetails));
  }

  if (data.equipments) {
    addItemsToGroup("設備", extractFacilityItems(data.equipments));
  }

  const result: FacilityGroup[] = [];
  for (const [category, { items }] of groups.entries()) {
    if (items.length > 0) {
      result.push({ category, items });
    }
  }
  return result;
};

export const normalizeGymDetail = (
  data: GymDetailApiResponse,
  canonicalSlug: string,
): NormalizedGymDetail => {
  // Prioritize categories array from backend (new format), fallback to extraction
  const backendCategories = Array.isArray(data.categories)
    ? data.categories.filter((c): c is string => typeof c === "string")
    : [];
  const categories =
    backendCategories.length > 0
      ? backendCategories
      : extractCategoryNames(data.categories ?? data.facilities ?? []);
  const facilities = extractFacilityGroups(data);
  const gymRecord = (data.gym ?? {}) as Record<string, unknown>;
  const locationSource =
    data.location ?? (gymRecord.location as GymLocationApiResponse | null | undefined);
  const location = locationSource ?? null;

  const pickNumber = (...values: unknown[]): number | undefined => {
    for (const value of values) {
      if (typeof value === "number" && Number.isFinite(value)) {
        return value;
      }
      if (typeof value === "string") {
        const parsed = Number(value);
        if (!Number.isNaN(parsed)) {
          return parsed;
        }
      }
    }
    return undefined;
  };

  const latitude = pickNumber(
    data.latitude,
    data.lat,
    gymRecord.latitude,
    gymRecord.lat,
    location?.latitude,
    location?.lat,
    location?.latitude,
    location?.lat,
  );
  const longitude = pickNumber(
    data.longitude,
    data.lng,
    gymRecord.longitude,
    gymRecord.lng,
    location?.longitude,
    location?.lng,
    location?.longitude,
    location?.lng,
  );

  const resolvedName = sanitizeText(data.name) ?? sanitizeText(gymRecord.name) ?? canonicalSlug;
  const resolvedAddress =
    sanitizeText(data.address) ??
    sanitizeText(gymRecord.address) ??
    sanitizeText(location?.address);
  const resolvedPref =
    sanitizeText(data.prefecture ?? data.pref) ??
    sanitizeText(gymRecord.pref ?? gymRecord.prefecture);
  const resolvedCity = sanitizeText(data.city) ?? sanitizeText(gymRecord.city);
  const resolvedWebsite = sanitizeText(data.official_url ?? data.website ?? data.website_url);

  return {
    id: gymRecord.id as number,
    slug: canonicalSlug,
    name: resolvedName,
    description: sanitizeText(data.description),
    address: resolvedAddress,
    prefecture: formatRegion(resolvedPref),
    city: formatRegion(resolvedCity),
    categories,
    openingHours: sanitizeText(data.openingHours ?? data.opening_hours),
    fees: sanitizeText(data.fees ?? data.price),
    website: resolvedWebsite,
    facilities,
    latitude,
    longitude,
    tags: data.tags ?? [],

    // Category-specific fields
    category: sanitizeText(data.category ?? gymRecord.category),
    poolLanes: pickNumber(data.pool_lanes ?? gymRecord.pool_lanes),
    poolLengthM: pickNumber(data.pool_length_m ?? gymRecord.pool_length_m),
    poolHeated: data.pool_heated ?? (gymRecord.pool_heated as boolean | undefined),
    pools: Array.isArray(data.pools)
      ? data.pools.map((p: Record<string, unknown>) => ({
          lanes: pickNumber(p.lanes),
          lengthM: pickNumber(p.length_m ?? p.lengthM),
          heated: p.heated as boolean | undefined,
        }))
      : [],
    courtType: sanitizeText(data.court_type ?? gymRecord.court_type),
    courtCount: pickNumber(data.court_count ?? gymRecord.court_count),
    courtSurface: sanitizeText(data.court_surface ?? gymRecord.court_surface),
    courtLighting: data.court_lighting ?? (gymRecord.court_lighting as boolean | undefined),
    courts: Array.isArray(data.courts)
      ? data.courts.map((c: Record<string, unknown>) => ({
          courtType: sanitizeText(c.court_type ?? c.courtType),
          courts: pickNumber(c.courts),
          surface: sanitizeText(c.surface),
          lighting: c.lighting as boolean | undefined,
        }))
      : [],
    hallSports: Array.isArray(data.hall_sports)
      ? data.hall_sports
      : Array.isArray(gymRecord.hall_sports)
        ? (gymRecord.hall_sports as string[])
        : [],
    hallAreaSqm: pickNumber(data.hall_area_sqm ?? gymRecord.hall_area_sqm),
    fieldType: sanitizeText(data.field_type ?? gymRecord.field_type),
    fieldCount: pickNumber(data.field_count ?? gymRecord.field_count),
    fieldLighting: data.field_lighting ?? (gymRecord.field_lighting as boolean | undefined),
    archeryType: sanitizeText(data.archery_type ?? gymRecord.archery_type),
    archeryRooms: pickNumber(data.archery_rooms ?? gymRecord.archery_rooms),
  };
};
