"use client";

import Link from "next/link";

import { Pagination } from "@/components/gyms/Pagination";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useMapSelectionStore } from "@/state/mapSelection";
import type { NearbyGym } from "@/types/gym";

const logPinClick = (payload: Record<string, unknown>) => {
  if (typeof window !== "undefined" && process.env.NODE_ENV !== "test") {
    // eslint-disable-next-line no-console
    console.debug("pin_click", payload);
  }
};

const formatSlug = (value: string | null | undefined) => {
  if (!value) {
    return null;
  }
  return value
    .split("-")
    .filter(Boolean)
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
};

export interface NearbyListProps {
  items: NearbyGym[];
  onRetry: () => void;
  onPageChange: (page: number) => void;
  meta: {
    total: number;
    page: number;
    pageSize: number;
    hasMore: boolean;
    hasPrev: boolean;
  };
  isLoading: boolean;
  isInitialLoading: boolean;
  error: string | null;
}

const formatDistance = (distanceKm: number) => {
  if (distanceKm < 1) {
    return `${Math.round(distanceKm * 1000)}m`;
  }
  return `${distanceKm.toFixed(1)}km`;
};

const NearbySkeleton = () => (
  <div aria-hidden className="space-y-3" role="presentation">
    {Array.from({ length: 5 }).map((_, index) => (
      <Card key={index} className="border border-dashed">
        <CardHeader className="space-y-2">
          <Skeleton className="h-5 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-4 w-1/2" />
        </CardContent>
      </Card>
    ))}
  </div>
);

const NearbyEmptyState = () => (
  <Card>
    <CardHeader>
      <CardTitle className="text-base">近隣のジムが見つかりませんでした</CardTitle>
    </CardHeader>
    <CardContent className="space-y-2 text-sm text-muted-foreground">
      <p>検索範囲を広げるか、地図をドラッグして別の地点をお試しください。</p>
      <ul className="list-disc space-y-1 pl-5">
        <li>半径スライダーを広げる</li>
        <li>地図を移動して中心地点を変更する</li>
        <li>緯度・経度を直接入力して検索する</li>
      </ul>
    </CardContent>
  </Card>
);

export function NearbyList({
  items,
  onRetry,
  onPageChange,
  meta,
  isLoading,
  isInitialLoading,
  error,
}: NearbyListProps) {
  const hoveredId = useMapSelectionStore(state => state.hoveredId);
  const setHovered = useMapSelectionStore(state => state.setHovered);
  const setSelected = useMapSelectionStore(state => state.setSelected);

  if (isInitialLoading) {
    return <NearbySkeleton />;
  }

  if (error) {
    return (
      <div className="space-y-3 rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
        <p>{error}</p>
        <Button onClick={onRetry} type="button" variant="outline">
          再試行する
        </Button>
      </div>
    );
  }

  const hasResults = items.length > 0;
  if (!hasResults && !isLoading) {
    return <NearbyEmptyState />;
  }

  const perPage = Math.max(meta.pageSize, 1);
  const currentPage = Math.max(meta.page, 1);
  const rangeStart = hasResults ? (currentPage - 1) * perPage + 1 : 0;
  const rangeEnd = hasResults ? rangeStart + items.length - 1 : 0;
  const hasExactTotal = meta.total > 0;
  const totalPages = hasExactTotal
    ? Math.max(Math.ceil(meta.total / perPage), currentPage)
    : Math.max(currentPage, meta.hasMore ? currentPage + 1 : currentPage);
  const summaryLabel = isLoading
    ? "検索結果を読み込み中です…"
    : hasExactTotal
      ? `全${meta.total}件中${rangeStart}–${rangeEnd}件目`
      : hasResults
        ? `${rangeStart}–${rangeEnd}件目`
        : "0件";

  return (
    <div className="space-y-4" aria-busy={isLoading} aria-live="polite">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
        <p className="text-sm font-medium text-foreground">{summaryLabel}</p>
        {hasExactTotal ? (
          <span className="text-xs text-muted-foreground">
            ページ {currentPage} / {totalPages}
          </span>
        ) : null}
      </div>

      {isLoading ? (
        <NearbySkeleton />
      ) : (
        <ul className="space-y-3">
          {items.map(gym => {
            const isHighlighted = hoveredId === gym.id;
            const prefectureLabel = formatSlug(gym.prefecture);
            const cityLabel = formatSlug(gym.city);
            const areaLabel =
              [prefectureLabel, cityLabel].filter(Boolean).join(" / ") || "エリア未設定";
            return (
              <li key={gym.id}>
                <Link
                  className={cn(
                    "group block rounded-lg border bg-card p-4 text-left shadow-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    isHighlighted
                      ? "border-primary bg-primary/5"
                      : "hover:border-primary hover:bg-primary/5",
                  )}
                  href={`/gyms/${gym.slug}`}
                  onBlur={() => setHovered(null)}
                  onClick={() => {
                    setSelected(gym.id);
                    logPinClick({ source: "list", slug: gym.slug });
                  }}
                  onFocus={() => setHovered(gym.id)}
                  onMouseEnter={() => setHovered(gym.id)}
                  onMouseLeave={() => setHovered(null)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="text-base font-semibold text-foreground group-hover:text-primary">
                      {gym.name}
                    </h3>
                    <span className="rounded-full bg-secondary px-3 py-1 text-xs text-secondary-foreground">
                      {formatDistance(gym.distanceKm)}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">{areaLabel}</p>
                  {gym.lastVerifiedAt ? (
                    <p className="mt-2 text-xs text-muted-foreground">
                      最終更新: {new Date(gym.lastVerifiedAt).toLocaleDateString()}
                    </p>
                  ) : null}
                </Link>
              </li>
            );
          })}
        </ul>
      )}

      <div className="border-t border-border/60 pt-4">
        <Pagination
          currentPage={currentPage}
          totalPages={Math.max(totalPages, 1)}
          hasNextPage={meta.hasMore}
          onChange={onPageChange}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}
