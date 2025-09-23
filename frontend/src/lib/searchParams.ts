export type SortOption = "distance" | "popular" | "fresh" | "newest";

export const SORT_OPTIONS: SortOption[] = [
  "distance",
  "popular",
  "fresh",
  "newest",
];

const SORT_OPTION_SET = new Set<SortOption>(SORT_OPTIONS);

export const DEFAULT_SORT: SortOption = "popular";

export const DEFAULT_LIMIT = 20;
export const MAX_LIMIT = 50;

export const MIN_DISTANCE_KM = 1;
export const MAX_DISTANCE_KM = 30;
export const DISTANCE_STEP_KM = 1;
export const DEFAULT_DISTANCE_KM = 5;

export interface FilterState {
  q: string;
  pref: string | null;
  city: string | null;
  categories: string[];
  sort: SortOption;
  page: number;
  limit: number;
  distance: number;
}

export const DEFAULT_FILTER_STATE: FilterState = {
  q: "",
  pref: null,
  city: null,
  categories: [],
  sort: DEFAULT_SORT,
  page: 1,
  limit: DEFAULT_LIMIT,
  distance: DEFAULT_DISTANCE_KM,
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
    .map((part) => part.trim())
    .filter(Boolean);
  return Array.from(new Set(sanitized));
};

const parseCategories = (params: URLSearchParams): string[] => {
  const source = params.get("cats") ?? params.get("equipments") ?? params.get("equipment");
  return normalizeCsvList(source);
};

export const isSortOption = (value: string | null | undefined): value is SortOption =>
  typeof value === "string" && SORT_OPTION_SET.has(value as SortOption);

const parseSort = (value: string | null): SortOption => {
  if (!value) {
    return DEFAULT_SORT;
  }
  if (SORT_OPTION_SET.has(value as SortOption)) {
    return value as SortOption;
  }
  if (value === "freshness") {
    return "fresh";
  }
  if (value === "created_at") {
    return "newest";
  }
  if (value === "score") {
    return "popular";
  }
  return DEFAULT_SORT;
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

export const parseFilterState = (params: URLSearchParams): FilterState => {
  const q = params.get("q")?.trim() ?? "";
  const pref = sanitizeSlug(params.get("pref") ?? params.get("prefecture"));
  const city = sanitizeSlug(params.get("city"));
  const categories = parseCategories(params);
  const sort = parseSort(params.get("sort"));
  const page = parsePositiveInt(params.get("page"), 1);
  const limit = clampLimit(
    parsePositiveInt(params.get("per_page") ?? params.get("limit"), DEFAULT_LIMIT),
  );
  const distance = parseDistance(params.get("distance"));

  return {
    q,
    pref,
    city,
    categories,
    sort,
    page,
    limit,
    distance,
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
  if (state.sort !== DEFAULT_SORT) {
    params.set("sort", state.sort);
  }
  if (state.page > 1) {
    params.set("page", String(state.page));
  }
  if (state.limit !== DEFAULT_LIMIT) {
    params.set("per_page", String(state.limit));
  }
  if (state.distance !== DEFAULT_DISTANCE_KM) {
    params.set("distance", String(state.distance));
  }

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
  Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
