"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
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
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
};

export interface NearbyListProps {
  items: NearbyGym[];
  hoveredId: number | null;
  onHover: (id: number | null) => void;
  onRetry: () => void;
  onLoadMore: () => void;
  hasNext: boolean;
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

export function NearbyList({
  items,
  hoveredId,
  onHover,
  onRetry,
  onLoadMore,
  hasNext,
  isLoading,
  isInitialLoading,
  error,
}: NearbyListProps) {
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

  if (items.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">近隣のジムが見つかりませんでした</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          検索範囲を広げるか、座標を変更して再度お試しください。
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <ul className="space-y-3">
        {items.map((gym) => {
          const isHighlighted = hoveredId === gym.id;
          const prefectureLabel = formatSlug(gym.prefecture);
          const cityLabel = formatSlug(gym.city);
          const areaLabel = [prefectureLabel, cityLabel].filter(Boolean).join(" / ") || "エリア未設定";
          return (
            <li key={gym.id}>
              <Link
                className={cn(
                  "group block rounded-lg border bg-card p-4 text-left shadow-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  isHighlighted ? "border-primary bg-primary/5" : "hover:border-primary hover:bg-primary/5",
                )}
                href={`/gyms/${gym.slug}`}
                onBlur={() => onHover(null)}
                onClick={() => logPinClick({ source: "list", slug: gym.slug })}
                onFocus={() => onHover(gym.id)}
                onMouseEnter={() => onHover(gym.id)}
                onMouseLeave={() => onHover(null)}
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
      {hasNext ? (
        <div className="flex justify-center">
          <Button
            disabled={isLoading}
            onClick={onLoadMore}
            type="button"
            variant="outline"
          >
            {isLoading ? "読み込み中..." : "もっと見る"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
