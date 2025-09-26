"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef } from "react";

import { useShallow } from "zustand/react/shallow";

import type { MapViewport } from "@/hooks/useVisibleGyms";
import { haversineDistanceKm } from "@/lib/geo";
import { MIN_DISTANCE_KM, MAX_DISTANCE_KM } from "@/lib/searchParams";
import { FALLBACK_LOCATION } from "@/hooks/useGymSearch";
import type { MapInteractionSource } from "@/state/mapSelection";
import type { NearbyGym } from "@/types/gym";
import { useGymSearchStore, gymSearchStore } from "@/store/searchStore";

const NearbyMap = dynamic(
  () => import("@/features/gyms/nearby/components/NearbyMap").then(mod => mod.NearbyMap),
  {
    ssr: false,
  },
);

const RADIUS_DEBOUNCE_MS = 300;

const calculateRadius = (viewport: MapViewport): number => {
  const { center, bounds } = viewport;
  const northEast = { lat: bounds.north, lng: bounds.east };
  const southWest = { lat: bounds.south, lng: bounds.west };
  const radius = Math.max(
    haversineDistanceKm(center, northEast),
    haversineDistanceKm(center, southWest),
  );
  const clamped = Math.min(Math.max(radius, MIN_DISTANCE_KM), MAX_DISTANCE_KM);
  return Number.isFinite(clamped) ? clamped : MIN_DISTANCE_KM;
};

interface MapViewProps {
  markers: NearbyGym[];
  status: "idle" | "loading" | "success" | "error";
  error: string | null;
  isInitialLoading: boolean;
  onRetry?: () => void;
}

export function MapView({ markers, status, error, isInitialLoading, onRetry }: MapViewProps) {
  const {
    lat,
    lng,
    zoom,
    selectedGymId,
    lastSelectionSource: rawLastSelectionSource,
    lastSelectionAt,
  } = useGymSearchStore(
    useShallow(state => ({
      lat: state.lat,
      lng: state.lng,
      zoom: state.zoom,
      selectedGymId: state.selectedGymId,
      lastSelectionSource: state.lastSelectionSource,
      lastSelectionAt: state.lastSelectionAt,
    })),
  );
  const setMapState = useGymSearchStore(state => state.setMapState);
  const setSelectedGym = useGymSearchStore(state => state.setSelectedGym);
  const setBusyFlag = useGymSearchStore(state => state.setBusyFlag);

  const lastSelectionSource: MapInteractionSource | null =
    rawLastSelectionSource === "panel"
      ? null
      : rawLastSelectionSource === "url"
        ? "url"
        : rawLastSelectionSource;

  const markersById = useMemo(() => new Map(markers.map(marker => [marker.id, marker])), [markers]);
  const center = useMemo(() => {
    if (
      typeof lat === "number" &&
      Number.isFinite(lat) &&
      typeof lng === "number" &&
      Number.isFinite(lng)
    ) {
      return { lat, lng };
    }
    return { lat: FALLBACK_LOCATION.lat, lng: FALLBACK_LOCATION.lng };
  }, [lat, lng]);

  const debounceRef = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (debounceRef.current !== null) {
        window.clearTimeout(debounceRef.current);
        debounceRef.current = null;
      }
      setBusyFlag("mapInteracting", false);
    },
    [setBusyFlag],
  );

  const handleViewportChange = useCallback(
    (viewport: MapViewport) => {
      if (debounceRef.current !== null) {
        window.clearTimeout(debounceRef.current);
        debounceRef.current = null;
      }
      const radiusKm = calculateRadius(viewport);
      const { center: viewportCenter, zoom: viewportZoom } = viewport;
      const current = gymSearchStore.getState();
      const sameCenter =
        current.lat != null &&
        current.lng != null &&
        Math.abs(current.lat - viewportCenter.lat) < 1e-6 &&
        Math.abs(current.lng - viewportCenter.lng) < 1e-6;
      const sameRadius = Math.abs(current.radiusKm - radiusKm) < 0.05;
      const sameZoom = viewportZoom == null ? true : Math.abs(current.zoom - viewportZoom) < 0.01;
      if (sameCenter && sameRadius && sameZoom) {
        return;
      }
      setBusyFlag("mapInteracting", true);
      debounceRef.current = window.setTimeout(() => {
        setBusyFlag("mapInteracting", false);
        setMapState({
          lat: viewportCenter.lat,
          lng: viewportCenter.lng,
          radiusKm,
          zoom: viewportZoom,
        });
      }, RADIUS_DEBOUNCE_MS);
    },
    [setBusyFlag, setMapState],
  );

  const handleSelect = useCallback(
    (gymId: number | null, source: MapInteractionSource) => {
      if (gymId == null) {
        setSelectedGym({ slug: null, id: null, source });
        return;
      }
      const gym = markersById.get(gymId) ?? null;
      setSelectedGym({ slug: gym?.slug ?? null, id: gymId, source });
    },
    [markersById, setSelectedGym],
  );

  return (
    <NearbyMap
      center={center}
      zoom={zoom}
      markers={markers}
      selectedGymId={selectedGymId}
      lastSelectionSource={lastSelectionSource}
      lastSelectionAt={lastSelectionAt}
      onCenterChange={center => {
        setBusyFlag("mapInteracting", true);
        if (debounceRef.current !== null) {
          window.clearTimeout(debounceRef.current);
          debounceRef.current = null;
        }
        const current = gymSearchStore.getState();
        const sameCenter =
          current.lat != null &&
          current.lng != null &&
          Math.abs(current.lat - center.lat) < 1e-6 &&
          Math.abs(current.lng - center.lng) < 1e-6;
        if (sameCenter) {
          setBusyFlag("mapInteracting", false);
          return;
        }
        debounceRef.current = window.setTimeout(() => {
          setBusyFlag("mapInteracting", false);
          setMapState({ lat: center.lat, lng: center.lng });
        }, RADIUS_DEBOUNCE_MS);
      }}
      onViewportChange={handleViewportChange}
      onSelect={handleSelect}
      markersStatus={status}
      markersError={error}
      markersIsLoading={status === "loading"}
      markersIsInitialLoading={isInitialLoading}
      onRetryMarkers={onRetry}
    />
  );
}
