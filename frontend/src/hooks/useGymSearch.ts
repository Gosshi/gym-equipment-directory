"use client";

import { useCallback, useEffect, useMemo, useRef, useState, useTransition } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { ApiError } from "@/lib/apiClient";
import {
  DEFAULT_FILTER_STATE,
  DEFAULT_LIMIT,
  MAX_LIMIT,
  DEFAULT_DISTANCE_KM,
  type FilterState,
  type SortOption,
  type SortOrder,
  areCategoriesEqual,
  normalizeCategories,
  parseFilterState,
  serializeFilterState,
  normalizeSortOrder,
  clampLatitude,
  clampLongitude,
} from "@/lib/searchParams";
import { searchGyms } from "@/services/gyms";
import { getCities, getEquipmentCategories, getPrefectures } from "@/services/meta";
import type { GymSearchMeta, GymSummary } from "@/types/gym";
import type { CityOption, EquipmentCategoryOption, PrefectureOption } from "@/types/meta";

const DEFAULT_DEBOUNCE_MS = 300;

export const FALLBACK_LOCATION = Object.freeze({
  lat: 35.681236,
  lng: 139.767125,
  label: "東京駅",
});

const FALLBACK_COORDINATE_EPSILON = 0.000005;

const isFallbackCoordinates = (lat: number | null, lng: number | null) =>
  lat != null &&
  lng != null &&
  Math.abs(lat - FALLBACK_LOCATION.lat) < FALLBACK_COORDINATE_EPSILON &&
  Math.abs(lng - FALLBACK_LOCATION.lng) < FALLBACK_COORDINATE_EPSILON;

const LOCATION_PERMISSION_DENIED_MESSAGE =
  "位置情報が許可されていません。任意の地点を選ぶか、許可してください。";
const LOCATION_UNAVAILABLE_MESSAGE =
  "位置情報を取得できませんでした。デフォルト地点を利用しています。";
const LOCATION_TIMEOUT_MESSAGE =
  "位置情報の取得がタイムアウトしました。デフォルト地点を利用しています。";
const LOCATION_UNSUPPORTED_MESSAGE =
  "この環境では位置情報を取得できません。緯度・経度を手入力するか、デフォルト地点を利用してください。";

export type LocationMode = "off" | "auto" | "manual" | "fallback";
export type LocationStatus = "idle" | "loading" | "success" | "error";

export interface LocationState {
  lat: number | null;
  lng: number | null;
  mode: LocationMode;
  status: LocationStatus;
  error: string | null;
  isSupported: boolean;
  isFallback: boolean;
  fallbackLabel: string | null;
}

type FormState = {
  q: string;
  prefecture: string;
  city: string;
  categories: string[];
  sort: SortOption;
  order: SortOrder;
  distance: number;
  lat: number | null;
  lng: number | null;
};

const toFormState = (filters: FilterState): FormState => ({
  q: filters.q,
  prefecture: filters.pref ?? "",
  city: filters.city ?? "",
  categories: [...filters.categories],
  sort: filters.sort,
  order: filters.order,
  distance: filters.distance,
  lat: filters.lat,
  lng: filters.lng,
});

const areFormStatesEqual = (a: FormState, b: FormState) =>
  a.q === b.q &&
  a.prefecture === b.prefecture &&
  a.city === b.city &&
  a.sort === b.sort &&
  a.order === b.order &&
  a.distance === b.distance &&
  a.lat === b.lat &&
  a.lng === b.lng &&
  areCategoriesEqual(a.categories, b.categories);

const areFilterStatesEqual = (a: FilterState, b: FilterState) =>
  a.q === b.q &&
  a.pref === b.pref &&
  a.city === b.city &&
  a.sort === b.sort &&
  a.order === b.order &&
  a.page === b.page &&
  a.limit === b.limit &&
  a.distance === b.distance &&
  a.lat === b.lat &&
  a.lng === b.lng &&
  areCategoriesEqual(a.categories, b.categories);

const normalizeFormState = (state: FormState): FormState => ({
  q: state.q,
  prefecture: state.prefecture.trim(),
  city: state.city.trim(),
  categories: normalizeCategories(state.categories),
  sort: state.sort,
  order: normalizeSortOrder(state.sort, state.order),
  distance: state.distance,
  lat: state.lat,
  lng: state.lng,
});

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
  order: normalizeSortOrder(form.sort, form.order),
  page: 1,
  limit: base.limit,
  distance: form.distance,
  lat: form.lat,
  lng: form.lng,
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
  updateSort: (value: SortOption, order: SortOrder) => void;
  updateDistance: (value: number) => void;
  clearFilters: () => void;
  submitSearch: () => void;
  location: LocationState;
  requestLocation: () => void;
  clearLocation: () => void;
  useFallbackLocation: () => void;
  setManualLocation: (lat: number | null, lng: number | null) => void;
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

