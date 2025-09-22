"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { metersToKilometres } from "@/lib/geo";
import { ApiError } from "@/lib/apiClient";
import { fetchNearbyGyms } from "@/services/gymNearby";
import type { NearbyGym } from "@/types/gym";

export type NearbyFilters = {
  center: { lat: number; lng: number };
  radiusMeters: number;
  perPage?: number;
};

interface NearbyState {
  items: NearbyGym[];
  isInitialLoading: boolean;
  isLoading: boolean;
  error: string | null;
  hasNext: boolean;
  loadMore: () => void;
  reload: () => void;
}

const logDebug = (event: string, payload: Record<string, unknown>) => {
  if (typeof window !== "undefined" && process.env.NODE_ENV !== "test") {
    // eslint-disable-next-line no-console
    console.debug(event, payload);
  }
};

export function useNearbyGyms({ center, radiusMeters, perPage = 20 }: NearbyFilters): NearbyState {
  const [items, setItems] = useState<NearbyGym[]>([]);
  const [pageToken, setPageToken] = useState<string | null>(null);
  const [hasNext, setHasNext] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);

  const abortRef = useRef<AbortController | null>(null);
  const latestRequestKey = useRef<string>("");

  const radiusKm = useMemo(() => metersToKilometres(radiusMeters), [radiusMeters]);

  const cancelOngoingRequest = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  const fetchPage = useCallback(
    async (token: string | null, reset: boolean) => {
      cancelOngoingRequest();
      const controller = new AbortController();
      abortRef.current = controller;

      const requestKey = `${center.lat}:${center.lng}:${radiusKm}:${token ?? ""}`;
      latestRequestKey.current = requestKey;

      setIsLoading(true);
      setError(null);
      if (reset) {
        setIsInitialLoading(true);
      }

      logDebug("nearby_fetch_start", {
        center_lat: center.lat,
        center_lng: center.lng,
        radius_km: radiusKm,
        page_token: token,
      });

      try {
        const response = await fetchNearbyGyms({
          lat: center.lat,
          lng: center.lng,
          radiusKm,
          perPage,
          pageToken: token,
          signal: controller.signal,
        });

        if (latestRequestKey.current !== requestKey) {
          return;
        }

        setItems((prev) => (reset ? response.items : [...prev, ...response.items]));
        setPageToken(response.pageToken);
        setHasNext(response.hasNext);
        setIsInitialLoading(false);

        logDebug("nearby_fetch_end", {
          returned: response.items.length,
          has_next: response.hasNext,
          next_token: response.pageToken,
        });
      } catch (err) {
        if (controller.signal.aborted) {
          return;
        }

        const message = err instanceof ApiError ? err.message : "近隣ジムの取得に失敗しました";
        setError(message);
        setItems((prev) => (reset ? [] : prev));
        setHasNext(false);
        setIsInitialLoading(false);
      } finally {
        if (latestRequestKey.current === requestKey) {
          setIsLoading(false);
        }
      }
    },
    [cancelOngoingRequest, center.lat, center.lng, perPage, radiusKm],
  );

  useEffect(() => {
    fetchPage(null, true);
    return cancelOngoingRequest;
  }, [fetchPage, cancelOngoingRequest]);

  const loadMore = useCallback(() => {
    if (!hasNext || isLoading) {
      return;
    }
    fetchPage(pageToken, false);
  }, [fetchPage, hasNext, isLoading, pageToken]);

  const reload = useCallback(() => {
    fetchPage(null, true);
  }, [fetchPage]);

  return {
    items,
    isInitialLoading,
    isLoading,
    error,
    hasNext,
    loadMore,
    reload,
  };
}
