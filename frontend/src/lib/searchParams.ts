export type GymSearchSort = "score" | "freshness" | "created_at" | "richness" | "gym_name";

export interface GymSearchFilters {
  q: string;
  pref: string | null;
  city: string | null;
  cats: string[];
  sort: GymSearchSort;
  page: number;
  limit: number;
}

export const DEFAULT_QUERY_STATE: GymSearchFilters = {
  q: "",
  pref: null,
  city: null,
  cats: [],
  sort: "score",
  page: 1,
  limit: 20,
};

const SORT_VALUES: GymSearchSort[] = ["score", "freshness", "created_at", "richness", "gym_name"];

const clamp = (value: number, min: number, max: number): number => {
  if (!Number.isFinite(value)) {
    return min;
  }
  if (value < min) {
    return min;
  }
  if (value > max) {
    return max;
  }
  return value;
};

const parsePositiveInt = (value: string | null, fallback: number, max: number) => {
  if (!value) {
    return fallback;
  }
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return clamp(parsed, 1, max);
};

const normalizeCsv = (value: string | null): string[] => {
  if (!value) {
    return [];
  }
  const seen = new Set<string>();
  const normalized: string[] = [];
  value
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean)
    .forEach((part) => {
      const key = part.toLowerCase();
      if (seen.has(key)) {
        return;
      }
      seen.add(key);
      normalized.push(part);
    });
  return normalized;
};

const normalizeSort = (input: string | null): GymSearchSort => {
  if (!input) {
    return DEFAULT_QUERY_STATE.sort;
  }
  return SORT_VALUES.includes(input as GymSearchSort)
    ? (input as GymSearchSort)
    : DEFAULT_QUERY_STATE.sort;
};

export const parseSearchParams = (params: URLSearchParams): GymSearchFilters => {
  const sortParam = params.get("sort");
  const qParam = params.get("q");
  const prefParam = params.get("pref");
  const cityParam = params.get("city");
  const catsParam = params.get("cats");
  const pageParam = params.get("page");
  const limitParam = params.get("limit");

  const q = qParam ? qParam.trim() : DEFAULT_QUERY_STATE.q;
  const pref = prefParam ? prefParam.trim() || null : DEFAULT_QUERY_STATE.pref;
  const city = cityParam ? cityParam.trim() || null : DEFAULT_QUERY_STATE.city;
  const cats = normalizeCsv(catsParam);
  const sort = normalizeSort(sortParam);
  const page = parsePositiveInt(pageParam, DEFAULT_QUERY_STATE.page, Number.MAX_SAFE_INTEGER);
  const limit = parsePositiveInt(limitParam, DEFAULT_QUERY_STATE.limit, 50);

  return {
    q,
    pref,
    city,
    cats,
    sort,
    page,
    limit,
  };
};

const shouldSerializeString = (value: string | null | undefined): value is string =>
  Boolean(value && value.trim().length > 0);

export const serializeSearchParams = (filters: GymSearchFilters): URLSearchParams => {
  const params = new URLSearchParams();

  if (shouldSerializeString(filters.q)) {
    params.set("q", filters.q.trim());
  }
  if (shouldSerializeString(filters.pref)) {
    params.set("pref", filters.pref!.trim());
  }
  if (shouldSerializeString(filters.city)) {
    params.set("city", filters.city!.trim());
  }
  if (filters.cats.length > 0) {
    params.set("cats", filters.cats.join(","));
  }
  if (filters.sort !== DEFAULT_QUERY_STATE.sort) {
    params.set("sort", filters.sort);
  }
  if (filters.page > 1) {
    params.set("page", String(filters.page));
  }
  if (filters.limit !== DEFAULT_QUERY_STATE.limit) {
    params.set("limit", String(filters.limit));
  }

  return params;
};

export const areCategoriesEqual = (a: string[], b: string[]) => {
  if (a.length !== b.length) {
    return false;
  }
  return a.every((value, index) => value === b[index]);
};

export const normalizeCategories = (values: string[]): string[] => {
  const seen = new Set<string>();
  const normalized: string[] = [];
  values
    .map((value) => value.trim())
    .filter(Boolean)
    .forEach((value) => {
      const key = value.toLowerCase();
      if (seen.has(key)) {
        return;
      }
      seen.add(key);
      normalized.push(value);
    });
  return normalized;
};

export const withResetPage = (filters: GymSearchFilters): GymSearchFilters => ({
  ...filters,
  page: DEFAULT_QUERY_STATE.page,
});