export function useGymSearch(options: UseGymSearchOptions = {}): UseGymSearchResult {
  const { debounceMs = DEFAULT_DEBOUNCE_MS } = options;
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const searchParamsKey = searchParams.toString();

  const [appliedFilters, setAppliedFilters] = useState<FilterState>(() =>
    parseFilterState(new URLSearchParams(searchParamsKey)),
  );
  const [, startTransition] = useTransition();

  const [formState, setFormState] = useState<FormState>(() => toFormState(appliedFilters));

  const geolocationSupportedRef = useRef(
    typeof window !== "undefined" &&
      typeof window.navigator !== "undefined" &&
      "geolocation" in window.navigator,
  );
  const initialLocationRequestRef = useRef(false);
  const [locationMode, setLocationMode] = useState<LocationMode>(() => {
    if (appliedFilters.lat != null && appliedFilters.lng != null) {
      return isFallbackCoordinates(appliedFilters.lat, appliedFilters.lng) ? "fallback" : "manual";
    }
    return "off";
  });
  const [locationStatus, setLocationStatus] = useState<LocationStatus>(() =>
    appliedFilters.lat != null && appliedFilters.lng != null ? "success" : "idle",
  );
  const [locationError, setLocationError] = useState<string | null>(null);

  useEffect(() => {
    const next = parseFilterState(new URLSearchParams(searchParamsKey));
    setAppliedFilters(prev => (areFilterStatesEqual(prev, next) ? prev : next));
  }, [searchParamsKey]);

  useEffect(() => {
    const next = toFormState(appliedFilters);
    setFormState(prev => (areFormStatesEqual(prev, next) ? prev : next));
  }, [appliedFilters]);

  useEffect(() => {
    const hasLocation = appliedFilters.lat != null && appliedFilters.lng != null;
    const fallbackActive = isFallbackCoordinates(appliedFilters.lat, appliedFilters.lng);
    setLocationMode(prev => {
      if (!hasLocation) {
        return "off";
      }
      if (prev === "auto") {
        return "auto";
      }
      if (fallbackActive) {
        return "fallback";
      }
      if (prev === "fallback") {
        return "manual";
      }
      if (prev === "off") {
        return "manual";
      }
      return prev;
    });
    setLocationStatus(prev => {
      if (hasLocation) {
        if (fallbackActive) {
          return prev;
        }
        if (prev === "loading" || prev === "idle" || prev === "error") {
          return "success";
        }
        return prev;
      }
      return prev === "success" ? "idle" : prev;
    });
    if (hasLocation && !fallbackActive) {
      setLocationError(null);
    }
  }, [appliedFilters.lat, appliedFilters.lng]);

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
      setAppliedFilters(prev => (areFilterStatesEqual(prev, nextFilters) ? prev : nextFilters));

      const params = serializeFilterState(nextFilters);
      const nextQuery = params.toString();
      if (nextQuery === searchParamsKey) {
        appendModeRef.current = false;
        return;
      }

      appendModeRef.current = Boolean(options.append);
      const nextUrl = nextQuery ? `${pathname}?${nextQuery}` : pathname;
      startTransition(() => {
        router.push(nextUrl, { scroll: false });
      });
    },
    [pathname, router, searchParamsKey, setAppliedFilters, startTransition],
  );

  const scheduleApply = useCallback(
    (updater: (prev: FormState) => FormState) => {
      setFormState(prev => {
        const normalized = normalizeFormState(updater(prev));

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

  useEffect(() => {
    const hasLocation = appliedFilters.lat != null && appliedFilters.lng != null;
    const shouldApplyFallback = !hasLocation && appliedFilters.sort === "distance";
    if (!shouldApplyFallback) {
      return;
    }

    cancelPendingDebounce();
    const nextFilters: FilterState = {
      ...appliedFilters,
      lat: FALLBACK_LOCATION.lat,
      lng: FALLBACK_LOCATION.lng,
      distance: DEFAULT_DISTANCE_KM,
      page: 1,
    };
    const nextFormState = toFormState(nextFilters);
    setFormState(prev => (areFormStatesEqual(prev, nextFormState) ? prev : nextFormState));
    setLocationMode("fallback");
    setLocationStatus("success");
    setLocationError(null);
    applyFilters(nextFilters, { append: false });
  }, [appliedFilters, applyFilters, cancelPendingDebounce]);

  const updateKeyword = useCallback(
    (value: string) => scheduleApply(prev => ({ ...prev, q: value })),
    [scheduleApply],
  );

  const updatePrefecture = useCallback(
    (value: string) =>
      scheduleApply(prev => ({
        ...prev,
        prefecture: value,
        city: "",
      })),
    [scheduleApply],
  );

  const updateCity = useCallback(
    (value: string) => scheduleApply(prev => ({ ...prev, city: value })),
    [scheduleApply],
  );

  const updateCategories = useCallback(
    (values: string[]) =>
      scheduleApply(prev => ({
        ...prev,
        categories: values,
      })),
    [scheduleApply],
  );

  const updateSort = useCallback(
    (value: SortOption, order: SortOrder) =>
      scheduleApply(prev => ({
        ...prev,
        sort: value,
        order: normalizeSortOrder(value, order),
      })),
    [scheduleApply],
  );

  const updateDistance = useCallback(
    (value: number) =>
      scheduleApply(prev => ({
        ...prev,
        distance: value,
      })),
    [scheduleApply],
  );

  const applyLocation = useCallback(
    (lat: number | null, lng: number | null, mode: LocationMode) => {
      cancelPendingDebounce();
      setFormState(prev => {
        const hasLocation = lat != null && lng != null;
        const nextDistance = hasLocation ? prev.distance : DEFAULT_DISTANCE_KM;
        const shouldResetSort = !hasLocation && prev.sort === "distance";
        const nextSort = shouldResetSort ? DEFAULT_FILTER_STATE.sort : prev.sort;
        const nextOrder = shouldResetSort
          ? DEFAULT_FILTER_STATE.order
          : normalizeSortOrder(nextSort, prev.order);
        const next: FormState = {
          ...prev,
          lat,
          lng,
          distance: nextDistance,
          sort: nextSort,
          order: nextOrder,
        };
        applyFilters(
          buildFilterStateFromForm(next, appliedFilters, {
            lat,
            lng,
            distance: nextDistance,
          }),
        );
        return next;
      });
      if (lat != null && lng != null) {
        setLocationMode(mode);
        setLocationStatus("success");
        setLocationError(null);
      } else {
        setLocationMode("off");
        setLocationStatus("idle");
        setLocationError(null);
      }
    },
    [appliedFilters, applyFilters, cancelPendingDebounce],
  );

  const applyFallbackLocation = useCallback(
    (message: string | null = null) => {
      applyLocation(FALLBACK_LOCATION.lat, FALLBACK_LOCATION.lng, "fallback");
      if (message) {
        setLocationStatus("error");
        setLocationError(message);
      } else {
        setLocationStatus("success");
        setLocationError(null);
      }
    },
    [applyLocation],
  );

  const handleGeolocationError = useCallback(
    (error: GeolocationPositionError | null, overrideMessage?: string) => {
      if (overrideMessage) {
        applyFallbackLocation(overrideMessage);
        return;
      }
      const code = error?.code;
      const PERM = error?.PERMISSION_DENIED ?? 1;
      const UNAV = error?.POSITION_UNAVAILABLE ?? 2;
      const TOUT = error?.TIMEOUT ?? 3;
      if (code === PERM) {
        applyFallbackLocation(LOCATION_PERMISSION_DENIED_MESSAGE);
        return;
      }
      if (code === UNAV) {
        applyFallbackLocation(LOCATION_UNAVAILABLE_MESSAGE);
        return;
      }
      if (code === TOUT) {
        applyFallbackLocation(LOCATION_TIMEOUT_MESSAGE);
        return;
      }
      applyFallbackLocation(LOCATION_UNAVAILABLE_MESSAGE);
    },
    [applyFallbackLocation],
  );

  const requestLocation = useCallback(() => {
    if (typeof window === "undefined" || !geolocationSupportedRef.current) {
      handleGeolocationError(null, LOCATION_UNSUPPORTED_MESSAGE);
      return;
    }
    setLocationMode("auto");
    setLocationStatus("loading");
    setLocationError(null);
    window.navigator.geolocation.getCurrentPosition(
      position => {
        applyLocation(
          clampLatitude(position.coords.latitude),
          clampLongitude(position.coords.longitude),
          "auto",
        );
      },
      error => {
        handleGeolocationError(error);
      },
      { enableHighAccuracy: false, maximumAge: 300000, timeout: 10000 },
    );
  }, [applyLocation, handleGeolocationError]);

  const setManualLocation = useCallback(
    (lat: number | null, lng: number | null) => {
      if (lat == null || lng == null) {
        applyLocation(null, null, "off");
        return;
      }
      applyLocation(clampLatitude(lat), clampLongitude(lng), "manual");
    },
    [applyLocation],
  );

  const useFallbackLocation = useCallback(() => {
    applyFallbackLocation(null);
  }, [applyFallbackLocation]);

  const clearLocation = useCallback(() => {
    applyLocation(null, null, "off");
  }, [applyLocation]);

  const clearFilters = useCallback(() => {
    cancelPendingDebounce();
    const hasLocation = formState.lat != null && formState.lng != null;
    const resetFilters: FilterState = {
      ...DEFAULT_FILTER_STATE,
      limit: appliedFilters.limit,
      lat: hasLocation ? formState.lat : null,
      lng: hasLocation ? formState.lng : null,
      distance: DEFAULT_DISTANCE_KM,
    };
    setFormState(toFormState(resetFilters));
    applyFilters(resetFilters);
    if (hasLocation) {
      setLocationMode(mode => (mode === "off" ? "manual" : mode));
      setLocationStatus("success");
      setLocationError(null);
    } else {
      setLocationMode("off");
      setLocationStatus(status => (status === "success" ? "idle" : status));
    }
  }, [appliedFilters.limit, applyFilters, cancelPendingDebounce, formState.lat, formState.lng]);

  useEffect(() => {
    if (initialLocationRequestRef.current) {
      return;
    }
    if (typeof window === "undefined") {
      return;
    }
    const hasQueryLocation = appliedFilters.lat != null && appliedFilters.lng != null;
    if (hasQueryLocation) {
      initialLocationRequestRef.current = true;
      return;
    }
    initialLocationRequestRef.current = true;
    requestLocation();
  }, [appliedFilters.lat, appliedFilters.lng, requestLocation]);

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
    page: 1,
    perPage: DEFAULT_LIMIT,
    hasNext: false,
    hasPrev: false,
    hasMore: false,
    pageToken: null,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshIndex, setRefreshIndex] = useState(0);

  const submitSearch = useCallback(() => {
    cancelPendingDebounce();
    const normalized = normalizeFormState(formState);
    setFormState(normalized);

    const currentAppliedForm = toFormState(appliedFilters);
    if (areFormStatesEqual(currentAppliedForm, normalized)) {
      setRefreshIndex(value => value + 1);
      return;
    }

    applyFilters(buildFilterStateFromForm(normalized, appliedFilters));
  }, [appliedFilters, applyFilters, cancelPendingDebounce, formState]);

  const retry = useCallback(() => setRefreshIndex(value => value + 1), []);

  const loadNextPage = useCallback(() => {
    if (isLoading || !meta.hasNext) {
      return;
    }
    setPage(appliedFilters.page + 1, { append: true });
  }, [appliedFilters.page, isLoading, meta.hasNext, setPage]);

  useEffect(() => {
    const missingLocationForDistance =
      appliedFilters.sort === "distance" &&
      (appliedFilters.lat == null || appliedFilters.lng == null);
    if (missingLocationForDistance) {
      appendModeRef.current = false;
      setIsLoading(false);
      setError(null);
      return;
    }

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
        order: appliedFilters.order,
        page: appliedFilters.page,
        limit: appliedFilters.limit,
        perPage: appliedFilters.limit,
        ...(appliedFilters.lat != null && appliedFilters.lng != null
          ? {
              lat: appliedFilters.lat,
              lng: appliedFilters.lng,
              radiusKm: appliedFilters.distance,
            }
          : {}),
      },
      { signal: controller.signal },
    )
      .then(response => {
        if (!active) {
          return;
        }
        setItems(previous => {
          if (!shouldAppend) {
            return response.items;
          }

          if (response.items.length === 0) {
            return previous;
          }

          const seen = new Set(previous.map(item => item.id));
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
      .catch(err => {
        if (!active) {
          return;
        }
        if (err instanceof DOMException && err.name === "AbortError") {
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
  const [equipmentCategories, setEquipmentCategories] = useState<EquipmentCategoryOption[]>([]);
  const [isMetaLoading, setIsMetaLoading] = useState(false);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [metaReloadIndex, setMetaReloadIndex] = useState(0);

  const reloadMeta = useCallback(() => setMetaReloadIndex(value => value + 1), []);

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
      .catch(err => {
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
    setCityReloadIndex(value => value + 1);
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
      .then(data => {
        if (!active) {
          return;
        }
        citiesCacheRef.current.set(prefSlug, data);
        setCities(data);
      })
      .catch(err => {
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

  const location: LocationState = useMemo(() => {
    const fallbackActive = isFallbackCoordinates(formState.lat, formState.lng);
    return {
      lat: formState.lat,
      lng: formState.lng,
      mode: locationMode,
      status: locationStatus,
      error: locationError,
      isSupported: geolocationSupportedRef.current,
      isFallback: fallbackActive,
      fallbackLabel: fallbackActive ? FALLBACK_LOCATION.label : null,
    };
  }, [formState.lat, formState.lng, locationMode, locationStatus, locationError]);

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
    submitSearch,
    location,
    requestLocation,
    clearLocation,
    useFallbackLocation,
    setManualLocation,
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
