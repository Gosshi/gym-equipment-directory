"use client";

import dynamic from "next/dynamic";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { GymDetailPanel } from "@/components/gyms/GymDetailPanel";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import { useSelectedGym } from "@/hooks/useSelectedGym";
import { useVisibleGyms } from "@/hooks/useVisibleGyms";
import { MIN_DISTANCE_KM, MAX_DISTANCE_KM } from "@/lib/searchParams";
import type { MapInteractionSource } from "@/state/mapSelection";
import { useMapSelectionStore } from "@/state/mapSelection";
import type { NearbyGym } from "@/types/gym";

import { NearbyList } from "./components/NearbyList";
import { NearbySearchPanel } from "./components/NearbySearchPanel";
import { useNearbyGyms } from "./useNearbyGyms";
import { useNearbySearchController } from "./useNearbySearchController";

const NearbyMap = dynamic(() => import("./components/NearbyMap").then(mod => mod.NearbyMap), {
  ssr: false,
});

const FALLBACK_CENTER = { lat: 35.681236, lng: 139.767125 };
const DEFAULT_RADIUS_KM = 3;

const logPinClick = (payload: Record<string, unknown>) => {
  if (typeof window !== "undefined" && process.env.NODE_ENV !== "test") {
    // eslint-disable-next-line no-console
    console.debug("pin_click", payload);
  }
};

const resolveDefaultCenter = () => {
  const envValue = process.env.NEXT_PUBLIC_DEFAULT_CENTER;
  if (typeof envValue === "string") {
    const parts = envValue.split(",").map(part => Number.parseFloat(part.trim()));
    if (parts.length === 2 && parts.every(value => Number.isFinite(value))) {
      return { lat: parts[0], lng: parts[1] };
    }
  }
  return FALLBACK_CENTER;
};

const resolveDefaultRadiusKm = () => {
  const envValue = process.env.NEXT_PUBLIC_DEFAULT_RADIUS;
  if (typeof envValue === "string") {
    const parsed = Number.parseFloat(envValue);
    if (Number.isFinite(parsed) && parsed > 0) {
      const normalized = parsed > 100 ? parsed / 1000 : parsed;
      const rounded = Math.round(normalized);
      return Math.min(Math.max(rounded, MIN_DISTANCE_KM), MAX_DISTANCE_KM);
    }
  }
  return DEFAULT_RADIUS_KM;
};

