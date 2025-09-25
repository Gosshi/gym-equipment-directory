"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { haversineDistanceKm } from "@/lib/geo";
import type { MapBounds } from "@/lib/cluster";
import { fetchNearbyGyms } from "@/services/gymNearby";
import type { NearbyGym } from "@/types/gym";

export type MapViewport = {
  bounds: MapBounds;
  zoom: number;
  center: { lat: number; lng: number };
};

type FetchStatus = "idle" | "loading" | "success" | "error";

const DEFAULT_DEBOUNCE_MS = 220;
const DEFAULT_LIMIT = 250;
const MIN_RADIUS_KM = 0.5;

const roundCoordinate = (value: number) => Number.parseFloat(value.toFixed(5));

const buildViewportKey = (viewport: MapViewport) => {
  const { bounds, center, zoom } = viewport;
  return [
    roundCoordinate(center.lat),
    roundCoordinate(center.lng),
    roundCoordinate(bounds.north),
    roundCoordinate(bounds.south),
    roundCoordinate(bounds.east),
    roundCoordinate(bounds.west),
    Math.round(zoom),
  ].join(":");
};

const calculateRadiusKm = (viewport: MapViewport) => {
  const { bounds, center } = viewport;
  const northEast = { lat: bounds.north, lng: bounds.east };
  const southWest = { lat: bounds.south, lng: bounds.west };
  const radius = Math.max(
    haversineDistanceKm(center, northEast),
    haversineDistanceKm(center, southWest),
  );
  return Math.max(radius, MIN_RADIUS_KM);
};

export interface UseVisibleGymsOptions {
  initialGyms?: NearbyGym[];
  debounceMs?: number;
  filtersKey?: string;
  limit?: number;
  maxRadiusKm?: number;
}

export interface UseVisibleGymsResult {
  gyms: NearbyGym[];
  status: FetchStatus;
  error: string | null;
  isLoading: boolean;
  isInitialLoading: boolean;
  updateViewport: (viewport: MapViewport) => void;
  reload: () => void;
}

export function useVisibleGyms({
  initialGyms = [],
  debounceMs = DEFAULT_DEBOUNCE_MS,
  filtersKey = "",
  limit = DEFAULT_LIMIT,
  maxRadiusKm,
}: UseVisibleGymsOptions = {}): UseVisibleGymsResult {
  const [gyms, setGyms] = useState<NearbyGym[]>(initialGyms);
  const [status, setStatus] = useState<FetchStatus>(initialGyms.length > 0 ? "success" : "idle");
  const [error, setError] = useState<string | null>(null);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(initialGyms.length > 0);

  const latestViewportRef = useRef<MapViewport | null>(null);
  const lastRequestKeyRef = useRef<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceTimerRef = useRef<number | null>(null);
  const filtersKeyRef = useRef(filtersKey);

  useEffect(() => {
    filtersKeyRef.current = filtersKey;
  }, [filtersKey]);

  useEffect(() => {
    return () => {
      if (debounceTimerRef.current !== null) {
        window.clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    setGyms(initialGyms);
    setStatus(initialGyms.length > 0 ? "success" : "idle");
    setError(null);
    setHasLoadedOnce(initialGyms.length > 0);
  }, [initialGyms, filtersKey]);

  const runFetch = useCallback(
    (viewport: MapViewport, immediate = false, force = false) => {
      const viewportKey = buildViewportKey(viewport);
      const requestKey = `${filtersKeyRef.current}:${viewportKey}`;

      if (!force && lastRequestKeyRef.current === requestKey && status !== "error") {
        return;
      }

      const execute = () => {
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
        }

        const controller = new AbortController();
        abortControllerRef.current = controller;

        setStatus("loading");
        setError(null);

        const radiusKm = Math.min(calculateRadiusKm(viewport), maxRadiusKm ?? Number.POSITIVE_INFINITY);
        const perPage = Math.max(Math.min(Math.round(limit), 500), 50);

        fetchNearbyGyms({
          lat: viewport.center.lat,
          lng: viewport.center.lng,
          radiusKm: Number.isFinite(radiusKm) ? radiusKm : calculateRadiusKm(viewport),
          perPage,
          page: 1,
          signal: controller.signal,
        })
          .then(response => {
            lastRequestKeyRef.current = requestKey;
            setGyms(response.items);
            setStatus("success");
            setHasLoadedOnce(true);
          })
          .catch(err => {
            if (controller.signal.aborted) {
              return;
            }
            setStatus("error");
            setError(err instanceof Error ? err.message : "地図のジム取得に失敗しました");
          });
      };

      if (immediate) {
        execute();
        return;
      }

      if (debounceTimerRef.current !== null) {
        window.clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }

      debounceTimerRef.current = window.setTimeout(execute, debounceMs);
    },
    [debounceMs, limit, maxRadiusKm, status],
  );

  const updateViewport = useCallback(
    (viewport: MapViewport) => {
      latestViewportRef.current = viewport;
      runFetch(viewport);
    },
    [runFetch],
  );

  const reload = useCallback(() => {
    if (!latestViewportRef.current) {
      return;
    }
    runFetch(latestViewportRef.current, true, true);
  }, [runFetch]);

  const isLoading = status === "loading";
  const isInitialLoading = isLoading && !hasLoadedOnce;

  return useMemo(
    () => ({
      gyms,
      status,
      error,
      isLoading,
      isInitialLoading,
      updateViewport,
      reload,
    }),
    [error, gyms, isInitialLoading, isLoading, reload, status, updateViewport],
  );
}

