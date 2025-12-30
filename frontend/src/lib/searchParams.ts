export type SortOption = "distance" | "name";
export type SortOrder = "asc" | "desc";

export const SORT_OPTIONS: SortOption[] = ["distance", "name"];

const SORT_OPTION_SET = new Set<SortOption>(SORT_OPTIONS);
const SORT_ORDER_SET = new Set<SortOrder>(["asc", "desc"]);

export const DEFAULT_SORT: SortOption = "name";
export const DEFAULT_ORDER: SortOrder = "asc";

export const SORT_DEFAULT_ORDERS: Record<SortOption, SortOrder> = {
  distance: "asc",
  name: "asc",
};

export const SORT_ALLOWED_ORDERS: Record<SortOption, SortOrder[]> = {
  distance: ["asc"],
  name: ["asc"],
};

export const getDefaultOrderForSort = (sort: SortOption): SortOrder => SORT_DEFAULT_ORDERS[sort];

export const normalizeSortOrder = (
  sort: SortOption,
  order: SortOrder | null | undefined,
): SortOrder => {
  const allowed = SORT_ALLOWED_ORDERS[sort] ?? [getDefaultOrderForSort(sort)];
  if (order && allowed.includes(order)) {
    return order;
  }
  return allowed[0];
};

export const DEFAULT_LIMIT = 20;
export const MAX_LIMIT = 100;

export const MIN_DISTANCE_KM = 1;
export const MAX_DISTANCE_KM = 30;
export const DISTANCE_STEP_KM = 1;
export const DEFAULT_DISTANCE_KM = 5;

export const MIN_LATITUDE = -90;
export const MAX_LATITUDE = 90;
export const MIN_LONGITUDE = -180;
export const MAX_LONGITUDE = 180;

export type ConditionOption =
  | "parking"
  | "24h"
  | "shower"
  | "sauna"
  | "wifi"
  | "powder_room"
  | "rental_wear"
  | "rental_shoes"
  | "rental_towel";

export const CONDITION_OPTIONS: { value: ConditionOption; label: string }[] = [
  { value: "parking", label: "駐車場あり" },
  { value: "24h", label: "24時間営業" },
  { value: "shower", label: "シャワー" },
  { value: "sauna", label: "サウナ" },
  { value: "wifi", label: "Wi-Fi" },
  { value: "powder_room", label: "パウダールーム" },
  { value: "rental_wear", label: "レンタルウェア" },
  { value: "rental_shoes", label: "レンタルシューズ" },
  { value: "rental_towel", label: "レンタルタオル" },
];

export interface FilterState {
  q: string;
  pref: string | null;
  city: string | null;
  categories: string[];
  equipments: string[];
  conditions: string[];
  sort: SortOption;
  order: SortOrder;
  page: number;
  limit: number;
  distance: number;
  lat: number | null;
  lng: number | null;
  min_lat: number | null;
  max_lat: number | null;
  min_lng: number | null;
  max_lng: number | null;
}

export const DEFAULT_FILTER_STATE: FilterState = {
  q: "",
  pref: null,
  city: null,
  categories: [],
  equipments: [],
  conditions: [],
  sort: DEFAULT_SORT,
  order: DEFAULT_ORDER,
  page: 1,
  limit: DEFAULT_LIMIT,
  distance: DEFAULT_DISTANCE_KM,
  lat: null,
  lng: null,
  min_lat: null,
  max_lat: null,
  min_lng: null,
  max_lng: null,
};

const parsePositiveInt = (value: string | null, fallback: number): number => {
  if (!value) {
    return fallback;
  }
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallback;
  }
  return parsed;
};

const clampLimit = (value: number) => Math.min(Math.max(value, 1), MAX_LIMIT);

const clampDistance = (value: number) =>
  Math.min(Math.max(value, MIN_DISTANCE_KM), MAX_DISTANCE_KM);

export const clampLatitude = (value: number) =>
  Math.min(Math.max(value, MIN_LATITUDE), MAX_LATITUDE);

export const clampLongitude = (value: number) =>
  Math.min(Math.max(value, MIN_LONGITUDE), MAX_LONGITUDE);

