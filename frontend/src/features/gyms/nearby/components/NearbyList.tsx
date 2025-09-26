"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";

import { Pagination } from "@/components/gyms/Pagination";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { MapInteractionSource } from "@/state/mapSelection";
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
  selectedGymId: number | null;
  onSelectGym: (gymId: number, source?: MapInteractionSource) => void;
  onOpenDetail: (gym: NearbyGym, options?: { preferModal?: boolean }) => void;
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
  selectedGymId,
  onSelectGym,
  onOpenDetail,
}: NearbyListProps) {
  const listRef = useRef<HTMLDivElement | null>(null);
  const itemRefs = useRef(new Map<number, HTMLDivElement>());
  const virtualScrollRef = useRef<HTMLDivElement | null>(null);
  const scrollTimeoutRef = useRef<number | null>(null);
  const shouldVirtualize = items.length > 40;
  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => virtualScrollRef.current,
    estimateSize: () => 148,
    overscan: 6,
  });
  const virtualItems = virtualizer.getVirtualItems();

  useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current !== null) {
        window.clearTimeout(scrollTimeoutRef.current);
        scrollTimeoutRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (shouldVirtualize) {
      itemRefs.current.clear();
      return;
    }
    const activeIds = new Set(items.map(gym => gym.id));
    itemRefs.current.forEach((_, id) => {
      if (!activeIds.has(id)) {
        itemRefs.current.delete(id);
      }
    });
  }, [items, shouldVirtualize]);

  useEffect(() => {
    if (scrollTimeoutRef.current !== null) {
      window.clearTimeout(scrollTimeoutRef.current);
      scrollTimeoutRef.current = null;
    }

    if (selectedGymId === null) {
      return;
    }

    const ids = items.map(gym => gym.id);
    const targetIndex = ids.indexOf(selectedGymId);
    if (targetIndex === -1) {
      return;
    }

    if (shouldVirtualize) {
      virtualizer.scrollToIndex(targetIndex, { align: "center" });
      return;
    }

    const target = itemRefs.current.get(selectedGymId);
    if (!target) {
      return;
    }

    const container = listRef.current ?? target.parentElement;
    if (!container) {
      return;
    }

    const scheduleScroll = () => {
      if (!target.isConnected) {
        return;
      }

      const containerElement = container as HTMLElement;
      const containerRect = containerElement.getBoundingClientRect();
      const itemRect = target.getBoundingClientRect();
      const scrollable =
        Math.ceil(containerElement.scrollHeight) > Math.ceil(containerElement.clientHeight + 1);

      const outsideContainer =
        itemRect.top < containerRect.top || itemRect.bottom > containerRect.bottom;

      const docElement = typeof document !== "undefined" ? document.documentElement : null;
      const viewportHeight = docElement ? window.innerHeight || docElement.clientHeight : 0;
      const outsideViewport = viewportHeight
        ? itemRect.top < 0 || itemRect.bottom > viewportHeight
        : false;

      const shouldScroll = scrollable ? outsideContainer : outsideViewport;

      if (shouldScroll) {
        target.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    };

    scrollTimeoutRef.current = window.setTimeout(scheduleScroll, 75);

    return () => {
      if (scrollTimeoutRef.current !== null) {
        window.clearTimeout(scrollTimeoutRef.current);
        scrollTimeoutRef.current = null;
      }
    };
  }, [items, selectedGymId, shouldVirtualize, virtualizer]);

  const renderGymButton = useCallback(
    (gym: NearbyGym, isSelected: boolean) => {
      const prefectureLabel = formatSlug(gym.prefecture);
      const cityLabel = formatSlug(gym.city);
      const areaLabel = [prefectureLabel, cityLabel].filter(Boolean).join(" / ") || "エリア未設定";
      const hasCoordinates = Number.isFinite(gym.latitude) && Number.isFinite(gym.longitude);
      return (
        <button
          className={cn(
            "group flex w-full flex-col rounded-lg border bg-card p-4 text-left shadow-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            isSelected
              ? "border-primary bg-primary/10 shadow-md"
              : "hover:border-primary hover:bg-primary/5",
          )}
          data-state={isSelected ? "selected" : "default"}
          data-panel-anchor="list"
          onClick={() => {
            onSelectGym(gym.id, "list");
            logPinClick({ source: "list", slug: gym.slug });
          }}
          type="button"
        >
          <div className="flex items-center justify-between gap-2">
            <h3
              className={cn(
                "text-base font-semibold text-foreground group-hover:text-primary",
                isSelected ? "text-primary" : undefined,
              )}
            >
              {gym.name}
            </h3>
            <span className="rounded-full bg-secondary px-3 py-1 text-xs text-secondary-foreground">
              {formatDistance(gym.distanceKm)}
            </span>
          </div>
          <p className="text-sm text-muted-foreground">{areaLabel}</p>
          {!hasCoordinates ? (
            <span className="mt-2 inline-flex items-center rounded-full border border-dashed border-border/60 px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              地図非対応
            </span>
          ) : null}
          {gym.lastVerifiedAt ? (
            <p className="mt-2 text-xs text-muted-foreground">
              最終更新: {new Date(gym.lastVerifiedAt).toLocaleDateString()}
            </p>
          ) : null}
        </button>
      );
    },
    [onSelectGym],
  );

  const activeOptionId = useMemo(() => {
    if (selectedGymId !== null && items.some(gym => gym.id === selectedGymId)) {
      return selectedGymId;
    }
    return null;
  }, [items, selectedGymId]);

  const handleKeyDown = useCallback(
    (event: ReactKeyboardEvent<HTMLDivElement>) => {
      if (items.length === 0) {
        return;
      }

      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        const ids = items.map(gym => gym.id);
        const selectedIndex = selectedGymId != null ? ids.indexOf(selectedGymId) : -1;
        const currentIndex = selectedIndex;
        const delta = event.key === "ArrowDown" ? 1 : -1;
        const nextIndex =
          currentIndex === -1
            ? event.key === "ArrowDown"
              ? 0
              : items.length - 1
            : (currentIndex + delta + items.length) % items.length;
        const nextGym = items[nextIndex];
        if (nextGym) {
          onSelectGym(nextGym.id, "list");
          logPinClick({ source: "list", slug: nextGym.slug });
        }
        return;
      }

      if (event.key === "Enter") {
        event.preventDefault();
        const targetGym =
          (selectedGymId != null ? (items.find(gym => gym.id === selectedGymId) ?? null) : null) ??
          items[0];
        if (targetGym) {
          onSelectGym(targetGym.id, "list");
          logPinClick({ source: "list", slug: targetGym.slug });
        }
        return;
      }

      if (event.key === "o" || event.key === "O") {
        event.preventDefault();
        const targetGym =
          selectedGymId != null ? (items.find(gym => gym.id === selectedGymId) ?? null) : null;
        if (targetGym) {
          onSelectGym(targetGym.id, "list");
          onOpenDetail(targetGym, { preferModal: true });
        }
      }
    },
    [items, onOpenDetail, onSelectGym, selectedGymId],
  );

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
      ) : shouldVirtualize ? (
        <div
          aria-activedescendant={activeOptionId ? `gym-option-${activeOptionId}` : undefined}
          aria-label="近隣のジム一覧"
          className="max-h-[70vh] overflow-y-auto focus:outline-none"
          onKeyDown={handleKeyDown}
          ref={node => {
            listRef.current = node;
            virtualScrollRef.current = node;
          }}
          role="listbox"
          tabIndex={0}
        >
          <div
            style={{
              height: `${virtualizer.getTotalSize()}px`,
              position: "relative",
              width: "100%",
            }}
          >
            {virtualItems.map(virtualRow => {
              const gym = items[virtualRow.index];
              const isSelected = selectedGymId === gym.id;
              return (
                <div
                  key={gym.id}
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    transform: `translateY(${virtualRow.start}px)`,
                    height: `${virtualRow.size}px`,
                  }}
                >
                  <div
                    aria-selected={isSelected}
                    className="mb-3 last:mb-0"
                    data-testid={`gym-item-${gym.id}`}
                    id={`gym-option-${gym.id}`}
                    role="option"
                  >
                    {renderGymButton(gym, isSelected)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div
          aria-activedescendant={activeOptionId ? `gym-option-${activeOptionId}` : undefined}
          aria-label="近隣のジム一覧"
          className="focus:outline-none"
          onKeyDown={handleKeyDown}
          ref={node => {
            listRef.current = node;
            virtualScrollRef.current = null;
          }}
          role="listbox"
          tabIndex={0}
        >
          {items.map(gym => {
            const isSelected = selectedGymId === gym.id;
            return (
              <div
                aria-selected={isSelected}
                className="mb-3 last:mb-0"
                data-testid={`gym-item-${gym.id}`}
                id={`gym-option-${gym.id}`}
                key={gym.id}
                ref={node => {
                  if (node) {
                    itemRefs.current.set(gym.id, node);
                  } else {
                    itemRefs.current.delete(gym.id);
                  }
                }}
                role="option"
              >
                {renderGymButton(gym, isSelected)}
              </div>
            );
          })}
        </div>
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
