"use client";

import dynamic from "next/dynamic";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import { MIN_DISTANCE_KM, MAX_DISTANCE_KM } from "@/lib/searchParams";
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

  const hoveredId = useMapSelectionStore(state => state.hoveredId);
  const selectedId = useMapSelectionStore(state => state.selectedId);
  const setHoveredId = useMapSelectionStore(state => state.setHovered);
  const setSelectedId = useMapSelectionStore(state => state.setSelected);
  const clearSelection = useMapSelectionStore(state => state.clear);
  const skipNextUrlSelectionRef = useRef(false);

  useEffect(() => {
    if (skipNextUrlSelectionRef.current) {
      skipNextUrlSelectionRef.current = false;
      return;
    }

    const params = new URLSearchParams(searchParamsSnapshot);
    const raw = params.get("selected");
    if (!raw) {
      return;
    }

    const parsed = Number.parseInt(raw, 10);
    if (!Number.isFinite(parsed)) {
      return;
    }

    if (selectedId === parsed) {
      return;
    }

    setSelectedId(parsed, "url");
  }, [searchParamsSnapshot, selectedId, setSelectedId]);

  useEffect(() => {
    if (!pathname) {
      return;
    }

    const params = new URLSearchParams(searchParamsSnapshot);
    const current = params.get("selected");
    const next = selectedId === null ? null : String(selectedId);

    if (next === null) {
      if (current === null) {
        return;
      }
      params.delete("selected");
    } else if (current === next) {
      return;
    } else {
      params.set("selected", next);
    }

    const query = params.toString();
    const nextUrl = query ? `${pathname}?${query}` : pathname;
    router.replace(nextUrl, { scroll: false });
  }, [pathname, router, searchParamsSnapshot, selectedId]);

  useEffect(() => {
    if (hoveredId === null) {
      return;
    }
    if (!items.some(gym => gym.id === hoveredId)) {
      setHoveredId(null);
    }
  }, [hoveredId, items, setHoveredId]);

  useEffect(() => {
    if (selectedId === null) {
      return;
    }
    if (!items.some(gym => gym.id === selectedId)) {
      skipNextUrlSelectionRef.current = true;
      setSelectedId(null);
    }
  }, [items, selectedId, setSelectedId]);

  useEffect(() => () => clearSelection(), [clearSelection]);

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

  const handleMarkerSelect = useCallback(
    (gym: NearbyGym) => {
      logPinClick({ source: "map", slug: gym.slug });
      router.push(`/gyms/${gym.slug}`);
    },
    [router],
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
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
          <div className="space-y-4">
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
            <Card className="overflow-hidden">
              <CardHeader className="space-y-1">
                <CardTitle className="text-lg font-semibold">地図</CardTitle>
                <p className="text-sm text-muted-foreground">
                  地図をドラッグして中心を変更できます。ピンをクリックすると詳細ページへ移動します。
                </p>
              </CardHeader>
              <CardContent className="p-0">
                <NearbyMap
                  center={{ lat: applied.lat, lng: applied.lng }}
                  markers={items}
                  onCenterChange={handleMapCenterChange}
                  onMarkerSelect={handleMarkerSelect}
                />
              </CardContent>
            </Card>
          </div>
          <aside className="space-y-4" ref={listContainerRef}>
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
                  onPageChange={setPage}
                  onRetry={reload}
                />
              </CardContent>
            </Card>
          </aside>
        </div>
      </div>
    </div>
  );
}