const sanitizeSlug = (value: string | null): string | null => {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

const normalizeCsvList = (value: string | null): string[] => {
  if (!value) {
    return [];
  }
  const sanitized = value
    .split(",")
    .map(part => part.trim())
    .filter(Boolean);
  return Array.from(new Set(sanitized));
};

const parseCategories = (params: URLSearchParams): string[] => {
  const source = params.get("cats") ?? params.get("categories");
  return normalizeCsvList(source);
};

const parseEquipments = (params: URLSearchParams): string[] => {
  const source = params.get("equipments") ?? params.get("equipment");
  return normalizeCsvList(source);
};

const parseConditions = (params: URLSearchParams): string[] => {
  const source = params.get("conditions") ?? params.get("conds");
  return normalizeCsvList(source);
};

export const isSortOption = (value: string | null | undefined): value is SortOption =>
  typeof value === "string" && SORT_OPTION_SET.has(value as SortOption);

export const isSortOrder = (value: string | null | undefined): value is SortOrder =>
  typeof value === "string" && SORT_ORDER_SET.has(value as SortOrder);

const parseSort = (value: string | null): SortOption => {
  if (!value) {
    return DEFAULT_SORT;
  }
  if (SORT_OPTION_SET.has(value as SortOption)) {
    return value as SortOption;
  }
  if (value === "score" || value === "popular" || value === "richness") {
    return "name";
  }
  if (value === "fresh" || value === "freshness") {
    return "name";
  }
  if (value === "newest" || value === "created_at") {
    return "name";
  }
  return DEFAULT_SORT;
};

const parseSortOrder = (sort: SortOption, value: string | null): SortOrder => {
  if (!value || !isSortOrder(value)) {
    return getDefaultOrderForSort(sort);
  }
  return normalizeSortOrder(sort, value);
};

const parseDistance = (value: string | null): number => {
  if (!value) {
    return DEFAULT_DISTANCE_KM;
  }
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed)) {
    return DEFAULT_DISTANCE_KM;
  }
  return clampDistance(parsed);
};

const parseLatitude = (value: string | null): number | null => {
  if (!value) {
    return null;
  }
  const parsed = Number.parseFloat(value);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return clampLatitude(parsed);
};

const parseLongitude = (value: string | null): number | null => {
  if (!value) {
    return null;
  }
  const parsed = Number.parseFloat(value);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return clampLongitude(parsed);
};

export const parseFilterState = (params: URLSearchParams): FilterState => {
  const q = params.get("q")?.trim() ?? "";
  const pref = sanitizeSlug(params.get("pref") ?? params.get("prefecture"));
  const city = sanitizeSlug(params.get("city"));
  const categories = parseCategories(params);
  const equipments = parseEquipments(params);
  const conditions = parseConditions(params);
  const sort = parseSort(params.get("sort"));
  const order = parseSortOrder(sort, params.get("order"));
  const page = parsePositiveInt(params.get("page"), 1);
  const limit = clampLimit(
    parsePositiveInt(
      params.get("page_size") ?? params.get("per_page") ?? params.get("limit"),
      DEFAULT_LIMIT,
    ),
  );
  const distance = parseDistance(params.get("radius_km") ?? params.get("distance"));
  const latRaw = parseLatitude(params.get("lat"));
  const lngRaw = parseLongitude(params.get("lng"));
  const lat = latRaw != null && lngRaw != null ? latRaw : null;
  const lng = latRaw != null && lngRaw != null ? lngRaw : null;
  const minLat = parseLatitude(params.get("min_lat"));
  const maxLat = parseLatitude(params.get("max_lat"));
  const minLng = parseLongitude(params.get("min_lng"));
  const maxLng = parseLongitude(params.get("max_lng"));

  return {
    q,
    pref,
    city,
    categories,
    equipments,
    conditions,
    sort,
    order,
    page,
    limit,
    distance,
    lat,
    lng,
    min_lat: minLat,
    max_lat: maxLat,
    min_lng: minLng,
    max_lng: maxLng,
  };
};

export const serializeFilterState = (state: FilterState): URLSearchParams => {
  const params = new URLSearchParams();

  if (state.q.trim()) {
    params.set("q", state.q.trim());
  }
  if (state.pref) {
    params.set("pref", state.pref);
  }
  if (state.city) {
    params.set("city", state.city);
  }
  if (state.categories.length > 0) {
    params.set("cats", state.categories.join(","));
  }
  if (state.equipments.length > 0) {
    params.set("equipments", state.equipments.join(","));
  }
  if (state.conditions.length > 0) {
    params.set("conditions", state.conditions.join(","));
  }
  params.set("sort", state.sort);
  params.set("order", normalizeSortOrder(state.sort, state.order));
  if (state.page > 1) {
    params.set("page", String(state.page));
  }
  if (state.limit !== DEFAULT_LIMIT) {
    params.set("page_size", String(state.limit));
  }
  if (state.lat != null && state.lng != null) {
    params.set("radius_km", String(state.distance));
    params.set("lat", state.lat.toFixed(6));
    params.set("lng", state.lng.toFixed(6));
  } else if (state.distance !== DEFAULT_DISTANCE_KM) {
    params.set("radius_km", String(state.distance));
  }

  if (state.min_lat != null) params.set("min_lat", state.min_lat.toFixed(6));
  if (state.max_lat != null) params.set("max_lat", state.max_lat.toFixed(6));
  if (state.min_lng != null) params.set("min_lng", state.min_lng.toFixed(6));
  if (state.max_lng != null) params.set("max_lng", state.max_lng.toFixed(6));

  return params;
};

export const filterStateToQueryString = (state: FilterState): string =>
  serializeFilterState(state).toString();

export const areCategoriesEqual = (a: string[], b: string[]) => {
  if (a.length !== b.length) {
    return false;
  }
  return a.every((value, index) => value === b[index]);
};

export const normalizeCategories = (values: string[]): string[] =>
  Array.from(new Set(values.map(value => value.trim()).filter(Boolean)));
