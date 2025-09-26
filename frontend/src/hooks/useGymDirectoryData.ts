"use client";

import { useMemo } from "react";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useShallow } from "zustand/react/shallow";

import { MAX_LIMIT, type SortOption, type SortOrder } from "@/lib/searchParams";
import { fetchNearbyGyms } from "@/services/gymNearby";
import { searchGyms } from "@/services/gyms";
import { useGymSearchStore } from "@/store/searchStore";
import type { GymNearbyResponse, GymSearchResponse } from "@/types/gym";

const MAP_RESULT_MIN = 60;

type SearchQueryKey = [
  "gyms",
  "search",
  {
    q: string;
    categories: string[];
    prefecture: string;
    city: string;
    sort: SortOption;
    order: SortOrder;
    page: number;
    limit: number;
    lat: number | null;
    lng: number | null;
    radiusKm: number;
  },
];

type MapQueryKey = [
  "gyms",
  "map",
  {
    lat: number;
    lng: number;
    radiusKm: number;
    limit: number;
  },
];

const createSearchKey = (params: SearchQueryKey[2]): SearchQueryKey => ["gyms", "search", params];

const createMapKey = (params: MapQueryKey[2]): MapQueryKey => ["gyms", "map", params];
const DISABLED_MAP_KEY: MapQueryKey = ["gyms", "map", { lat: 0, lng: 0, radiusKm: 0, limit: 0 }];

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

  const searchKey = useMemo<SearchQueryKey>(
    () =>
      createSearchKey({
        q,
        categories,
        prefecture,
        city,
        sort,
        order,
        page,
        limit,
        lat,
        lng,
        radiusKm,
      }),
    [q, categories, prefecture, city, sort, order, page, limit, lat, lng, radiusKm],
  );

  const mapKey = useMemo<MapQueryKey | null>(() => {
    if (lat == null || lng == null || !Number.isFinite(lat) || !Number.isFinite(lng)) {
      return null;
    }
    const baseLimit = typeof limit === "number" && limit > 0 ? limit : MAP_RESULT_MIN;
    const perPage = Math.min(Math.max(baseLimit * 2, MAP_RESULT_MIN), MAX_LIMIT);
    return createMapKey({
      lat,
      lng,
      radiusKm,
      limit: perPage,
    });
  }, [lat, lng, radiusKm, limit]);

  const searchQuery = useQuery<GymSearchResponse, unknown, GymSearchResponse, SearchQueryKey>({
    queryKey: searchKey,
    placeholderData: keepPreviousData,
    queryFn: async ({ queryKey: [, , params] }) =>
      searchGyms({
        q: params.q || undefined,
        categories: params.categories.length > 0 ? params.categories : undefined,
        prefecture: params.prefecture || undefined,
        city: params.city || undefined,
        page: params.page,
        limit: params.limit,
        sort: params.sort,
        order: params.order,
        lat: params.lat ?? undefined,
        lng: params.lng ?? undefined,
        radiusKm: params.radiusKm,
      }),
    gcTime: 1000 * 60 * 5,
    staleTime: 1000 * 10,
  });

  const mapQuery = useQuery<GymNearbyResponse, unknown, GymNearbyResponse, MapQueryKey>({
    queryKey: mapKey ?? DISABLED_MAP_KEY,
    enabled: mapKey !== null,
    placeholderData: keepPreviousData,
    queryFn: async ({ queryKey: [, , params] }) =>
      fetchNearbyGyms({
        lat: params.lat,
        lng: params.lng,
        radiusKm: params.radiusKm ?? undefined,
        perPage: params.limit,
        page: 1,
      }),
    gcTime: 1000 * 60 * 5,
    staleTime: 1000 * 5,
  });

  return {
    searchQuery,
    mapQuery,
    isMapEnabled: mapKey !== null,
  };
}
