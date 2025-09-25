"use client";

import { useId, useMemo } from "react";

import Image from "next/image";

import { Navigation2, Star, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export interface GymPopupData {
  id: number;
  slug: string;
  name: string;
  latitude?: number | null;
  longitude?: number | null;
  prefecture?: string | null;
  city?: string | null;
  address?: string | null;
  distanceKm?: number | null;
  thumbnailUrl?: string | null;
  categories?: string[] | null;
  rating?: number | null;
}

export type GymPopupMode = "preview" | "selected";

export interface GymPopupProps {
  data: GymPopupData;
  mode: GymPopupMode;
  isLoading?: boolean;
  onClose: () => void;
  onViewDetail: () => void;
}

const FALLBACK_IMAGE =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160' viewBox='0 0 160 160'%3E%3Crect fill='%23e4e4e7' width='160' height='160' rx='20'/%3E%3Cpath d='M53 128l18-24 26 16 22-28 14 20v24H53z' fill='%23d4d4d8'/%3E%3Ccircle cx='66' cy='62' r='18' fill='%23d4d4d8'/%3E%3C/svg%3E";

const formatDistance = (distanceKm: number | null | undefined) => {
  if (distanceKm == null) {
    return "距離情報なし";
  }
  if (distanceKm < 1) {
    return `${Math.round(distanceKm * 1000)}m`;
  }
  return `${distanceKm.toFixed(1)}km`;
};

const buildRouteHref = (lat?: number | null, lng?: number | null) => {
  if (lat == null || lng == null) {
    return null;
  }
  const preciseLat = lat.toFixed(6);
  const preciseLng = lng.toFixed(6);
  return `https://www.google.com/maps/dir/?api=1&destination=${preciseLat},${preciseLng}`;
};

const resolveAddress = (data: GymPopupData) => {
  if (data.address && data.address.trim()) {
    return data.address.trim();
  }
  const parts = [data.prefecture, data.city]
    .map(value => value?.trim())
    .filter((value): value is string => Boolean(value));
  return parts.length > 0 ? parts.join(" ") : "住所情報が登録されていません";
};

const resolveImageSrc = (thumbnailUrl?: string | null) =>
  typeof thumbnailUrl === "string" && thumbnailUrl.trim() ? thumbnailUrl : FALLBACK_IMAGE;

const resolveCategories = (categories?: string[] | null) => {
  if (!categories) {
    return [];
  }
  return categories
    .map(category => category?.trim())
    .filter((category): category is string => Boolean(category));
};

export function GymPopup({ data, mode, isLoading = false, onClose, onViewDetail }: GymPopupProps) {
  const labelId = useId();
  const descriptionId = useId();

  const addressLabel = useMemo(() => resolveAddress(data), [data]);
  const imageSrc = useMemo(() => resolveImageSrc(data.thumbnailUrl), [data.thumbnailUrl]);
  const routeHref = useMemo(() => buildRouteHref(data.latitude, data.longitude), [
    data.latitude,
    data.longitude,
  ]);
  const categories = useMemo(() => resolveCategories(data.categories), [data.categories]);
  const distanceLabel = useMemo(() => formatDistance(data.distanceKm ?? null), [data.distanceKm]);
  const categoryChips = useMemo(() => {
    if (isLoading) {
      return [];
    }
    return categories.length > 0 ? categories.slice(0, 3) : ["カテゴリ準備中"];
  }, [categories, isLoading]);

  return (
    <div
      aria-describedby={descriptionId}
      aria-labelledby={labelId}
      aria-live="polite"
      className={cn(
        "w-[320px] max-w-[85vw] rounded-2xl border bg-background/95 p-4 text-foreground shadow-lg backdrop-blur-sm supports-[backdrop-filter]:bg-background/80",
        "ring-1 ring-border",
        mode === "selected" ? "ring-primary/70 shadow-xl" : "ring-border/80",
      )}
      data-mode={mode}
      role="dialog"
      tabIndex={-1}
      onKeyDown={event => {
        if (event.key === "Escape") {
          event.stopPropagation();
          onClose();
        }
      }}
    >
      <div className="flex items-start gap-4">
        <div className="relative h-20 w-20 overflow-hidden rounded-xl border border-border/70 bg-muted">
          {isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : (
            <Image
              alt={`${data.name}のサムネイル`}
              className="h-full w-full object-cover"
              height={80}
              src={imageSrc}
              unoptimized={imageSrc === FALLBACK_IMAGE}
              width={80}
            />
          )}
        </div>
        <div className="flex-1 space-y-2">
          <div className="flex items-start justify-between gap-2">
            <div className="max-w-[200px] space-y-1">
              {isLoading ? (
                <Skeleton aria-hidden className="h-6 w-32" />
              ) : (
                <p className="text-base font-semibold leading-tight" id={labelId}>
                  {data.name}
                </p>
              )}
              <p className="text-xs text-muted-foreground" id={descriptionId}>
                {isLoading ? <Skeleton aria-hidden className="h-4 w-24" /> : addressLabel}
              </p>
            </div>
            <button
              aria-label="ポップアップを閉じる"
              className="rounded-md p-1 text-muted-foreground transition hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              onClick={onClose}
              type="button"
            >
              <X aria-hidden className="h-4 w-4" />
            </button>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Star aria-hidden className="h-3.5 w-3.5 fill-yellow-400 text-yellow-400" />
            {isLoading ? (
              <Skeleton aria-hidden className="h-3 w-16" />
            ) : (
              <span>評価は準備中</span>
            )}
          </div>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {isLoading ? (
          <Skeleton aria-hidden className="h-6 w-24" />
        ) : (
          <span className="inline-flex items-center rounded-full bg-secondary/70 px-3 py-1 text-xs text-secondary-foreground">
            {distanceLabel}
          </span>
        )}
        {isLoading ? (
          <Skeleton aria-hidden className="h-6 w-20" />
        ) : (
          categoryChips.map(category => (
            <Badge key={category} variant="outline">
              {category}
            </Badge>
          ))
        )}
      </div>

      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
        <Button
          className="flex-1"
          onClick={onViewDetail}
          size="sm"
          type="button"
          variant="default"
        >
          詳細を見る
        </Button>
        <Button
          asChild
          className="flex-1"
          disabled={!routeHref}
          size="sm"
          variant="secondary"
        >
          <a href={routeHref ?? "#"} rel="noopener noreferrer" target="_blank">
            <span className="inline-flex items-center gap-2">
              <Navigation2 aria-hidden className="h-4 w-4" />
              ルート表示
            </span>
          </a>
        </Button>
      </div>
    </div>
  );
}
