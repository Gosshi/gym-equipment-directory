"use client";

import { useCallback, useEffect, useMemo, useRef, useState, useTransition } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

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
  filterStateToQueryString,
  normalizeSortOrder,
  clampLatitude,
  clampLongitude,
} from "@/lib/searchParams";
import { searchGyms } from "@/services/gyms";
import { getCities, getEquipmentCategories, getPrefectures } from "@/services/meta";
import type { GymSearchMeta, GymSearchResponse, GymSummary } from "@/types/gym";
import type { CityOption, EquipmentCategoryOption, PrefectureOption } from "@/types/meta";
import { useSearchStore, areFilterStatesEqual, type NavigationSource } from "@/store/searchStore";

const DEFAULT_DEBOUNCE_MS = 300;

const EMPTY_META: GymSearchMeta = {
  total: 0,
  page: 1,
  perPage: DEFAULT_LIMIT,
  hasNext: false,
  hasPrev: false,
  hasMore: false,
  pageToken: null,
};

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
  hasResolvedSupport: boolean;
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

  const filters = useSearchStore(state => state.filters);
  const setFilters = useSearchStore(state => state.setFilters);
  const updateFilters = useSearchStore(state => state.updateFilters);
  const currentQueryString = useSearchStore(state => state.queryString);
  const setNavigationSource = useSearchStore(state => state.setNavigationSource);
  const saveScrollPosition = useSearchStore(state => state.saveScrollPosition);
  const [, startTransition] = useTransition();

  const [formState, setFormState] = useState<FormState>(() => toFormState(filters));

  const pendingNavigationRef = useRef<NavigationSource | null>(null);
  const pendingQueryRef = useRef<string | null>(null);
  const initializedRef = useRef(false);

  const geolocationSupportedRef = useRef(
    typeof window !== "undefined" &&
      typeof window.navigator !== "undefined" &&
      "geolocation" in window.navigator,
  );
  const [isGeolocationSupported, setIsGeolocationSupported] = useState(
    geolocationSupportedRef.current,
  );
  const [hasResolvedGeolocationSupport, setHasResolvedGeolocationSupport] = useState(false);
  const initialLocationRequestRef = useRef(false);
  const [locationMode, setLocationMode] = useState<LocationMode>(() => {
    if (filters.lat != null && filters.lng != null) {
      return isFallbackCoordinates(filters.lat, filters.lng) ? "fallback" : "manual";
    }
    return "off";
  });
  const [locationStatus, setLocationStatus] = useState<LocationStatus>(() =>
    filters.lat != null && filters.lng != null ? "success" : "idle",
  );
  const [locationError, setLocationError] = useState<string | null>(null);

  const detectGeolocationSupport = useCallback(() => {
    if (typeof window === "undefined" || typeof window.navigator === "undefined") {
      geolocationSupportedRef.current = false;
      setIsGeolocationSupported(false);
      setHasResolvedGeolocationSupport(true);
      return false;
    }
    const geolocation = window.navigator.geolocation;
    const supported =
      typeof geolocation === "object" &&
      geolocation !== null &&
      typeof geolocation.getCurrentPosition === "function";
    geolocationSupportedRef.current = supported;
    setIsGeolocationSupported(supported);
    setHasResolvedGeolocationSupport(true);
    return supported;
  }, []);

  useEffect(() => {
    detectGeolocationSupport();
  }, [detectGeolocationSupport]);

  useEffect(() => {
    const params = new URLSearchParams(searchParamsKey);
    const next = parseFilterState(params);
    const nextQuery = filterStateToQueryString(next);

    let source: NavigationSource = initializedRef.current ? "pop" : "initial";
    if (pendingNavigationRef.current === "push" && pendingQueryRef.current === nextQuery) {
      source = "push";
    }

    pendingNavigationRef.current = null;
    pendingQueryRef.current = null;
    initializedRef.current = true;

    setFilters(next, { queryString: nextQuery });
    setNavigationSource(source);
  }, [searchParamsKey, setFilters, setNavigationSource]);

  useEffect(() => {
    const next = toFormState(filters);
    setFormState(prev => (areFormStatesEqual(prev, next) ? prev : next));
  }, [filters]);

  useEffect(() => {
    const hasLocation = filters.lat != null && filters.lng != null;
    const fallbackActive = isFallbackCoordinates(filters.lat, filters.lng);
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
  }, [filters.lat, filters.lng]);

  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  const cancelPendingDebounce = useCallback(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
  }, []);

  useEffect(() => cancelPendingDebounce, [cancelPendingDebounce]);

  const applyFilters = useCallback(
    (nextFilters: FilterState, options: { force?: boolean } = {}) => {
      const params = serializeFilterState(nextFilters);
      const nextQuery = params.toString();

      if (!options.force && areFilterStatesEqual(filters, nextFilters)) {
        return;
      }

      if (typeof window !== "undefined") {
        saveScrollPosition(currentQueryString, window.scrollY);
      }

      pendingNavigationRef.current = "push";
      pendingQueryRef.current = nextQuery;
      setFilters(nextFilters, { queryString: nextQuery, force: true });
      setNavigationSource("push");

      const nextUrl = nextQuery ? `${pathname}?${nextQuery}` : pathname;
      startTransition(() => {
        router.replace(nextUrl, { scroll: false });
      });
    },
    [
      currentQueryString,
      filters,
      pathname,
      router,
      saveScrollPosition,
      setFilters,
      setNavigationSource,
      startTransition,
    ],
  );

  const queueFilters = useCallback(
    (
      nextFormState: FormState,
      options: {
        overrides?: Partial<FilterState>;
        debounceMs?: number;
      } = {},
    ) => {
      cancelPendingDebounce();
      const delay = options.debounceMs ?? debounceMs;
      const run = () => {
        applyFilters(buildFilterStateFromForm(nextFormState, filters, options.overrides));
      };

      if (delay <= 0) {
        run();
      } else {
        debounceRef.current = setTimeout(run, delay);
      }
    },
    [applyFilters, cancelPendingDebounce, debounceMs, filters],
  );

  const scheduleApply = useCallback(
    (updater: (prev: FormState) => FormState, options?: { debounceMs?: number }) => {
      setFormState(prev => {
        const normalized = normalizeFormState(updater(prev));

        if (areFormStatesEqual(prev, normalized)) {
          return prev;
        }

        queueFilters(normalized, { debounceMs: options?.debounceMs });

        return normalized;
      });
    },
    [queueFilters],
  );

  useEffect(() => {
    const hasLocation = filters.lat != null && filters.lng != null;
    const shouldApplyFallback = !hasLocation && filters.sort === "distance";
    if (!shouldApplyFallback) {
      return;
    }

    const nextFilters: FilterState = {
      ...filters,
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
    applyFilters(nextFilters, { force: true });
  }, [applyFilters, filters]);

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
      setFormState(prev => {
        const hasLocation = lat != null && lng != null;
        const nextDistance = hasLocation ? prev.distance : DEFAULT_DISTANCE_KM;
        const shouldResetSort = !hasLocation && prev.sort === "distance";
        const nextSort = shouldResetSort ? DEFAULT_FILTER_STATE.sort : prev.sort;
        const nextOrder = shouldResetSort
          ? DEFAULT_FILTER_STATE.order
          : normalizeSortOrder(nextSort, prev.order);
        const next = normalizeFormState({
          ...prev,
          lat,
          lng,
          distance: nextDistance,
          sort: nextSort,
          order: nextOrder,
        });

        if (!areFormStatesEqual(prev, next)) {
          const nextFilters = buildFilterStateFromForm(next, filters, {
            lat,
            lng,
            distance: nextDistance,
          });
          setFilters(nextFilters, {
            queryString: filterStateToQueryString(nextFilters),
            force: true,
          });
          queueFilters(next, {
            overrides: { lat, lng, distance: nextDistance },
            debounceMs: Math.min(150, debounceMs),
          });
        }

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
    [debounceMs, filters, queueFilters, setFilters],
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
    const supported = detectGeolocationSupport();
    if (!supported) {
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
  }, [applyLocation, detectGeolocationSupport, handleGeolocationError]);

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
      limit: filters.limit,
      lat: hasLocation ? formState.lat : null,
      lng: hasLocation ? formState.lng : null,
      distance: DEFAULT_DISTANCE_KM,
    };
    setFormState(toFormState(resetFilters));
    applyFilters(resetFilters, { force: true });
    if (hasLocation) {
      setLocationMode(mode => (mode === "off" ? "manual" : mode));
      setLocationStatus("success");
      setLocationError(null);
    } else {
      setLocationMode("off");
      setLocationStatus(status => (status === "success" ? "idle" : status));
    }
  }, [applyFilters, cancelPendingDebounce, filters.limit, formState.lat, formState.lng]);

  useEffect(() => {
    if (initialLocationRequestRef.current) {
      return;
    }
    if (typeof window === "undefined") {
      return;
    }
    const hasQueryLocation = filters.lat != null && filters.lng != null;
    if (hasQueryLocation) {
      initialLocationRequestRef.current = true;
      return;
    }
    if (!hasResolvedGeolocationSupport) {
      return;
    }
    if (!isGeolocationSupported) {
      handleGeolocationError(null, LOCATION_UNSUPPORTED_MESSAGE);
      initialLocationRequestRef.current = true;
      return;
    }
    initialLocationRequestRef.current = true;
    requestLocation();
  }, [
    filters.lat,
    filters.lng,
    handleGeolocationError,
    hasResolvedGeolocationSupport,
    isGeolocationSupported,
    requestLocation,
  ]);

  const setPage = useCallback(
    (page: number) => {
      const nextPage = Number.isFinite(page) && page > 0 ? Math.trunc(page) : 1;
      cancelPendingDebounce();
      applyFilters(
        {
          ...filters,
          page: nextPage,
        },
        { force: true },
      );
    },
    [applyFilters, cancelPendingDebounce, filters],
  );

  const setLimit = useCallback(
    (value: number) => {
      const parsed = Number.isFinite(value) ? Math.trunc(value) : DEFAULT_LIMIT;
      const clamped = Math.min(Math.max(parsed, 1), MAX_LIMIT);
      cancelPendingDebounce();
      applyFilters(
        {
          ...filters,
          limit: clamped,
          page: 1,
        },
        { force: true },
      );
    },
    [applyFilters, cancelPendingDebounce, filters],
  );

  const [refreshIndex, setRefreshIndex] = useState(0);

  const submitSearch = useCallback(() => {
    cancelPendingDebounce();
    const normalized = normalizeFormState(formState);
    setFormState(normalized);

    const currentAppliedForm = toFormState(filters);
    if (areFormStatesEqual(currentAppliedForm, normalized)) {
      setRefreshIndex(value => value + 1);
      return;
    }

    applyFilters(buildFilterStateFromForm(normalized, filters));
  }, [applyFilters, cancelPendingDebounce, filters, formState]);

  const retry = useCallback(() => setRefreshIndex(value => value + 1), []);

  const missingLocationForDistance =
    filters.sort === "distance" && (filters.lat == null || filters.lng == null);

  const filterQueryString = useMemo(() => filterStateToQueryString(filters), [filters]);

  const gymsQuery = useQuery<GymSearchResponse>({
    queryKey: ["gyms", filterQueryString, refreshIndex],
    queryFn: ({ signal }) =>
      searchGyms(
        {
          q: filters.q || undefined,
          prefecture: filters.pref ?? undefined,
          city: filters.city ?? undefined,
          categories: filters.categories,
          sort: filters.sort,
          order: filters.order,
          page: filters.page,
          limit: filters.limit,
          perPage: filters.limit,
          ...(filters.lat != null && filters.lng != null
            ? {
                lat: filters.lat,
                lng: filters.lng,
                radiusKm: filters.distance,
              }
            : {}),
        },
        { signal },
      ),
    enabled: !missingLocationForDistance,
    keepPreviousData: true,
  });

  const queryData = gymsQuery.data;
  const queryError = gymsQuery.error;

  const items: GymSummary[] = !missingLocationForDistance ? (queryData?.items ?? []) : [];

  let meta: GymSearchMeta = {
    ...EMPTY_META,
    page: filters.page,
    perPage: filters.limit,
  };

  if (!missingLocationForDistance && queryData?.meta) {
    const serverMeta = queryData.meta;
    const resolvedPage =
      Number.isInteger(serverMeta.page) && (serverMeta.page ?? 0) > 0
        ? serverMeta.page
        : filters.page;
    const resolvedPerPage =
      Number.isInteger(serverMeta.perPage) && (serverMeta.perPage ?? 0) > 0
        ? serverMeta.perPage
        : filters.limit;
    meta = {
      ...serverMeta,
      page: resolvedPage,
      perPage: resolvedPerPage,
    };
  }

  const hasLoadedOnce = !missingLocationForDistance && Boolean(queryData);
  const isLoading = !missingLocationForDistance && gymsQuery.isFetching;
  const isInitialLoading = isLoading && !hasLoadedOnce;

  let error: string | null = null;
  if (!missingLocationForDistance && gymsQuery.isError && queryError) {
    if (queryError instanceof ApiError) {
      error = queryError.message || "ジムの取得に失敗しました";
    } else if (queryError instanceof Error) {
      error = queryError.message;
    } else {
      error = "ジムの取得に失敗しました";
    }
  }

  const serverPage = queryData?.meta?.page;
  useEffect(() => {
    if (missingLocationForDistance) {
      return;
    }
    const resolvedServerPage =
      Number.isInteger(serverPage) && (serverPage ?? 0) > 0 ? serverPage : null;
    if (resolvedServerPage != null && resolvedServerPage !== filters.page) {
      setPage(resolvedServerPage);
    }
  }, [filters.page, missingLocationForDistance, serverPage, setPage]);

  const loadNextPage = useCallback(() => {
    if (isLoading || !meta.hasNext) {
      return;
    }
    setPage(filters.page + 1);
  }, [filters.page, isLoading, meta.hasNext, setPage]);

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

  useEffect(() => {
    return () => {
      if (typeof window === "undefined") {
        return;
      }
      saveScrollPosition(currentQueryString, window.scrollY);
    };
  }, [currentQueryString, saveScrollPosition]);

  const location: LocationState = useMemo(() => {
    const fallbackActive = isFallbackCoordinates(formState.lat, formState.lng);
    return {
      lat: formState.lat,
      lng: formState.lng,
      mode: locationMode,
      status: locationStatus,
      error: locationError,
      isSupported: isGeolocationSupported,
      hasResolvedSupport: hasResolvedGeolocationSupport,
      isFallback: fallbackActive,
      fallbackLabel: fallbackActive ? FALLBACK_LOCATION.label : null,
    };
  }, [
    formState.lat,
    formState.lng,
    hasResolvedGeolocationSupport,
    isGeolocationSupported,
    locationMode,
    locationStatus,
    locationError,
  ]);

  return {
    formState,
    appliedFilters: filters,
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
    page: filters.page,
    limit: filters.limit,
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
