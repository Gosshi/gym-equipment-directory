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
    () =>
      items.filter(
        gym => Number.isFinite(gym.latitude) && Number.isFinite(gym.longitude),
      ),
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
  } = useSelectedGym({ gyms: selectionGyms });
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
      title: "地図の読み込みに失敗しました",
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
      title: "位置情報を取得できませんでした",
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
      return "位置情報の利用可否を確認しています…";
    }
    if (!location.isSupported) {
      return "この環境では位置情報を取得できません。緯度・経度を入力してください。";
    }
    const coordinateLabel = `${applied.lat.toFixed(4)}, ${applied.lng.toFixed(4)}`;
    if (location.status === "loading") {
      return "現在地を取得しています…";
    }
    if (location.mode === "auto") {
      return `現在地を使用中（${coordinateLabel}）`;
    }
    if (location.mode === "map") {
      return `地図で選択した地点（${coordinateLabel}）`;
    }
    if (location.mode === "manual") {
      return `手入力した地点（${coordinateLabel}）`;
    }
    return `URLで指定された地点（${coordinateLabel}）`;
  }, [
    applied.lat,
    applied.lng,
    location.hasResolvedSupport,
    location.isSupported,
    location.mode,
    location.status,
  ]);

  const radiusKmLabel = useMemo(() => `約${applied.radiusKm}km`, [applied.radiusKm]);

  const listContainerRef = useRef<HTMLDivElement | null>(null);
  const previousPageRef = useRef(applied.page);
  useEffect(() => {
    if (previousPageRef.current !== applied.page && listContainerRef.current) {
      listContainerRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    previousPageRef.current = applied.page;
  }, [applied.page]);

  return (
    <div className="flex min-h-screen flex-col gap-6 px-4 py-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <header className="space-y-2">
          <p className="text-sm font-medium text-primary">ジムを探す</p>
          <h1 className="text-3xl font-bold text-foreground">近隣ジムをマップでチェック</h1>
          <p className="text-base text-muted-foreground">
            現在地または任意の座標を中心に、半径 {radiusKmLabel} のジムを表示します。
          </p>
        </header>

        <div className="flex flex-col gap-6 md:flex-row">
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
              <div className="flex-1 space-y-4">
                <Card className="overflow-hidden">
                  <CardHeader className="space-y-1">
                    <CardTitle className="text-lg font-semibold">地図</CardTitle>
                    <p className="text-sm text-muted-foreground">
                      ピンを選択すると右側の詳細パネルが開きます。ドラッグで中心地点を調整できます。
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

                <div ref={listContainerRef}>
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg font-semibold">近隣のジム一覧</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
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
                    className="shadow-lg"
                    onClose={() => {
                      clearSelection();
                    }}
                    slug={selectedSlug}
                  />
                ) : (
                  <div className="rounded-2xl border border-dashed border-border/60 bg-card/40 p-6 text-sm text-muted-foreground">
                    <p>地図上のピンまたは一覧からジムを選択すると詳細が表示されます。</p>
                  </div>
                )}
              </aside>
            </div>
          </div>
        </div>
      </div>
      <div
        aria-live="polite"
        className={`md:hidden fixed inset-x-0 bottom-0 z-40 px-4 pb-4 pt-2 transition-transform duration-300 ${
          selectedSlug ? "pointer-events-auto translate-y-0" : "pointer-events-none translate-y-full"
        }`}
        data-panel-anchor="mobile-panel"
        ref={mobilePanelRef}
      >
        <div className="mx-auto max-w-lg">
          {selectedSlug ? (
            <GymDetailPanel
              className="rounded-3xl border border-border/70 bg-card shadow-xl"
              onClose={() => {
                clearSelection();
              }}
              slug={selectedSlug}
            />
          ) : (
            <div className="rounded-3xl border border-dashed border-border/60 bg-card/80 p-6 text-sm text-muted-foreground shadow">
              <p>地図上のピンを選択すると詳細が表示されます。</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
