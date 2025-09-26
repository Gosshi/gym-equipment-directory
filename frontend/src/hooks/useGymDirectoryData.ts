"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";

import { MAX_LIMIT } from "@/lib/searchParams";
import { fetchNearbyGyms } from "@/services/gymNearby";
import { searchGyms } from "@/services/gyms";
import { useGymSearchStore } from "@/store/searchStore";
import { useShallow } from "zustand/react/shallow";
import type { GymNearbyResponse, GymSearchResponse } from "@/types/gym";

const MAP_RESULT_MIN = 60;

type QueryStatus = "idle" | "pending" | "success" | "error";

interface QueryState<TData> {
  data: TData | null;
  error: unknown;
  status: QueryStatus;
  isLoading: boolean;
  isFetching: boolean;
  isError: boolean;
}

const createInitialState = <TData>(): QueryState<TData> => ({
  data: null,
  error: null,
  status: "idle",
  isLoading: true,
  isFetching: false,
  isError: false,
});

export function useGymDirectoryData() {
  const { q, categories, prefecture, city, sort, order, lat, lng, radiusKm, page, limit } =
    useGymSearchStore(
      useShallow(state => ({
        q: state.q,
        categories: state.categories,
        prefecture: state.prefecture,
        city: state.city,
        sort: state.sort,
        order: state.order,
        lat: state.lat,
        lng: state.lng,
        radiusKm: state.radiusKm,
        page: state.page,
        limit: state.limit,
      })),
    );

  const [searchState, setSearchState] = useState<QueryState<GymSearchResponse>>(() =>
    createInitialState<GymSearchResponse>(),
  );
  const [mapState, setMapState] = useState<QueryState<GymNearbyResponse>>(() =>
    createInitialState<GymNearbyResponse>(),
  );

  const searchAbortRef = useRef<AbortController | null>(null);
  const mapAbortRef = useRef<AbortController | null>(null);

  const updatePendingState = useCallback(
    <TData>(setState: Dispatch<SetStateAction<QueryState<TData>>>) => {
      setState(prev => ({
        ...prev,
        status: prev.data ? prev.status : "pending",
        isLoading: !prev.data,
        isFetching: true,
        isError: false,
        error: null,
      }));
    },
    [],
  );

  const runSearchFetch = useCallback(
    async (signal: AbortSignal) => {
      try {
        const response = await searchGyms(
          {
            q: q || undefined,
            categories: categories.length > 0 ? categories : undefined,
            prefecture: prefecture || undefined,
            city: city || undefined,
            page,
            limit,
            sort,
            order,
            lat: lat ?? undefined,
            lng: lng ?? undefined,
            radiusKm,
          },
          { signal },
        );

        if (signal.aborted) {
          return;
        }

        setSearchState({
          data: response,
          error: null,
          status: "success",
          isLoading: false,
          isFetching: false,
          isError: false,
        });
      } catch (error) {
        if (signal.aborted) {
          return;
        }

        setSearchState(prev => ({
          ...prev,
          error,
          status: "error",
          isLoading: !prev.data,
          isFetching: false,
          isError: true,
        }));
      }
    },
    [categories, city, lat, limit, lng, order, page, prefecture, q, radiusKm, sort],
  );

  const runMapFetch = useCallback(
    async (signal: AbortSignal) => {
      const hasLat = typeof lat === "number" && Number.isFinite(lat);
      const hasLng = typeof lng === "number" && Number.isFinite(lng);
      if (!hasLat || !hasLng) {
        setMapState(prev => ({
          ...prev,
          status: "idle",
          isFetching: false,
          isLoading: false,
          isError: false,
          error: null,
        }));
        return;
      }

      try {
        const baseLimit = typeof limit === "number" && limit > 0 ? limit : MAP_RESULT_MIN;
        const perPage = Math.min(Math.max(baseLimit * 2, MAP_RESULT_MIN), MAX_LIMIT);
        const response = await fetchNearbyGyms({
          lat,
          lng,
          radiusKm: radiusKm ?? undefined,
          perPage,
          page: 1,
          signal,
        });

        if (signal.aborted) {
          return;
        }

        setMapState({
          data: response,
          error: null,
          status: "success",
          isLoading: false,
          isFetching: false,
          isError: false,
        });
      } catch (error) {
        if (signal.aborted) {
          return;
        }

        setMapState(prev => ({
          ...prev,
          error,
          status: "error",
          isLoading: !prev.data,
          isFetching: false,
          isError: true,
        }));
      }
    },
    [lat, limit, lng, radiusKm],
  );

  useEffect(() => {
    const controller = new AbortController();
    searchAbortRef.current?.abort();
    searchAbortRef.current = controller;
    updatePendingState(setSearchState);
    void runSearchFetch(controller.signal);
    return () => {
      controller.abort();
    };
  }, [runSearchFetch, updatePendingState]);

  useEffect(() => {
    const mapEnabled =
      typeof lat === "number" &&
      Number.isFinite(lat) &&
      typeof lng === "number" &&
      Number.isFinite(lng);
    if (!mapEnabled) {
      mapAbortRef.current?.abort();
      setMapState(prev => ({
        ...prev,
        status: "idle",
        isFetching: false,
        isLoading: false,
        isError: false,
        error: null,
      }));
      return undefined;
    }

    const controller = new AbortController();
    mapAbortRef.current?.abort();
    mapAbortRef.current = controller;
    updatePendingState(setMapState);
    void runMapFetch(controller.signal);
    return () => {
      controller.abort();
    };
  }, [lat, lng, updatePendingState, runMapFetch]);

  const refetchSearch = useCallback(async () => {
    const controller = new AbortController();
    searchAbortRef.current?.abort();
    searchAbortRef.current = controller;
    updatePendingState(setSearchState);
    await runSearchFetch(controller.signal);
  }, [runSearchFetch, updatePendingState]);

  const refetchMap = useCallback(async () => {
    const mapEnabled = Number.isFinite(lat) && Number.isFinite(lng);
    if (!mapEnabled) {
      setMapState(prev => ({
        ...prev,
        status: "idle",
        isFetching: false,
        isLoading: false,
        isError: false,
        error: null,
      }));
      return;
    }
    const controller = new AbortController();
    mapAbortRef.current?.abort();
    mapAbortRef.current = controller;
    updatePendingState(setMapState);
    await runMapFetch(controller.signal);
  }, [lat, lng, runMapFetch, updatePendingState]);

  return {
    searchQuery: {
      ...searchState,
      refetch: refetchSearch,
    },
    mapQuery: {
      ...mapState,
      refetch: refetchMap,
    },
  };
}
