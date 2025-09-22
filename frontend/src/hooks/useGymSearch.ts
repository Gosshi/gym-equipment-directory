"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { ApiError } from "@/lib/apiClient";
import {
  DEFAULT_FILTER_STATE,
  DEFAULT_LIMIT,
  MAX_LIMIT,
  type FilterState,
  type SortOption,
  areCategoriesEqual,
  normalizeCategories,
  parseFilterState,
  serializeFilterState,
} from "@/lib/searchParams";
import { searchGyms } from "@/services/gyms";
import { getCities, getEquipmentCategories, getPrefectures } from "@/services/meta";
import type { GymSearchMeta, GymSummary } from "@/types/gym";
import type {
  CityOption,
  EquipmentCategoryOption,
  PrefectureOption,
} from "@/types/meta";

const DEFAULT_DEBOUNCE_MS = 300;

type FormState = {
  q: string;
  prefecture: string;
  city: string;
  categories: string[];
  sort: SortOption;
  distance: number;
};

const toFormState = (filters: FilterState): FormState => ({
  q: filters.q,
  prefecture: filters.pref ?? "",
  city: filters.city ?? "",
  categories: [...filters.categories],
  sort: filters.sort,
  distance: filters.distance,
});

const areFormStatesEqual = (a: FormState, b: FormState) =>
  a.q === b.q &&
  a.prefecture === b.prefecture &&
  a.city === b.city &&
  a.sort === b.sort &&
  a.distance === b.distance &&
  areCategoriesEqual(a.categories, b.categories);

const buildFilterStateFromForm = (
  form: FormState,
  base: FilterState,
  overrides: Partial<FilterState> = {},
): FilterState => ({
  q: form.q.trim(),
  pref: form.prefecture.trim() || null,
  city: form.city.trim() || null,
  categories: normalizeCategories(form.categories),
  sort: form.sort,
  page: 1,
  limit: base.limit,
  distance: form.distance,
  ...overrides,
});

export interface UseGymSearchOptions {
  debounceMs?: number;
}

export interface UseGymSearchResult {
  formState: FormState;
  appliedFilters: FilterState;
  updateKeyword: (value: string) => void;
  updatePrefecture: (value: string) => void;
  updateCity: (value: string) => void;
  updateCategories: (values: string[]) => void;
  updateSort: (value: SortOption) => void;
  updateDistance: (value: number) => void;
  clearFilters: () => void;
  page: number;
  limit: number;
  setPage: (page: number) => void;
  setLimit: (limit: number) => void;
  loadNextPage: () => void;
  items: GymSummary[];
  meta: GymSearchMeta;
  isLoading: boolean;
  isInitialLoading: boolean;
  error: string | null;
  retry: () => void;
  prefectures: PrefectureOption[];
  cities: CityOption[];
  equipmentCategories: EquipmentCategoryOption[];
  isMetaLoading: boolean;
  metaError: string | null;
  reloadMeta: () => void;
  isCityLoading: boolean;
  cityError: string | null;
  reloadCities: () => void;
}

