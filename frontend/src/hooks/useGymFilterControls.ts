"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiError } from "@/lib/apiClient";
import {
  DEFAULT_DISTANCE_KM,
  DEFAULT_ORDER,
  DEFAULT_SORT,
  type SortOption,
  type SortOrder,
} from "@/lib/searchParams";
import { getCities, getEquipmentCategories, getPrefectures } from "@/services/meta";
import type { CityOption, EquipmentCategoryOption, PrefectureOption } from "@/types/meta";
import {
  FALLBACK_LOCATION,
  type LocationMode,
  type LocationState,
  type LocationStatus,
} from "@/hooks/useGymSearch";
import { useGymSearchStore } from "@/store/searchStore";

const LOCATION_PERMISSION_DENIED_MESSAGE =
  "位置情報が許可されていません。任意の地点を選ぶか、許可してください。";
const LOCATION_UNAVAILABLE_MESSAGE =
  "位置情報を取得できませんでした。デフォルト地点を利用しています。";
const LOCATION_TIMEOUT_MESSAGE =
  "位置情報の取得がタイムアウトしました。デフォルト地点を利用しています。";
const LOCATION_UNSUPPORTED_MESSAGE =
  "この環境では位置情報を取得できません。緯度・経度を手入力するか、デフォルト地点を利用してください。";

const FALLBACK_COORDINATE_EPSILON = 0.000005;

const isFallbackCoordinates = (lat: number | null, lng: number | null) =>
  lat != null &&
  lng != null &&
  Math.abs(lat - FALLBACK_LOCATION.lat) < FALLBACK_COORDINATE_EPSILON &&
  Math.abs(lng - FALLBACK_LOCATION.lng) < FALLBACK_COORDINATE_EPSILON;

const DEFAULT_LOCATION_MODE: LocationMode = isFallbackCoordinates(
  FALLBACK_LOCATION.lat,
  FALLBACK_LOCATION.lng,
)
  ? "fallback"
  : "manual";

interface GymFilterControls {
  state: {
    q: string;
    prefecture: string;
    city: string;
    categories: string[];
    sort: SortOption;
    order: SortOrder;
    distance: number;
  };
  location: LocationState;
  prefectures: PrefectureOption[];
  cities: CityOption[];
  categories: EquipmentCategoryOption[];
  isMetaLoading: boolean;
  isCityLoading: boolean;
  metaError: string | null;
  cityError: string | null;
  onKeywordChange: (value: string) => void;
  onPrefectureChange: (value: string) => void;
  onCityChange: (value: string) => void;
  onCategoriesChange: (values: string[]) => void;
  onSortChange: (sort: string, order: string) => void;
  onDistanceChange: (value: number) => void;
  onClear: () => void;
  onRequestLocation: () => void;
  onUseFallbackLocation: () => void;
  onClearLocation: () => void;
  onManualLocationChange: (lat: number | null, lng: number | null) => void;
  onReloadMeta: () => void;
  onReloadCities: () => void;
}

