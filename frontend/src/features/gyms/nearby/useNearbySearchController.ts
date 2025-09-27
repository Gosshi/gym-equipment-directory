"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  clampLatitude,
  clampLongitude,
  DISTANCE_STEP_KM,
  MAX_DISTANCE_KM,
  MIN_DISTANCE_KM,
} from "@/lib/searchParams";
import { planNavigation, type HistoryNavigationMode } from "@/lib/urlNavigation";

const DEFAULT_RADIUS_KM = 3;

const clampRadius = (value: number) => {
  if (!Number.isFinite(value)) {
    return DEFAULT_RADIUS_KM;
  }
  const rounded = Math.round(value);
  return Math.min(Math.max(rounded, MIN_DISTANCE_KM), MAX_DISTANCE_KM);
};

const parseRadius = (raw: string | null): number | null => {
  if (raw == null) {
    return null;
  }
  const parsed = Number.parseFloat(raw);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return clampRadius(parsed);
};

const parsePage = (raw: string | null): number => {
  if (!raw) {
    return 1;
  }
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return 1;
  }
  return parsed;
};

const GEO_PERMISSION_DENIED_MESSAGE =
  "位置情報が許可されていません。手動入力や地図から地点を選択してください。";
const GEO_UNAVAILABLE_MESSAGE =
  "現在地を取得できませんでした。通信環境をご確認いただくか、手動で地点を指定してください。";
const GEO_TIMEOUT_MESSAGE =
  "位置情報の取得がタイムアウトしました。再度お試しいただくか、手動で地点を指定してください。";
const GEO_UNSUPPORTED_MESSAGE =
  "この環境では位置情報を取得できません。緯度・経度を入力してください。";

type NearbySearchParams = {
  get(name: string): string | null;
};

const parseNearbyState = (
  params: NearbySearchParams,
  defaults: { lat: number; lng: number; radiusKm: number },
): NearbyQueryState => {
  const latRaw = params.get("lat");
  const lngRaw = params.get("lng");
  const lat = latRaw == null ? defaults.lat : clampLatitude(Number.parseFloat(latRaw));
  const lng = lngRaw == null ? defaults.lng : clampLongitude(Number.parseFloat(lngRaw));

  const radiusParam = params.get("radiusKm") ?? params.get("radius_km") ?? params.get("radius");
  const radius = parseRadius(radiusParam) ?? defaults.radiusKm;

  const page = parsePage(params.get("page"));

  return {
    lat: Number.isFinite(lat) ? lat : defaults.lat,
    lng: Number.isFinite(lng) ? lng : defaults.lng,
    radiusKm: radius,
    page,
  };
};

const areStatesEqual = (a: NearbyQueryState, b: NearbyQueryState) =>
  Math.abs(a.lat - b.lat) < 1e-9 &&
  Math.abs(a.lng - b.lng) < 1e-9 &&
  a.radiusKm === b.radiusKm &&
  a.page === b.page;

export type LocationStatus = "idle" | "loading" | "success" | "error";
export type LocationMode = "url" | "auto" | "manual" | "map";

export interface NearbyQueryState {
  lat: number;
  lng: number;
  radiusKm: number;
  page: number;
}

export interface NearbyFormState {
  latInput: string;
  lngInput: string;
  radiusKm: number;
}

export interface NearbyLocationState {
  status: LocationStatus;
  error: string | null;
  isSupported: boolean;
  hasResolvedSupport: boolean;
  mode: LocationMode;
  hasExplicitLocation: boolean;
}

export interface UseNearbySearchControllerOptions {
  defaultCenter: { lat: number; lng: number };
  defaultRadiusKm?: number;
}

export interface UseNearbySearchControllerResult {
  applied: NearbyQueryState;
  formState: NearbyFormState;
  manualError: string | null;
  location: NearbyLocationState;
  radiusBounds: { min: number; max: number; step: number };
  setLatInput: (value: string) => void;
  setLngInput: (value: string) => void;
  updateRadius: (value: number) => void;
  submitManualCoordinates: () => void;
  updateCenterFromMap: (center: { lat: number; lng: number }) => void;
  requestCurrentLocation: () => void;
  setPage: (page: number) => void;
}