export function NearbyGymsPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const searchParamsSnapshot = searchParams.toString();
  const { toast } = useToast();
  const defaultCenter = useMemo(() => resolveDefaultCenter(), []);
  const defaultRadius = useMemo(() => resolveDefaultRadiusKm(), []);

  const {
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
  } = useNearbySearchController({ defaultCenter, defaultRadiusKm: defaultRadius });

  const { items, meta, isInitialLoading, isLoading, error, reload } = useNearbyGyms({
    center: { lat: applied.lat, lng: applied.lng },
    radiusKm: applied.radiusKm,
    page: applied.page,
  });

  const markerGyms = useMemo(
    () => items.filter(gym => Number.isFinite(gym.latitude) && Number.isFinite(gym.longitude)),
    [items],
  );

  const mapFiltersKey = useMemo(
    () =>
      [
        applied.lat.toFixed(4),
        applied.lng.toFixed(4),
        applied.radiusKm,
        applied.page,
        searchParamsSnapshot,
      ].join(":"),
    [applied.lat, applied.lng, applied.page, applied.radiusKm, searchParamsSnapshot],
  );

  const {
    gyms: visibleGyms,
    status: mapMarkersStatus,
    error: mapMarkersError,
    isLoading: mapMarkersIsLoading,
    isInitialLoading: mapMarkersIsInitialLoading,
    updateViewport: updateVisibleViewport,
    reload: reloadVisibleGyms,
  } = useVisibleGyms({
    initialGyms: markerGyms,
    filtersKey: mapFiltersKey,
    limit: 100,
    maxRadiusKm: Math.max(applied.radiusKm * 2, applied.radiusKm + 1),
  });

  const selectionGyms = useMemo(() => {
    const merged = new Map<number, NearbyGym>();
    items.forEach(gym => merged.set(gym.id, gym));
    visibleGyms.forEach(gym => merged.set(gym.id, gym));
    return Array.from(merged.values());
  }, [items, visibleGyms]);

  const {
    selectedGymId,
    selectedSlug,
    lastSelectionSource,
    lastSelectionAt,
    selectGym,
    clearSelection,
  } = useSelectedGym({ gyms: selectionGyms, requiredGymIds: items.map(gym => gym.id) });
  const clearStore = useMapSelectionStore(state => state.clear);
  const [isDesktop, setIsDesktop] = useState(false);
  const desktopPanelRef = useRef<HTMLDivElement | null>(null);
  const mobilePanelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => () => clearStore(), [clearStore]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const media = window.matchMedia("(min-width: 768px)");
    const update = () => setIsDesktop(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    if (mapMarkersStatus !== "error" || !mapMarkersError) {
      return;
    }
    toast({
      title: "MAP LOAD ERROR",
      description: mapMarkersError,
      variant: "destructive",
    });
  }, [mapMarkersError, mapMarkersStatus, toast]);

  useEffect(() => {
    if (!selectedSlug) {
      return;
    }

    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) {
        return;
      }

      const activePanel = isDesktop ? desktopPanelRef.current : mobilePanelRef.current;
      if (activePanel && activePanel.contains(target)) {
        return;
      }

      if (target instanceof Element && target.closest("[data-panel-anchor]")) {
        return;
      }

      clearSelection();
    };

    window.addEventListener("pointerdown", handlePointerDown);
    return () => window.removeEventListener("pointerdown", handlePointerDown);
  }, [clearSelection, isDesktop, selectedSlug]);

  const hasRequestedLocationRef = useRef(false);
  useEffect(() => {
    if (hasRequestedLocationRef.current) {
      return;
    }
    if (location.hasExplicitLocation) {
      hasRequestedLocationRef.current = true;
      return;
    }
    if (!location.isSupported) {
      return;
    }
    hasRequestedLocationRef.current = true;
    requestCurrentLocation();
  }, [location.hasExplicitLocation, location.isSupported, requestCurrentLocation]);

  const lastToastMessageRef = useRef<string | null>(null);
  useEffect(() => {
    if (location.status !== "error" || !location.error) {
      lastToastMessageRef.current = null;
      return;
    }
    if (lastToastMessageRef.current === location.error) {
      return;
    }
    lastToastMessageRef.current = location.error;
    toast({
      title: "LOCATION ERROR",
      description: location.error,
      variant: "destructive",
    });
  }, [location.error, location.status, toast]);

  const handleSelect = useCallback(
    (gymId: number | null, source: MapInteractionSource = "map") => {
      if (gymId !== null && source === "map") {
        const targetGym = selectionGyms.find(gym => gym.id === gymId);
        if (targetGym) {
          logPinClick({ source: "map", slug: targetGym.slug });
        }
      }
      selectGym(gymId, source);
    },
    [selectGym, selectionGyms],
  );

  const handleSelectFromList = useCallback(
    (gymId: number, source: MapInteractionSource = "list") => {
      handleSelect(gymId, source);
    },
    [handleSelect],
  );

  const handleRequestDetail = useCallback(
    (gym: NearbyGym, source: MapInteractionSource = "list") => {
      handleSelect(gym.id, source);
      const panelNode = isDesktop ? desktopPanelRef.current : mobilePanelRef.current;
      if (panelNode) {
        window.requestAnimationFrame(() => {
          panelNode.scrollIntoView({ behavior: "smooth", block: isDesktop ? "start" : "end" });
        });
      }
    },
    [handleSelect, isDesktop],
  );

  const handleListRequestDetail = useCallback(
    (gym: NearbyGym, _options?: { preferModal?: boolean }) => {
      handleRequestDetail(gym, "list");
    },
    [handleRequestDetail],
  );

  const handleMapCenterChange = useCallback(
    (nextCenter: { lat: number; lng: number }) => {
      updateCenterFromMap(nextCenter);
    },
    [updateCenterFromMap],
  );

  const locationSummary = useMemo(() => {
    if (!location.hasResolvedSupport) {
      return "Checking location support...";
    }
    if (!location.isSupported) {
      return "Location not supported. Please enter coordinates manually.";
    }
    const coordinateLabel = `${applied.lat.toFixed(4)}, ${applied.lng.toFixed(4)}`;
    if (location.status === "loading") {
      return "Acquiring location...";
    }
    if (location.mode === "auto") {
      return `Current Location (${coordinateLabel})`;
    }
    if (location.mode === "map") {
      return `Map Selection (${coordinateLabel})`;
    }
    if (location.mode === "manual") {
      return `Manual Input (${coordinateLabel})`;
    }
    return `URL Specified (${coordinateLabel})`;
  }, [
    applied.lat,
    applied.lng,
    location.hasResolvedSupport,
    location.isSupported,
    location.mode,
    location.status,
  ]);

  const radiusKmLabel = useMemo(() => `~${applied.radiusKm}km`, [applied.radiusKm]);

  const listContainerRef = useRef<HTMLDivElement | null>(null);
  const previousPageRef = useRef(applied.page);
  useEffect(() => {
    if (previousPageRef.current !== applied.page && listContainerRef.current) {
      listContainerRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    previousPageRef.current = applied.page;
  }, [applied.page]);

  return (
    <div className="flex min-h-screen flex-col gap-6 bg-background px-4 pb-16 pt-8 sm:px-6 sm:pt-10 lg:px-8 xl:px-0">
      {/* Background Grid */}
      <div className="fixed inset-0 z-0 bg-grid-pattern opacity-10 pointer-events-none" />

      <div className="relative z-10 mx-auto flex w-full max-w-7xl flex-col gap-8">
        <a
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-accent focus:px-5 focus:py-2 focus:font-mono focus:text-sm focus:font-bold focus:text-accent-foreground"
          href="#nearby-results"
        >
          SKIP TO RESULTS
        </a>

        <header className="space-y-2 border-b border-border pb-6">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 bg-accent" />
            <p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-accent">
              System: Nearby
            </p>
          </div>
          <h1
            className="font-heading text-4xl font-black uppercase tracking-tighter text-foreground sm:text-5xl md:text-6xl"
            role="heading"
            aria-level={1}
          >
            Proximity Scan
          </h1>
          <p className="text-base font-mono text-muted-foreground">
            {"// TARGET: "}
            {radiusKmLabel}
            {" RADIUS FROM CENTER."}
          </p>
        </header>

        <div className="flex flex-col gap-8 md:flex-row">
          <div className="space-y-4 md:w-[320px] md:flex-shrink-0">
            <NearbySearchPanel
              latInput={formState.latInput}
              lngInput={formState.lngInput}
              radiusKm={formState.radiusKm}
              radiusMin={radiusBounds.min}
              radiusMax={radiusBounds.max}
              radiusStep={radiusBounds.step}
              locationSummary={locationSummary}
              locationStatus={location.status}
              locationError={location.error}
              manualError={manualError}
              isLocating={location.status === "loading"}
              hasResolvedLocationSupport={location.hasResolvedSupport}
              isLocationSupported={location.isSupported}
              onLatChange={setLatInput}
              onLngChange={setLngInput}
              onRadiusChange={updateRadius}
              onSubmit={submitManualCoordinates}
              onUseCurrentLocation={requestCurrentLocation}
            />
          </div>

          <div className="flex-1 space-y-6">
            <div className="flex flex-col gap-6 md:flex-row">
              <div className="flex-1 space-y-6">
                <Card className="overflow-hidden rounded-none border-2 border-border bg-card/50 backdrop-blur-sm">
                  <CardHeader className="space-y-1 border-b border-border bg-muted/50 px-6 py-4">
                    <CardTitle
                      className="font-heading text-xl font-bold uppercase tracking-wide"
                      role="heading"
                      aria-level={2}
                    >
                      Tactical Map
                    </CardTitle>
                    <p className="font-mono text-xs text-muted-foreground">
                      SELECT TARGET TO VIEW INTEL. DRAG TO RE-CENTER.
                    </p>
                  </CardHeader>
                  <CardContent className="p-0">
                    <NearbyMap
                      center={{ lat: applied.lat, lng: applied.lng }}
                      markers={visibleGyms}
                      selectedGymId={selectedGymId}
                      lastSelectionSource={lastSelectionSource}
                      lastSelectionAt={lastSelectionAt}
                      onCenterChange={handleMapCenterChange}
                      onSelect={handleSelect}
                      onViewportChange={updateVisibleViewport}
                      markersStatus={mapMarkersStatus}
                      markersIsLoading={mapMarkersIsLoading}
                      markersIsInitialLoading={mapMarkersIsInitialLoading}
                      markersError={mapMarkersError}
                      onRetryMarkers={reloadVisibleGyms}
                    />
                  </CardContent>
                </Card>

                <div ref={listContainerRef} id="nearby-results">
                  <Card
                    aria-live="polite"
                    className="rounded-none border border-border bg-transparent shadow-none"
                  >
                    <CardHeader className="px-0 pt-0">
                      <CardTitle
                        className="font-heading text-2xl font-bold uppercase tracking-wide"
                        role="heading"
                        aria-level={2}
                      >
                        Detected Targets
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4 px-0">
                      <NearbyList
                        error={error}
                        isInitialLoading={isInitialLoading}
                        isLoading={isLoading}
                        items={items}
                        meta={meta}
                        onOpenDetail={handleListRequestDetail}
                        onPageChange={setPage}
                        onRetry={reload}
                        onSelectGym={handleSelectFromList}
                        selectedGymId={selectedGymId}
                      />
                    </CardContent>
                  </Card>
                </div>
              </div>

              <aside
                aria-live="polite"
                className="hidden md:block md:w-[320px] lg:w-[340px]"
                ref={desktopPanelRef}
                role="complementary"
                tabIndex={-1}
              >
                {selectedSlug ? (
                  <GymDetailPanel
                    className="rounded-none border-2 border-accent bg-card shadow-2xl"
                    onClose={() => {
                      clearSelection();
                    }}
                    slug={selectedSlug}
                  />
                ) : (
                  <div className="flex h-64 flex-col items-center justify-center gap-4 rounded-none border-2 border-dashed border-border/50 bg-card/20 p-6 text-center text-sm text-muted-foreground">
                    <div className="h-12 w-12 rounded-full border-2 border-dashed border-muted-foreground/30" />
                    <p className="font-mono text-xs uppercase tracking-wider">
                      Awaiting Target Selection
                    </p>
                  </div>
                )}
              </aside>
            </div>
          </div>
        </div>
      </div>
      <div
        aria-live="polite"
        className={`md:hidden fixed inset-x-0 bottom-0 z-40 px-0 pb-0 pt-2 transition-transform duration-300 ${
          selectedSlug
            ? "pointer-events-auto translate-y-0"
            : "pointer-events-none translate-y-full"
        }`}
        data-panel-anchor="mobile-panel"
        ref={mobilePanelRef}
      >
        <div className="mx-auto max-w-lg">
          {selectedSlug ? (
            <GymDetailPanel
              className="rounded-t-xl border-t-2 border-accent bg-card shadow-[0_-10px_40px_rgba(0,0,0,0.5)]"
              onClose={() => {
                clearSelection();
              }}
              slug={selectedSlug}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