export function useGymSearch(
  options: UseGymSearchOptions = {},
): UseGymSearchResult {
  const { debounceMs = DEFAULT_DEBOUNCE_MS } = options;
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const searchParamsKey = searchParams.toString();

  const appliedFilters = useMemo(
    () => parseFilterState(new URLSearchParams(searchParamsKey)),
    [searchParamsKey],
  );

  const [formState, setFormState] = useState<FormState>(() =>
    toFormState(appliedFilters),
  );

  useEffect(() => {
    const next = toFormState(appliedFilters);
    setFormState((prev) => (areFormStatesEqual(prev, next) ? prev : next));
  }, [appliedFilters]);

  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  const cancelPendingDebounce = useCallback(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
  }, []);

  useEffect(() => cancelPendingDebounce, [cancelPendingDebounce]);

  const appendModeRef = useRef(false);

  const applyFilters = useCallback(
    (nextFilters: FilterState, options: { append?: boolean } = {}) => {
      const params = serializeFilterState(nextFilters);
      const nextQuery = params.toString();
      if (nextQuery === searchParamsKey) {
        appendModeRef.current = false;
        return;
      }

      appendModeRef.current = Boolean(options.append);
      const nextUrl = nextQuery ? `${pathname}?${nextQuery}` : pathname;
      router.push(nextUrl, { scroll: false });
    },
    [pathname, router, searchParamsKey],
  );

  const scheduleApply = useCallback(
    (updater: (prev: FormState) => FormState) => {
      setFormState((prev) => {
        const updated = updater(prev);
        const normalized: FormState = {
          q: updated.q,
          prefecture: updated.prefecture.trim(),
          city: updated.city.trim(),
          categories: normalizeCategories(updated.categories),
          sort: updated.sort,
          distance: updated.distance,
        };

        if (areFormStatesEqual(prev, normalized)) {
          return prev;
        }

        cancelPendingDebounce();
        debounceRef.current = setTimeout(() => {
          applyFilters(buildFilterStateFromForm(normalized, appliedFilters));
        }, debounceMs);

        return normalized;
      });
    },
    [appliedFilters, applyFilters, cancelPendingDebounce, debounceMs],
  );

  const updateKeyword = useCallback(
    (value: string) => scheduleApply((prev) => ({ ...prev, q: value })),
    [scheduleApply],
  );

  const updatePrefecture = useCallback(
    (value: string) =>
      scheduleApply((prev) => ({
        ...prev,
        prefecture: value,
        city: "",
      })),
    [scheduleApply],
  );

  const updateCity = useCallback(
    (value: string) => scheduleApply((prev) => ({ ...prev, city: value })),
    [scheduleApply],
  );

  const updateCategories = useCallback(
    (values: string[]) =>
      scheduleApply((prev) => ({
        ...prev,
        categories: values,
      })),
    [scheduleApply],
  );

  const updateSort = useCallback(
    (value: SortOption) => scheduleApply((prev) => ({ ...prev, sort: value })),
    [scheduleApply],
  );

  const updateDistance = useCallback(
    (value: number) =>
      scheduleApply((prev) => ({
        ...prev,
        distance: value,
      })),
    [scheduleApply],
  );

  const clearFilters = useCallback(() => {
    cancelPendingDebounce();
    const resetFilters: FilterState = {
      ...DEFAULT_FILTER_STATE,
      limit: appliedFilters.limit,
    };
    setFormState(toFormState(resetFilters));
    applyFilters(resetFilters);
  }, [appliedFilters.limit, applyFilters, cancelPendingDebounce]);

  const setPage = useCallback(
    (page: number, options: { append?: boolean } = {}) => {
      const nextPage = Number.isFinite(page) && page > 0 ? Math.trunc(page) : 1;
      cancelPendingDebounce();
      applyFilters(
        {
          ...appliedFilters,
          page: nextPage,
        },
        { append: options.append },
      );
    },
    [appliedFilters, applyFilters, cancelPendingDebounce],
  );

  const setLimit = useCallback(
    (value: number) => {
      const parsed = Number.isFinite(value) ? Math.trunc(value) : DEFAULT_LIMIT;
      const clamped = Math.min(Math.max(parsed, 1), MAX_LIMIT);
      cancelPendingDebounce();
      applyFilters(
        {
          ...appliedFilters,
          limit: clamped,
          page: 1,
        },
        { append: false },
      );
    },
    [appliedFilters, applyFilters, cancelPendingDebounce],
  );

  const [items, setItems] = useState<GymSummary[]>([]);
  const [meta, setMeta] = useState<GymSearchMeta>({
    total: 0,
    hasNext: false,
    pageToken: null,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshIndex, setRefreshIndex] = useState(0);

  const retry = useCallback(() => setRefreshIndex((value) => value + 1), []);

  const loadNextPage = useCallback(() => {
    if (isLoading || !meta.hasNext) {
      return;
    }
    setPage(appliedFilters.page + 1, { append: true });
  }, [appliedFilters.page, isLoading, meta.hasNext, setPage]);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const shouldAppend = appendModeRef.current;
    appendModeRef.current = false;

    setIsLoading(true);
    setError(null);

    searchGyms(
      {
        q: appliedFilters.q || undefined,
        prefecture: appliedFilters.pref ?? undefined,
        city: appliedFilters.city ?? undefined,
        categories: appliedFilters.categories,
        sort: appliedFilters.sort,
        page: appliedFilters.page,
        limit: appliedFilters.limit,
      },
      { signal: controller.signal },
    )
      .then((response) => {
        if (!active) {
          return;
        }
        setItems((previous) => {
          if (!shouldAppend) {
            return response.items;
          }

          if (response.items.length === 0) {
            return previous;
          }

          const seen = new Set(previous.map((item) => item.id));
          const merged = [...previous];
          for (const item of response.items) {
            if (seen.has(item.id)) {
              continue;
            }
            seen.add(item.id);
            merged.push(item);
          }
          return merged;
        });
        setMeta(response.meta);
        setHasLoadedOnce(true);
      })
      .catch((err) => {
        if (!active) {
          return;
        }
        if (
          err instanceof DOMException &&
          err.name === "AbortError"
        ) {
          return;
        }
        if (err instanceof ApiError) {
          setError(err.message || "ジムの取得に失敗しました");
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("ジムの取得に失敗しました");
        }
      })
      .finally(() => {
        if (!active) {
          return;
        }
        setIsLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [appliedFilters, refreshIndex]);

  const [prefectures, setPrefectures] = useState<PrefectureOption[]>([]);
  const [equipmentCategories, setEquipmentCategories] =
    useState<EquipmentCategoryOption[]>([]);
  const [isMetaLoading, setIsMetaLoading] = useState(false);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [metaReloadIndex, setMetaReloadIndex] = useState(0);

  const reloadMeta = useCallback(
    () => setMetaReloadIndex((value) => value + 1),
    [],
  );

  useEffect(() => {
    let active = true;
    setIsMetaLoading(true);
    setMetaError(null);

    Promise.all([getPrefectures(), getEquipmentCategories()])
      .then(([prefData, equipmentData]) => {
        if (!active) {
          return;
        }
        setPrefectures(prefData);
        setEquipmentCategories(equipmentData);
      })
      .catch((err) => {
        if (!active) {
          return;
        }
        if (err instanceof ApiError) {
          setMetaError(err.message || "検索条件の取得に失敗しました");
        } else if (err instanceof Error) {
          setMetaError(err.message);
        } else {
          setMetaError("検索条件の取得に失敗しました");
        }
      })
      .finally(() => {
        if (!active) {
          return;
        }
        setIsMetaLoading(false);
      });

    return () => {
      active = false;
    };
  }, [metaReloadIndex]);

  const [cities, setCities] = useState<CityOption[]>([]);
  const [isCityLoading, setIsCityLoading] = useState(false);
  const [cityError, setCityError] = useState<string | null>(null);
  const citiesCacheRef = useRef(new Map<string, CityOption[]>());
  const [cityReloadIndex, setCityReloadIndex] = useState(0);

  const reloadCities = useCallback(() => {
    const prefSlug = formState.prefecture.trim();
    if (prefSlug) {
      citiesCacheRef.current.delete(prefSlug);
    }
    setCityReloadIndex((value) => value + 1);
  }, [formState.prefecture]);

  useEffect(() => {
    const prefSlug = formState.prefecture.trim();
    if (!prefSlug) {
      setCities([]);
      setCityError(null);
      return;
    }

    const cached = citiesCacheRef.current.get(prefSlug);
    if (cached) {
      setCities(cached);
      setCityError(null);
      return;
    }

    let active = true;
    setIsCityLoading(true);
    setCityError(null);

    getCities(prefSlug)
      .then((data) => {
        if (!active) {
          return;
        }
        citiesCacheRef.current.set(prefSlug, data);
        setCities(data);
      })
      .catch((err) => {
        if (!active) {
          return;
        }
        if (err instanceof ApiError) {
          setCityError(err.message || "市区町村の取得に失敗しました");
        } else if (err instanceof Error) {
          setCityError(err.message);
        } else {
          setCityError("市区町村の取得に失敗しました");
        }
      })
      .finally(() => {
        if (!active) {
          return;
        }
        setIsCityLoading(false);
      });

    return () => {
      active = false;
    };
  }, [formState.prefecture, cityReloadIndex]);

  const isInitialLoading = isLoading && !hasLoadedOnce;

  return {
    formState,
    appliedFilters,
    updateKeyword,
    updatePrefecture,
    updateCity,
    updateCategories,
    updateSort,
    updateDistance,
    clearFilters,
    page: appliedFilters.page,
    limit: appliedFilters.limit,
    setPage,
    setLimit,
    loadNextPage,
    items,
    meta,
    isLoading,
    isInitialLoading,
    error,
    retry,
    prefectures,
    cities,
    equipmentCategories,
    isMetaLoading,
    metaError,
    reloadMeta,
    isCityLoading,
    cityError,
    reloadCities,
  };
}
