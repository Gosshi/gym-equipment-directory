"use client";

import { useMemo } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { fetchNearbyGyms } from "@/services/gymNearby";
import { searchGyms } from "@/services/gyms";
import { useGymSearchStore } from "@/store/searchStore";
import type { GymNearbyResponse, GymSearchResponse } from "@/types/gym";

const MAP_RESULT_LIMIT = 200;

export function useGymDirectoryData() {
  const filters = useGymSearchStore(state => ({
    q: state.q,
    category: state.category,
    lat: state.lat,
    lng: state.lng,
    radiusKm: state.radiusKm,
    page: state.page,
    limit: state.limit,
    sort: state.sort,
  }));

  const searchKey = useMemo(
    () => [
      "gym-search",
      {
        q: filters.q,
        category: filters.category,
        lat: filters.lat,
        lng: filters.lng,
        radiusKm: filters.radiusKm,
        page: filters.page,
        limit: filters.limit,
        sort: filters.sort,
      },
    ],
    [filters],
  );

  const searchQuery = useQuery<GymSearchResponse>({
    queryKey: searchKey,
    queryFn: () =>
      searchGyms({
        q: filters.q || undefined,
        categories: filters.category ? [filters.category] : undefined,
        page: filters.page,
        limit: filters.limit,
        sort: filters.sort,
        lat: filters.lat,
        lng: filters.lng,
        radiusKm: filters.radiusKm,
      }),
    placeholderData: keepPreviousData,
  });

  const mapQuery = useQuery<GymNearbyResponse>({
    queryKey: [
      "gym-map",
      {
        lat: filters.lat,
        lng: filters.lng,
        radiusKm: filters.radiusKm,
      },
    ],
    queryFn: () =>
      fetchNearbyGyms({
        lat: filters.lat,
        lng: filters.lng,
        radiusKm: filters.radiusKm,
        perPage: Math.max(filters.limit * 2, MAP_RESULT_LIMIT),
        page: 1,
      }),
    enabled: Number.isFinite(filters.lat) && Number.isFinite(filters.lng),
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });

  return { searchQuery, mapQuery };
}