export function useNearbySearchController({
  defaultCenter,
  defaultRadiusKm = DEFAULT_RADIUS_KM,
}: UseNearbySearchControllerOptions): UseNearbySearchControllerResult {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const searchParamsKey = searchParams.toString();

  const resolvedDefaults = useMemo(
    () => ({
      lat: clampLatitude(defaultCenter.lat),
      lng: clampLongitude(defaultCenter.lng),
      radiusKm: clampRadius(defaultRadiusKm),
    }),
    [defaultCenter.lat, defaultCenter.lng, defaultRadiusKm],
  );

  const geolocationSupportedRef = useRef(
    typeof window !== "undefined" &&
      typeof window.navigator !== "undefined" &&
      "geolocation" in window.navigator,
  );
  const [isGeolocationSupported, setIsGeolocationSupported] = useState(false);
  const [hasResolvedGeolocationSupport, setHasResolvedGeolocationSupport] = useState(false);

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

  const [applied, setApplied] = useState<NearbyQueryState>(() =>
    parseNearbyState(searchParams, resolvedDefaults),
  );
  const [hasExplicitLocation, setHasExplicitLocation] = useState(() => {
    const params = new URLSearchParams(searchParamsKey);
    return params.has("lat") && params.has("lng");
  });
  const [formState, setFormState] = useState<NearbyFormState>(() => ({
    latInput: applied.lat.toFixed(6),
    lngInput: applied.lng.toFixed(6),
    radiusKm: applied.radiusKm,
  }));
  const [manualError, setManualError] = useState<string | null>(null);
  const [locationStatus, setLocationStatus] = useState<LocationStatus>("success");
  const [locationError, setLocationError] = useState<string | null>(null);
  const [locationMode, setLocationMode] = useState<LocationMode>("url");

  const pendingSourceRef = useRef<LocationMode | null>(null);

  const applyQuery = useCallback(
    (
      next: NearbyQueryState,
      options: { historyMode?: HistoryNavigationMode; source?: LocationMode } = {},
    ) => {
      const isSame = areStatesEqual(applied, next);
      setApplied(next);
      setFormState({
        latInput: next.lat.toFixed(6),
        lngInput: next.lng.toFixed(6),
        radiusKm: next.radiusKm,
      });
      setManualError(null);

      if (options.source) {
        setLocationMode(options.source);
        if (options.source !== "url") {
          setLocationStatus("success");
          setLocationError(null);
        }
      }

      if (isSame) {
        pendingSourceRef.current = null;
        return;
      }

      pendingSourceRef.current = options.source ?? null;
      const params = new URLSearchParams(searchParamsKey);
      params.set("lat", next.lat.toFixed(6));
      params.set("lng", next.lng.toFixed(6));
      params.delete("radius");
      params.delete("radius_km");
      params.set("radiusKm", String(next.radiusKm));
      if (next.page <= 1) {
        params.delete("page");
      } else {
        params.set("page", String(next.page));
      }
      const nextQuery = params.toString();
      const desiredMode: HistoryNavigationMode = options.historyMode ?? "push";
      const plan = planNavigation({
        pathname,
        currentSearch: searchParamsKey,
        nextSearch: nextQuery,
        mode: desiredMode,
      });

      if (!plan.shouldNavigate || !plan.url) {
        pendingSourceRef.current = null;
        return;
      }

      if (plan.mode === "replace") {
        router.replace(plan.url, { scroll: false });
      } else {
        router.push(plan.url, { scroll: false });
      }
      setHasExplicitLocation(true);
    },
    [applied, pathname, router, searchParamsKey],
  );

  useEffect(() => {
    const parsed = parseNearbyState(new URLSearchParams(searchParamsKey), resolvedDefaults);
    setApplied(prev => (areStatesEqual(prev, parsed) ? prev : parsed));
    const params = new URLSearchParams(searchParamsKey);
    setHasExplicitLocation(params.has("lat") && params.has("lng"));
    setFormState(prev => {
      if (
        prev.latInput === parsed.lat.toFixed(6) &&
        prev.lngInput === parsed.lng.toFixed(6) &&
        prev.radiusKm === parsed.radiusKm
      ) {
        return prev;
      }
      return {
        latInput: parsed.lat.toFixed(6),
        lngInput: parsed.lng.toFixed(6),
        radiusKm: parsed.radiusKm,
      };
    });

    const source = pendingSourceRef.current;
    if (source) {
      setLocationMode(source);
      if (source !== "url") {
        setLocationStatus("success");
        setLocationError(null);
      }
    } else {
      setLocationMode("url");
      setLocationStatus(status => (status === "loading" ? "success" : status));
    }
    pendingSourceRef.current = null;
  }, [resolvedDefaults, searchParamsKey]);

  const setLatInput = useCallback((value: string) => {
    setFormState(prev => ({ ...prev, latInput: value }));
    setManualError(null);
  }, []);

  const setLngInput = useCallback((value: string) => {
    setFormState(prev => ({ ...prev, lngInput: value }));
    setManualError(null);
  }, []);

  const updateRadius = useCallback(
    (value: number) => {
      if (!Number.isFinite(value)) {
        return;
      }
      const nextRadius = clampRadius(value);
      if (nextRadius === formState.radiusKm && nextRadius === applied.radiusKm) {
        return;
      }
      applyQuery(
        {
          ...applied,
          radiusKm: nextRadius,
          page: 1,
        },
        { source: locationMode, historyMode: "push" },
      );
    },
    [applied, applyQuery, formState.radiusKm, locationMode],
  );

  const submitManualCoordinates = useCallback(() => {
    const latValue = Number.parseFloat(formState.latInput);
    const lngValue = Number.parseFloat(formState.lngInput);
    if (!Number.isFinite(latValue) || !Number.isFinite(lngValue)) {
      setManualError("緯度・経度を数値で入力してください。（例: 35.681236）");
      return;
    }
    const clampedLat = clampLatitude(latValue);
    const clampedLng = clampLongitude(lngValue);
    setManualError(null);
    setLocationMode("manual");
    setLocationStatus("success");
    setLocationError(null);
    applyQuery(
      {
        lat: clampedLat,
        lng: clampedLng,
        radiusKm: applied.radiusKm,
        page: 1,
      },
      { source: "manual", historyMode: "push" },
    );
  }, [applied.radiusKm, applyQuery, formState.latInput, formState.lngInput]);

  const updateCenterFromMap = useCallback(
    (center: { lat: number; lng: number }) => {
      const lat = clampLatitude(center.lat);
      const lng = clampLongitude(center.lng);
      applyQuery(
        {
          lat,
          lng,
          radiusKm: applied.radiusKm,
          page: 1,
        },
        { source: "map", historyMode: "push" },
      );
    },
    [applied.radiusKm, applyQuery],
  );

  const requestCurrentLocation = useCallback(() => {
    const supported = detectGeolocationSupport();
    if (!supported) {
      setLocationMode("auto");
      setLocationStatus("error");
      setLocationError(GEO_UNSUPPORTED_MESSAGE);
      return;
    }
    setLocationMode("auto");
    setLocationStatus("loading");
    setLocationError(null);
    window.navigator.geolocation.getCurrentPosition(
      position => {
        const lat = clampLatitude(position.coords.latitude);
        const lng = clampLongitude(position.coords.longitude);
        setLocationStatus("success");
        setLocationError(null);
        applyQuery(
          {
            lat,
            lng,
            radiusKm: applied.radiusKm,
            page: 1,
          },
          { source: "auto", historyMode: "push" },
        );
      },
      error => {
        const PERM = error?.PERMISSION_DENIED ?? 1;
        const UNAV = error?.POSITION_UNAVAILABLE ?? 2;
        const TOUT = error?.TIMEOUT ?? 3;
        let message = GEO_UNAVAILABLE_MESSAGE;
        if (error.code === PERM) {
          message = GEO_PERMISSION_DENIED_MESSAGE;
        } else if (error.code === UNAV) {
          message = GEO_UNAVAILABLE_MESSAGE;
        } else if (error.code === TOUT) {
          message = GEO_TIMEOUT_MESSAGE;
        }
        setLocationStatus("error");
        setLocationError(message);
      },
      { enableHighAccuracy: false, maximumAge: 300000, timeout: 10000 },
    );
  }, [applied.radiusKm, applyQuery, detectGeolocationSupport]);

  const setPage = useCallback(
    (page: number) => {
      if (!Number.isFinite(page)) {
        return;
      }
      const nextPage = Math.max(1, Math.trunc(page));
      if (nextPage === applied.page) {
        return;
      }
      applyQuery(
        {
          ...applied,
          page: nextPage,
        },
        { source: locationMode, historyMode: "replace" },
      );
    },
    [applied, applyQuery, locationMode],
  );

  const radiusBounds = useMemo(
    () => ({ min: MIN_DISTANCE_KM, max: MAX_DISTANCE_KM, step: DISTANCE_STEP_KM }),
    [],
  );

  const location: NearbyLocationState = useMemo(
    () => ({
      status: locationStatus,
      error: locationError,
      isSupported: isGeolocationSupported,
      hasResolvedSupport: hasResolvedGeolocationSupport,
      mode: locationMode,
      hasExplicitLocation,
    }),
    [
      hasExplicitLocation,
      hasResolvedGeolocationSupport,
      isGeolocationSupported,
      locationError,
      locationMode,
      locationStatus,
    ],
  );

  return {
    applied,
    formState,
    manualError,
    location,
    radiusBounds,
    setLatInput,
    setLngInput,
    updateRadius,
    submitManualCoordinates,
    updateCenterFromMap,
    requestCurrentLocation,
    setPage,
  };
}
