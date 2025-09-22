"use client";

import { FormEvent } from "react";

import { Button } from "@/components/ui/button";

export interface NearbySearchPanelProps {
  latInput: string;
  lngInput: string;
  radiusInput: string;
  isLocating: boolean;
  onLatChange: (value: string) => void;
  onLngChange: (value: string) => void;
  onRadiusChange: (value: string) => void;
  onSubmit: () => void;
  onUseCurrentLocation: () => void;
  errorMessage: string | null;
}

export function NearbySearchPanel({
  latInput,
  lngInput,
  radiusInput,
  isLocating,
  onLatChange,
  onLngChange,
  onRadiusChange,
  onSubmit,
  onUseCurrentLocation,
  errorMessage,
}: NearbySearchPanelProps) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <form
      aria-label="近隣検索フォーム"
      className="grid gap-4 rounded-lg border bg-card p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-1"
      onSubmit={handleSubmit}
    >
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
          onChange={(event) => onLatChange(event.target.value)}
          placeholder="35.681236"
          required
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
          onChange={(event) => onLngChange(event.target.value)}
          placeholder="139.767125"
          required
          value={lngInput}
        />
      </div>
      <div className="space-y-2 sm:col-span-2 lg:col-span-1">
        <label className="text-sm font-medium text-foreground" htmlFor="nearby-radius">
          検索半径 (メートル)
        </label>
        <input
          className="h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
          id="nearby-radius"
          inputMode="numeric"
          name="radius"
          onChange={(event) => onRadiusChange(event.target.value)}
          placeholder="3000"
          value={radiusInput}
        />
      </div>
      {errorMessage ? (
        <p className="sm:col-span-2 lg:col-span-1 text-sm text-destructive" role="alert">
          {errorMessage}
        </p>
      ) : null}
      <div className="flex flex-col gap-2 sm:col-span-2 lg:col-span-1 sm:flex-row">
        <Button className="w-full sm:w-auto" type="submit">
          この座標で検索
        </Button>
        <Button
          className="w-full sm:w-auto"
          disabled={isLocating}
          onClick={(event) => {
            event.preventDefault();
            onUseCurrentLocation();
          }}
          type="button"
          variant="outline"
        >
          {isLocating ? "現在地取得中..." : "現在地を使用"}
        </Button>
      </div>
    </form>
  );
}
