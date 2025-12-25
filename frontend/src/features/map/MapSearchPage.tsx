"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import { useGymSearch } from "@/hooks/useGymSearch";
import { Loader2 } from "lucide-react";

// Dynamically import SearchMap to avoid SSR issues with Leaflet
const SearchMap = dynamic(() => import("./SearchMap"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center bg-gray-100">
      <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
    </div>
  ),
});

export function MapSearchPage() {
  const { items, updateBoundingBox, location, isInitialLoading, appliedFilters } = useGymSearch({
    debounceMs: 500,
  });
  const [initialCenter, setInitialCenter] = useState<{ lat: number; lng: number } | undefined>(
    undefined,
  );

  // Set initial center based on location state or BBox or default
  useEffect(() => {
    if (location.lat && location.lng) {
      setInitialCenter({ lat: location.lat, lng: location.lng });
    } else if (
      appliedFilters.min_lat != null &&
      appliedFilters.max_lat != null &&
      appliedFilters.min_lng != null &&
      appliedFilters.max_lng != null
    ) {
      // Calculate center from BBox
      const lat = (appliedFilters.min_lat + appliedFilters.max_lat) / 2;
      const lng = (appliedFilters.min_lng + appliedFilters.max_lng) / 2;
      setInitialCenter({ lat, lng });
    }
  }, [
    location.lat,
    location.lng,
    appliedFilters.min_lat,
    appliedFilters.max_lat,
    appliedFilters.min_lng,
    appliedFilters.max_lng,
  ]);

  return (
    <div className="h-[calc(100vh-64px)] w-full flex flex-col relative">
      <div className="flex-1 relative z-0">
        <SearchMap items={items} onBoundsChange={updateBoundingBox} initialCenter={initialCenter} />
      </div>

      {/* Overlay: List of gyms (optional, simplified for now) */}
      <div className="absolute bottom-4 left-4 right-4 z-[1000] pointer-events-none">
        <div className="bg-white/90 backdrop-blur-sm p-3 rounded-lg shadow-lg border border-gray-200 pointer-events-auto max-w-md mx-auto">
          <p className="text-sm font-medium text-gray-700">
            {isInitialLoading ? "読み込み中..." : `${items.length}件のジムが見つかりました`}
          </p>
          <p className="text-xs text-gray-500 mt-1">地図を移動すると自動で再検索します</p>
        </div>
      </div>
    </div>
  );
}
