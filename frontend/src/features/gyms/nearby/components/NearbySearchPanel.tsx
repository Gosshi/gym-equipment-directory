"use client";

import { FormEvent, useMemo } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";

import { SearchDistanceBadge } from "@/components/search/SearchDistanceBadge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { LocationStatus } from "@/features/gyms/nearby/useNearbySearchController";

export interface NearbySearchPanelProps {
  latInput: string;
  lngInput: string;
  radiusKm: number;
  radiusMin: number;
  radiusMax: number;
  radiusStep: number;
  locationSummary: string;
  locationStatus: LocationStatus;
  locationError: string | null;
  manualError: string | null;
  isLocating: boolean;
  hasResolvedLocationSupport: boolean;
  isLocationSupported: boolean;
  onLatChange: (value: string) => void;
  onLngChange: (value: string) => void;
  onRadiusChange: (value: number) => void;
  onSubmit: () => void;
  onUseCurrentLocation: () => void;
}

export function NearbySearchPanel({
  latInput,
  lngInput,
  radiusKm,
  radiusMin,
  radiusMax,
  radiusStep,
  locationSummary,
  locationStatus,
  locationError,
  manualError,
  isLocating,
  hasResolvedLocationSupport,
  isLocationSupported,
  onLatChange,
  onLngChange,
  onRadiusChange,
  onSubmit,
  onUseCurrentLocation,
}: NearbySearchPanelProps) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  const radiusOptions = useMemo(() => {
    const count = Math.floor((radiusMax - radiusMin) / radiusStep);
    return Array.from({ length: count + 1 }, (_, index) => radiusMin + index * radiusStep).filter(
      value => value >= radiusMin && value <= radiusMax,
    );
  }, [radiusMax, radiusMin, radiusStep]);

  return (
    <form
      aria-label="近隣検索フォーム"
      className="grid gap-4 rounded-lg border bg-card p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-1"
      onSubmit={handleSubmit}
    >
      <div className="space-y-2 sm:col-span-2 lg:col-span-1">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-foreground">検索中心の設定</h3>
          <SearchDistanceBadge distanceKm={radiusKm} />
        </div>
        <p className="flex items-start gap-2 text-xs text-muted-foreground" role="status">
          {locationStatus === "loading" ? (
            <Loader2 aria-hidden="true" className="mt-0.5 h-3.5 w-3.5 animate-spin" />
          ) : null}
          {locationStatus === "error" ? (
            <AlertTriangle aria-hidden="true" className="mt-0.5 h-3.5 w-3.5 text-amber-500" />
          ) : null}
          <span className="break-words">{locationSummary}</span>
        </p>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground" htmlFor="nearby-lat">
          緯度
        </label>
        <input
          autoComplete="off"
          className="h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
          id="nearby-lat"
          inputMode="decimal"
          name="lat"
          onChange={event => onLatChange(event.target.value)}
          placeholder="35.681236"
          value={latInput}
        />
      </div>
      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground" htmlFor="nearby-lng">
          経度
        </label>
        <input
          autoComplete="off"
          className="h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
          id="nearby-lng"
          inputMode="decimal"
          name="lng"
          onChange={event => onLngChange(event.target.value)}
          placeholder="139.767125"
          value={lngInput}
        />
      </div>
      {manualError ? (
        <p className="sm:col-span-2 lg:col-span-1 text-xs text-destructive" role="alert">
          {manualError}
        </p>
      ) : null}

      <div className="space-y-3 sm:col-span-2 lg:col-span-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <label className="text-sm font-medium text-foreground" htmlFor="nearby-radius">
            検索半径（km）
          </label>
          <span className="text-xs text-muted-foreground">地図と一覧の対象範囲を調整します。</span>
        </div>
        <div className="grid gap-2">
          <input
            aria-label="検索半径（キロメートル）"
            className="hidden w-full sm:block"
            id="nearby-radius"
            max={radiusMax}
            min={radiusMin}
            onChange={event => {
              const next = Number.parseInt(event.target.value, 10);
              if (!Number.isNaN(next)) {
                onRadiusChange(next);
              }
            }}
            step={radiusStep}
            type="range"
            value={radiusKm}
          />
          <select
            aria-label="検索半径を選択"
            className={cn(
              "h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring",
              "sm:hidden",
            )}
            onChange={event => {
              const next = Number.parseInt(event.target.value, 10);
              if (!Number.isNaN(next)) {
                onRadiusChange(next);
              }
            }}
            value={radiusKm}
          >
            {radiusOptions.map(option => (
              <option key={option} value={option}>
                半径 {option}km
              </option>
            ))}
          </select>
        </div>
      </div>

      {locationError ? (
        <div
          className="sm:col-span-2 lg:col-span-1 rounded-md border border-amber-300/80 bg-amber-50/70 p-3 text-xs text-amber-700 shadow-sm"
          role="alert"
        >
          <div className="flex items-start gap-2">
            <AlertTriangle aria-hidden="true" className="mt-0.5 h-4 w-4" />
            <span>{locationError}</span>
          </div>
        </div>
      ) : null}

      <div className="flex flex-col gap-2 sm:col-span-2 lg:col-span-1 sm:flex-row">
        <Button className="w-full sm:w-auto" type="submit">
          この座標で検索
        </Button>
        <Button
          className="w-full sm:w-auto"
          disabled={
            isLocating || !hasResolvedLocationSupport || !isLocationSupported
          }
          onClick={event => {
            event.preventDefault();
            onUseCurrentLocation();
          }}
          type="button"
          variant="outline"
        >
          {isLocating ? (
            <span className="flex items-center gap-2">
              <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
              取得中...
            </span>
          ) : (
            "現在地を取得"
          )}
        </Button>
      </div>
    </form>
  );
}