export function useGymFilterControls(): GymFilterControls {
  const {
    q,
    prefecture,
    city,
    categories: selectedCategories,
    sort,
    order,
    radiusKm,
    lat,
    lng,
  } = useGymSearchStore(state => ({
    q: state.q,
    prefecture: state.prefecture,
    city: state.city,
    categories: state.categories,
    sort: state.sort,
    order: state.order,
    radiusKm: state.radiusKm,
    lat: state.lat,
    lng: state.lng,
  }));

  const setQuery = useGymSearchStore(state => state.setQuery);
  const setPrefecture = useGymSearchStore(state => state.setPrefecture);
  const setCity = useGymSearchStore(state => state.setCity);
  const setCategories = useGymSearchStore(state => state.setCategories);
  const setSort = useGymSearchStore(state => state.setSort);
  const setDistance = useGymSearchStore(state => state.setDistance);
  const setLocation = useGymSearchStore(state => state.setLocation);
  const resetFilters = useGymSearchStore(state => state.resetFilters);

  const [prefectures, setPrefectures] = useState<PrefectureOption[]>([]);
  const [categoryOptions, setCategoryOptions] = useState<EquipmentCategoryOption[]>([]);
  const [cities, setCities] = useState<CityOption[]>([]);

  const [isMetaLoading, setIsMetaLoading] = useState(true);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [metaReloadIndex, setMetaReloadIndex] = useState(0);

  const [isCityLoading, setIsCityLoading] = useState(false);
  const [cityError, setCityError] = useState<string | null>(null);
  const [cityReloadIndex, setCityReloadIndex] = useState(0);

  const citiesCacheRef = useRef(new Map<string, CityOption[]>());

  useEffect(() => {
    let active = true;
    setIsMetaLoading(true);
    setMetaError(null);

    Promise.all([getPrefectures(), getEquipmentCategories()])
      .then(([prefData, categoryData]) => {
        if (!active) {
          return;
        }
        setPrefectures(prefData);
        setCategoryOptions(categoryData);
      })
      .catch(error => {
        if (!active) {
          return;
        }
        if (error instanceof ApiError) {
          setMetaError(error.message || "検索条件の取得に失敗しました");
        } else if (error instanceof Error) {
          setMetaError(error.message);
        } else {
          setMetaError("検索条件の取得に失敗しました");
        }
      })
      .finally(() => {
        if (active) {
          setIsMetaLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [metaReloadIndex]);

  useEffect(() => {
    const prefSlug = prefecture.trim();
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
      .then(cityData => {
        if (!active) {
          return;
        }
        citiesCacheRef.current.set(prefSlug, cityData);
        setCities(cityData);
      })
      .catch(error => {
        if (!active) {
          return;
        }
        if (error instanceof ApiError) {
          setCityError(error.message || "市区町村の取得に失敗しました");
        } else if (error instanceof Error) {
          setCityError(error.message);
        } else {
          setCityError("市区町村の取得に失敗しました");
        }
      })
      .finally(() => {
        if (active) {
          setIsCityLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [prefecture, cityReloadIndex]);

  const [isGeolocationSupported, setIsGeolocationSupported] = useState(false);
  const [hasResolvedGeolocationSupport, setHasResolvedGeolocationSupport] = useState(false);
  const [locationMode, setLocationMode] = useState<LocationMode>(() =>
    lat != null && lng != null ? (isFallbackCoordinates(lat, lng) ? "fallback" : "manual") : "off",
  );
  const [locationStatus, setLocationStatus] = useState<LocationStatus>(() =>
    lat != null && lng != null ? "success" : "idle",
  );
  const [locationError, setLocationError] = useState<string | null>(null);

  const expectedLocationRef = useRef<{ lat: number | null; lng: number | null } | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const supported = typeof navigator !== "undefined" && Boolean(navigator.geolocation);
    setIsGeolocationSupported(supported);
    setHasResolvedGeolocationSupport(true);
  }, []);

  const applyLocation = useCallback(
    (
      nextLat: number | null,
      nextLng: number | null,
      mode: LocationMode,
      options: { status?: LocationStatus; error?: string | null } = {},
    ) => {
      const hasLocation = nextLat != null && nextLng != null;
      const status = options.status ?? (hasLocation ? "success" : "idle");
      const error = options.error ?? null;
      expectedLocationRef.current = { lat: nextLat, lng: nextLng };
      setLocation({ lat: nextLat, lng: nextLng });
      if (!hasLocation && sort === "distance") {
        setSort(DEFAULT_SORT, DEFAULT_ORDER);
      }
      if (!hasLocation) {
        setDistance(DEFAULT_DISTANCE_KM);
      }
      setLocationMode(mode);
      setLocationStatus(status);
      setLocationError(error);
    },
    [setDistance, setLocation, setSort, sort],
  );

  const handleGeolocationError = useCallback(
    (error: GeolocationPositionError | null, overrideMessage?: string) => {
      const message = overrideMessage
        ? overrideMessage
        : (() => {
            const code = error?.code;
            const PERM = error?.PERMISSION_DENIED ?? 1;
            const UNAV = error?.POSITION_UNAVAILABLE ?? 2;
            const TOUT = error?.TIMEOUT ?? 3;
            if (code === PERM) {
              return LOCATION_PERMISSION_DENIED_MESSAGE;
            }
            if (code === UNAV) {
              return LOCATION_UNAVAILABLE_MESSAGE;
            }
            if (code === TOUT) {
              return LOCATION_TIMEOUT_MESSAGE;
            }
            return LOCATION_UNAVAILABLE_MESSAGE;
          })();
      applyLocation(FALLBACK_LOCATION.lat, FALLBACK_LOCATION.lng, DEFAULT_LOCATION_MODE, {
        status: "error",
        error: message,
      });
    },
    [applyLocation],
  );

  const requestLocation = useCallback(() => {
    if (!hasResolvedGeolocationSupport) {
      return;
    }
    if (!isGeolocationSupported) {
      handleGeolocationError(null, LOCATION_UNSUPPORTED_MESSAGE);
      return;
    }

    setLocationMode("auto");
    setLocationStatus("loading");
    setLocationError(null);

    navigator.geolocation.getCurrentPosition(
      position => {
        applyLocation(position.coords.latitude, position.coords.longitude, "auto", {
          status: "success",
          error: null,
        });
      },
      error => {
        handleGeolocationError(error);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 30000,
      },
    );
  }, [
    applyLocation,
    handleGeolocationError,
    hasResolvedGeolocationSupport,
    isGeolocationSupported,
  ]);

  const useFallbackLocation = useCallback(() => {
    applyLocation(FALLBACK_LOCATION.lat, FALLBACK_LOCATION.lng, DEFAULT_LOCATION_MODE, {
      status: "success",
      error: null,
    });
  }, [applyLocation]);

  const clearLocation = useCallback(() => {
    applyLocation(null, null, "off", { status: "idle", error: null });
  }, [applyLocation]);

  const setManualLocation = useCallback(
    (manualLat: number | null, manualLng: number | null) => {
      if (manualLat == null || manualLng == null) {
        clearLocation();
        return;
      }
      applyLocation(manualLat, manualLng, "manual", { status: "success", error: null });
    },
    [applyLocation, clearLocation],
  );

  useEffect(() => {
    const expected = expectedLocationRef.current;
    if (expected && expected.lat === lat && expected.lng === lng) {
      expectedLocationRef.current = null;
      return;
    }

    if (lat == null || lng == null) {
      setLocationMode("off");
      if (locationStatus !== "loading") {
        setLocationStatus("idle");
        setLocationError(null);
      }
      return;
    }

    if (isFallbackCoordinates(lat, lng)) {
      setLocationMode(DEFAULT_LOCATION_MODE);
      if (locationStatus !== "loading") {
        setLocationStatus("success");
        setLocationError(null);
      }
      return;
    }

    setLocationMode(current => (current === "auto" ? current : "manual"));
    if (locationStatus !== "loading") {
      setLocationStatus("success");
      setLocationError(null);
    }
  }, [lat, lng, locationStatus]);

  useEffect(() => {
    if ((lat == null || lng == null) && sort === "distance") {
      setSort(DEFAULT_SORT, DEFAULT_ORDER);
    }
  }, [lat, lng, setSort, sort]);

  const handleClearFilters = useCallback(() => {
    expectedLocationRef.current = {
      lat: FALLBACK_LOCATION.lat,
      lng: FALLBACK_LOCATION.lng,
    };
    resetFilters();
    setLocationMode(DEFAULT_LOCATION_MODE);
    setLocationStatus("success");
    setLocationError(null);
  }, [resetFilters]);

  const handleReloadMeta = useCallback(() => setMetaReloadIndex(value => value + 1), []);
  const handleReloadCities = useCallback(() => {
    const prefSlug = prefecture.trim();
    if (prefSlug) {
      citiesCacheRef.current.delete(prefSlug);
    }
    setCityReloadIndex(value => value + 1);
  }, [prefecture]);

  const handleSortChange = useCallback(
    (nextSort: string, nextOrder: string) => {
      const sortValue = nextSort as SortOption;
      const orderValue = nextOrder ? (nextOrder as SortOrder) : DEFAULT_ORDER;
      setSort(sortValue, orderValue);
    },
    [setSort],
  );

  const fallbackActive = isFallbackCoordinates(lat, lng);
  const locationState: LocationState = useMemo(
    () => ({
      lat,
      lng,
      mode: locationMode,
      status: locationStatus,
      error: locationError,
      isSupported: isGeolocationSupported,
      hasResolvedSupport: hasResolvedGeolocationSupport,
      isFallback: fallbackActive,
      fallbackLabel: fallbackActive ? FALLBACK_LOCATION.label : null,
    }),
    [
      lat,
      lng,
      locationMode,
      locationStatus,
      locationError,
      isGeolocationSupported,
      hasResolvedGeolocationSupport,
      fallbackActive,
    ],
  );

  return {
    state: {
      q,
      prefecture,
      city,
      categories: selectedCategories,
      sort,
      order,
      distance: radiusKm,
    },
    location: locationState,
    prefectures,
    cities,
    categories: categoryOptions,
    isMetaLoading,
    isCityLoading,
    metaError,
    cityError,
    onKeywordChange: setQuery,
    onPrefectureChange: value => setPrefecture(value),
    onCityChange: value => setCity(value),
    onCategoriesChange: values => setCategories(values),
    onSortChange: handleSortChange,
    onDistanceChange: value => setDistance(value),
    onClear: handleClearFilters,
    onRequestLocation: requestLocation,
    onUseFallbackLocation: useFallbackLocation,
    onClearLocation: clearLocation,
    onManualLocationChange: (manualLat, manualLng) => setManualLocation(manualLat, manualLng),
    onReloadMeta: handleReloadMeta,
    onReloadCities: handleReloadCities,
  };
}
