"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { parseLatLng } from "@/lib/geo";
import type { NearbyGym } from "@/types/gym";

import { NearbyList } from "./components/NearbyList";
import { NearbySearchPanel } from "./components/NearbySearchPanel";
import { useNearbyGyms } from "./useNearbyGyms";

const NearbyMap = dynamic(() => import("./components/NearbyMap").then((mod) => mod.NearbyMap), {
  ssr: false,
});

const FALLBACK_CENTER = { lat: 35.681236, lng: 139.767125 };
const FALLBACK_RADIUS_METERS = 3000;
const MIN_RADIUS_METERS = 500;
const MAX_RADIUS_METERS = 30000;

const logPinClick = (payload: Record<string, unknown>) => {
  if (typeof window !== "undefined" && process.env.NODE_ENV !== "test") {
    // eslint-disable-next-line no-console
    console.debug("pin_click", payload);
  }
};

const resolveDefaultCenter = () => {
  const envValue = process.env.NEXT_PUBLIC_DEFAULT_CENTER;
  if (typeof envValue === "string") {
    const parsed = parseLatLng(envValue);
    if (parsed) {
      return parsed;
    }
  }
  return FALLBACK_CENTER;
};

const resolveDefaultRadius = () => {
  const envValue = process.env.NEXT_PUBLIC_DEFAULT_RADIUS;
  if (typeof envValue === "string") {
    const parsed = Number.parseInt(envValue, 10);
    if (Number.isFinite(parsed) && parsed > 0) {
      return parsed;
    }
  }
  return FALLBACK_RADIUS_METERS;
};

export function NearbyGymsPage() {
  const router = useRouter();
  const defaultCenter = useMemo(() => resolveDefaultCenter(), []);
  const defaultRadius = useMemo(() => resolveDefaultRadius(), []);

  const [center, setCenter] = useState(defaultCenter);
  const [radiusMeters, setRadiusMeters] = useState(defaultRadius);
  const [radiusInput, setRadiusInput] = useState(String(defaultRadius));
  const [latInput, setLatInput] = useState(defaultCenter.lat.toFixed(6));
  const [lngInput, setLngInput] = useState(defaultCenter.lng.toFixed(6));
  const [formError, setFormError] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<number | null>(null);
  const [isLocating, setIsLocating] = useState(false);

  const hasRequestedLocation = useRef(false);

  const { items, isInitialLoading, isLoading, error, hasNext, loadMore, reload } = useNearbyGyms({
    center,
    radiusMeters,
  });

  useEffect(() => {
    if (hoveredId === null) {
      return;
    }
    if (!items.some((gym) => gym.id === hoveredId)) {
      setHoveredId(null);
    }
  }, [hoveredId, items]);

  useEffect(() => {
    setLatInput(center.lat.toFixed(6));
    setLngInput(center.lng.toFixed(6));
  }, [center.lat, center.lng]);

  const handleRadiusChange = useCallback((value: string) => {
    setRadiusInput(value);
    const parsed = Number.parseInt(value, 10);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      return;
    }
    const sanitized = Math.max(MIN_RADIUS_METERS, Math.min(parsed, MAX_RADIUS_METERS));
    setRadiusMeters(sanitized);
    if (sanitized !== parsed) {
      setRadiusInput(String(sanitized));
    }
  }, []);

  const applyCoordinates = useCallback(() => {
    const parsed = parseLatLng(`${latInput},${lngInput}`);
    if (!parsed) {
      setFormError("緯度・経度の形式を確認してください。（例: 35.681236,139.767125）");
      return;
    }
    setFormError(null);
    setCenter(parsed);
    setHoveredId(null);
  }, [latInput, lngInput]);

  const requestCurrentLocation = useCallback(() => {
    if (typeof window === "undefined" || !("geolocation" in window.navigator)) {
      setFormError("ブラウザが現在地取得に対応していません");
      return;
    }
    setIsLocating(true);
    window.navigator.geolocation.getCurrentPosition(
      (position) => {
        setIsLocating(false);
        const coords = {
          lat: Number(position.coords.latitude.toFixed(6)),
          lng: Number(position.coords.longitude.toFixed(6)),
        };
        setCenter(coords);
        setFormError(null);
      },
      (geoError) => {
        setIsLocating(false);
        if (geoError.code === geoError.PERMISSION_DENIED) {
          setFormError("現在地の取得が拒否されました。手動で座標を入力してください。");
        } else {
          setFormError("現在地の取得に失敗しました。通信環境をご確認ください。");
        }
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }, []);

  useEffect(() => {
    if (hasRequestedLocation.current) {
      return;
    }
    hasRequestedLocation.current = true;
    requestCurrentLocation();
  }, [requestCurrentLocation]);

  const handleMapCenterChange = useCallback(
    (nextCenter: { lat: number; lng: number }) => {
      setCenter(nextCenter);
    },
    [],
  );

  const handleMarkerSelect = useCallback(
    (gym: NearbyGym) => {
      logPinClick({ source: "map", slug: gym.slug });
      router.push(`/gyms/${gym.slug}`);
    },
    [router],
  );

  const radiusKmLabel = useMemo(
    () => (radiusMeters >= 1000 ? `${(radiusMeters / 1000).toFixed(1)}km` : `${radiusMeters}m`),
    [radiusMeters],
  );

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
              errorMessage={formError}
              isLocating={isLocating}
              latInput={latInput}
              lngInput={lngInput}
              onLatChange={setLatInput}
              onLngChange={setLngInput}
              onRadiusChange={handleRadiusChange}
              onSubmit={applyCoordinates}
              onUseCurrentLocation={requestCurrentLocation}
              radiusInput={radiusInput}
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
                  center={center}
                  hoveredId={hoveredId}
                  markers={items}
                  onCenterChange={handleMapCenterChange}
                  onMarkerHover={setHoveredId}
                  onMarkerSelect={handleMarkerSelect}
                />
              </CardContent>
            </Card>
          </div>
          <aside className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg font-semibold">近隣のジム一覧</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <NearbyList
                  error={error}
                  hasNext={hasNext}
                  hoveredId={hoveredId}
                  isInitialLoading={isInitialLoading}
                  isLoading={isLoading}
                  items={items}
                  onHover={setHoveredId}
                  onLoadMore={loadMore}
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
