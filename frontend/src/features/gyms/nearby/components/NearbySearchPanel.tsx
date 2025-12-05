"use client";

import { FormEvent, useMemo } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";

import { SearchDistanceBadge } from "@/components/search/SearchDistanceBadge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { LocationStatus } from "@/features/gyms/nearby/useNearbySearchController";

export interface NearbySearchPanelProps {
  radiusKm: number;
  radiusMin: number;
  radiusMax: number;
  radiusStep: number;
  locationSummary: string;
  locationStatus: LocationStatus;
  locationError: string | null;
  isLocating: boolean;
  hasResolvedLocationSupport: boolean;
  isLocationSupported: boolean;
  onRadiusChange: (value: number) => void;
  onUseCurrentLocation: () => void;
}

export function NearbySearchPanel({
  radiusKm,
  radiusMin,
  radiusMax,
  radiusStep,
  locationSummary,
  locationStatus,
  locationError,
  isLocating,
  hasResolvedLocationSupport,
  isLocationSupported,
  onRadiusChange,
  onUseCurrentLocation,
}: NearbySearchPanelProps) {
  const radiusOptions = useMemo(() => {
    const count = Math.floor((radiusMax - radiusMin) / radiusStep);
    return Array.from({ length: count + 1 }, (_, index) => radiusMin + index * radiusStep).filter(
      value => value >= radiusMin && value <= radiusMax,
    );
  }, [radiusMax, radiusMin, radiusStep]);

  return (
    <div
      aria-label="近隣検索フォーム"
      className="flex flex-col gap-4 rounded-lg border bg-card p-4 shadow-sm md:flex-row md:items-center md:justify-between"
    >
      <div className="flex flex-1 flex-col gap-2 md:flex-row md:items-center md:gap-6">
        <Button
          className="w-full md:w-auto"
          disabled={isLocating || (hasResolvedLocationSupport && !isLocationSupported)}
          onClick={event => {
            event.preventDefault();
            onUseCurrentLocation();
          }}
          type="button"
          variant="default" // Changed to default for prominence
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

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2">
            <label
              className="text-sm font-medium text-foreground whitespace-nowrap"
              htmlFor="nearby-radius"
            >
              検索半径:
            </label>
            <SearchDistanceBadge distanceKm={radiusKm} />
          </div>
          <div className="flex-1 min-w-[120px]">
            <input
              aria-label="検索半径（キロメートル）"
              className="hidden w-full sm:block accent-accent"
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
                "h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring",
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
                  {option}km
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-1 text-right">
        <p
          className="flex items-center justify-end gap-2 text-xs text-muted-foreground"
          role="status"
        >
          {locationStatus === "loading" ? (
            <Loader2 aria-hidden="true" className="h-3.5 w-3.5 animate-spin" />
          ) : null}
          {locationStatus === "error" ? (
            <AlertTriangle aria-hidden="true" className="h-3.5 w-3.5 text-amber-500" />
          ) : null}
          <span className="break-words">{locationSummary}</span>
        </p>
        {locationError ? <p className="text-xs text-destructive">{locationError}</p> : null}
      </div>
    </div>
  );
}
