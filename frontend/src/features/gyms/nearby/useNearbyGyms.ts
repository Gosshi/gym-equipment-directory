"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiError } from "@/lib/apiClient";
import { fetchNearbyGyms } from "@/services/gymNearby";
import type { NearbyGym } from "@/types/gym";

export type NearbyFilters = {
  center: { lat: number; lng: number };
  radiusKm: number;
  page: number;
  perPage?: number;
};

interface NearbyState {
  items: NearbyGym[];
  meta: {
    total: number;
    page: number;
    pageSize: number;
    hasMore: boolean;
    hasPrev: boolean;
  };
  isInitialLoading: boolean;
  isLoading: boolean;
  error: string | null;
  reload: () => void;
}

export function useNearbyGyms({
  center,
  radiusKm,
  page,
  perPage = 20,
}: NearbyFilters): NearbyState {
  const [items, setItems] = useState<NearbyGym[]>([]);
  const [meta, setMeta] = useState({
    total: 0,
    page,
    pageSize: perPage,
    hasMore: false,
    hasPrev: false,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshIndex, setRefreshIndex] = useState(0);

  const abortRef = useRef<AbortController | null>(null);
  const latestRequestKey = useRef<string>("");

  const cancelOngoingRequest = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  useEffect(() => {
    cancelOngoingRequest();
    const controller = new AbortController();
    abortRef.current = controller;
    const requestKey = `${center.lat}:${center.lng}:${radiusKm}:${page}:${perPage}:${refreshIndex}`;
    latestRequestKey.current = requestKey;

    setIsLoading(true);
    setError(null);

    let active = true;

    fetchNearbyGyms({
      lat: center.lat,
      lng: center.lng,
      radiusKm,
      perPage,
      page,
      signal: controller.signal,
    })
      .then(response => {
        if (!active || latestRequestKey.current !== requestKey) {
          return;
        }
        setItems(response.items);
        setMeta({
          total: response.total,
          page: response.page,
          pageSize: response.pageSize,
          hasMore: response.hasMore,
          hasPrev: response.hasPrev,
        });
        setHasLoadedOnce(true);
      })
      .catch(err => {
        if (!active || controller.signal.aborted) {
          return;
        }
        const message = err instanceof ApiError ? err.message : "近隣施設の取得に失敗しました";
        setError(message);
        setItems([]);
        setMeta(prev => ({
          total: prev.total,
          page,
          pageSize: perPage,
          hasMore: false,
          hasPrev: page > 1,
        }));
      })
      .finally(() => {
        if (!active || latestRequestKey.current !== requestKey) {
          return;
        }
        setIsLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [cancelOngoingRequest, center.lat, center.lng, page, perPage, radiusKm, refreshIndex]);

  const reload = useCallback(() => {
    setRefreshIndex(value => value + 1);
  }, []);

  const isInitialLoading = isLoading && !hasLoadedOnce;

  const resolvedMeta = useMemo(
    () => ({
      total: meta.total,
      page: meta.page,
      pageSize: meta.pageSize,
      hasMore: meta.hasMore,
      hasPrev: meta.hasPrev,
    }),
    [meta.hasMore, meta.hasPrev, meta.page, meta.pageSize, meta.total],
  );

  return {
    items,
    meta: resolvedMeta,
    isInitialLoading,
    isLoading,
    error,
    reload,
  };
}
