"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { GymDetailModal } from "@/components/gym/GymDetailModal";
import { GymDetailPanel } from "@/components/gyms/GymDetailPanel";
import { GymList } from "@/components/gyms/GymList";
import { MapView } from "@/components/gyms/MapView";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useGymDirectoryData } from "@/hooks/useGymDirectoryData";
import { useUrlSync } from "@/hooks/useUrlSync";
import { getEquipmentCategories } from "@/services/meta";
import { useGymSearchStore } from "@/store/searchStore";
import type { SortOption } from "@/lib/searchParams";
import type { GymSearchMeta, GymSummary, NearbyGym } from "@/types/gym";
import type { EquipmentCategoryOption } from "@/types/meta";

const CATEGORY_ALL_VALUE = "__all";

const SORT_LABELS: Record<string, string> = {
  distance: "距離が近い順",
  rating: "評価が高い順",
  reviews: "口コミが多い順",
  name: "名前順",
};

const SORT_OPTIONS: SortOption[] = ["distance", "rating", "reviews", "name"];

const DEFAULT_META: GymSearchMeta = {
  total: null,
  page: 1,
  perPage: 20,
  hasNext: false,
  hasPrev: false,
  hasMore: false,
};

export function GymsPage() {
  useUrlSync();

  const { searchQuery, mapQuery } = useGymDirectoryData();

  const { q, category, sort, page, limit, selectedGymSlug, rightPanelOpen } = useGymSearchStore(
    state => ({
      q: state.q,
      category: state.category,
      sort: state.sort,
      page: state.page,
      limit: state.limit,
      selectedGymSlug: state.selectedGymSlug,
      rightPanelOpen: state.rightPanelOpen,
    }),
  );

  const setQuery = useGymSearchStore(state => state.setQuery);
  const setCategory = useGymSearchStore(state => state.setCategory);
  const setSort = useGymSearchStore(state => state.setSort);
  const setPage = useGymSearchStore(state => state.setPagination);
  const setLimit = useGymSearchStore(state => state.setLimit);
  const setSelectedGym = useGymSearchStore(state => state.setSelectedGym);
  const setRightPanelOpenState = useGymSearchStore(state => state.setRightPanelOpen);
  const resetFilters = useGymSearchStore(state => state.resetFilters);
  const resetSelectionIfMissing = useGymSearchStore(state => state.resetSelectionIfMissing);
  const setTotalPages = useGymSearchStore(state => state.setTotalPages);

  const gyms = useMemo<GymSummary[]>(() => searchQuery.data?.items ?? [], [searchQuery.data]);
  const effectiveMeta: GymSearchMeta = useMemo(() => {
    if (searchQuery.data?.meta) {
      const meta = { ...searchQuery.data.meta };
      const perPage = meta.perPage > 0 ? meta.perPage : limit;
      return { ...meta, perPage };
    }
    return { ...DEFAULT_META, page, perPage: limit };
  }, [limit, page, searchQuery.data]);

  const searchError = searchQuery.error
    ? searchQuery.error instanceof Error
      ? searchQuery.error.message
      : String(searchQuery.error)
    : null;

  const isInitialLoading = searchQuery.isLoading;
  const isLoading = searchQuery.isFetching;

  useEffect(() => {
    if (!searchQuery.data) {
      return;
    }
    const responseMeta = searchQuery.data.meta;
    const perPage = responseMeta.perPage > 0 ? responseMeta.perPage : limit;
    let totalPages: number | null = null;
    if (typeof responseMeta.total === "number" && responseMeta.total >= 0) {
      totalPages = Math.max(1, Math.ceil(responseMeta.total / Math.max(perPage, 1)));
    } else if (!responseMeta.hasNext && responseMeta.page > 0) {
      totalPages = responseMeta.page;
    }
    setTotalPages(totalPages);
  }, [limit, searchQuery.data, setTotalPages]);

  const [categoryOptions, setCategoryOptions] = useState<EquipmentCategoryOption[]>([]);

  useEffect(() => {
    let cancelled = false;
    getEquipmentCategories()
      .then(options => {
        if (!cancelled) {
          setCategoryOptions(options);
        }
      })
      .catch(error => {
        if (!cancelled && process.env.NODE_ENV !== "production") {
          // eslint-disable-next-line no-console
          console.info("Failed to load equipment categories", error);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const mapMarkers = useMemo<NearbyGym[]>(
    () =>
      (mapQuery.data?.items ?? []).filter(
        marker => Number.isFinite(marker.latitude) && Number.isFinite(marker.longitude),
      ),
    [mapQuery.data?.items],
  );

  useEffect(() => {
    const slugSet = new Set<string>();
    gyms.forEach(gym => slugSet.add(gym.slug));
    mapMarkers.forEach(marker => slugSet.add(marker.slug));
    resetSelectionIfMissing(slugSet);
  }, [gyms, mapMarkers, resetSelectionIfMissing]);

  const mapStatus: "idle" | "loading" | "success" | "error" =
    mapQuery.status === "pending"
      ? "loading"
      : mapQuery.status === "error"
        ? "error"
        : mapQuery.status === "success"
          ? "success"
          : "idle";

  const mapError = mapQuery.error
    ? mapQuery.error instanceof Error
      ? mapQuery.error.message
      : String(mapQuery.error)
    : null;

  const mapInitialLoading = mapQuery.status === "pending" && !mapQuery.data;

  const handleSelectGym = useCallback(
    (slug: string) => {
      const gym = gyms.find(item => item.slug === slug) ?? null;
      setSelectedGym({ slug, id: gym?.id ?? null, source: "list" });
    },
    [gyms, setSelectedGym],
  );

  const handleClosePanel = useCallback(() => {
    setRightPanelOpenState(false);
    setSelectedGym({ slug: null, id: null, source: "panel" });
  }, [setRightPanelOpenState, setSelectedGym]);

  const handleResetFilters = useCallback(() => {
    resetFilters();
  }, [resetFilters]);

  return (
    <div className="flex min-h-screen w-full flex-col bg-muted/10">
      <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 px-4 pb-16 pt-8 sm:gap-10 sm:pt-12 lg:px-6 xl:px-0">
        <header className="space-y-3 sm:space-y-4">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground sm:text-sm">
            Gym Directory
          </p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">ジム一覧・検索</h1>
          <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground sm:text-base">
            検索条件と地図の表示範囲が URL
            と同期されるため、共有や戻る/進む操作でも同じ状態を再現できます。
          </p>
        </header>

        <form
          className="grid gap-4 rounded-2xl border border-border/70 bg-card/90 p-5 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/70 md:grid-cols-3"
          onSubmit={event => event.preventDefault()}
        >
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground" htmlFor="gym-search-q">
              キーワード
            </label>
            <Input
              autoComplete="off"
              id="gym-search-q"
              placeholder="設備や施設名で検索"
              value={q}
              onChange={event => setQuery(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label
              className="text-sm font-medium text-muted-foreground"
              htmlFor="gym-search-category"
            >
              カテゴリ
            </label>
            <Select
              value={category ? category : CATEGORY_ALL_VALUE}
              onValueChange={value => setCategory(value === CATEGORY_ALL_VALUE ? "" : value)}
            >
              <SelectTrigger id="gym-search-category">
                <SelectValue placeholder="すべて" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={CATEGORY_ALL_VALUE}>すべて</SelectItem>
                {categoryOptions.map(option => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground" htmlFor="gym-search-sort">
              並び順
            </label>
            <Select value={sort} onValueChange={value => setSort(value as SortOption)}>
              <SelectTrigger id="gym-search-sort">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SORT_OPTIONS.map(option => (
                  <SelectItem key={option} value={option}>
                    {SORT_LABELS[option]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="md:col-span-3">
            <Button
              className="w-full md:w-auto"
              onClick={handleResetFilters}
              type="button"
              variant="outline"
            >
              フィルタをリセット
            </Button>
          </div>
        </form>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] xl:items-start xl:gap-8">
          <div className="flex flex-col gap-6">
            <GymList
              error={searchError}
              gyms={gyms}
              isInitialLoading={isInitialLoading}
              isLoading={isLoading}
              limit={limit}
              meta={effectiveMeta}
              onClearFilters={handleResetFilters}
              onLimitChange={setLimit}
              onPageChange={nextPage => setPage(nextPage, { history: "push" })}
              onRetry={() => searchQuery.refetch()}
              page={page}
              onGymSelect={handleSelectGym}
              selectedSlug={selectedGymSlug ?? undefined}
            />
          </div>

          <div className="flex flex-col gap-6">
            <div className="h-[420px] overflow-hidden rounded-2xl border border-border/70 bg-card shadow-sm">
              <MapView
                markers={mapMarkers}
                status={mapStatus}
                error={mapError}
                isInitialLoading={mapInitialLoading}
                onRetry={mapQuery.isError ? () => mapQuery.refetch() : undefined}
              />
            </div>
            {rightPanelOpen && selectedGymSlug ? (
              <GymDetailPanel slug={selectedGymSlug} onClose={handleClosePanel} />
            ) : null}
          </div>
        </div>
      </div>
      <GymDetailModal
        open={rightPanelOpen && Boolean(selectedGymSlug)}
        onOpenChange={setRightPanelOpenState}
        onRequestClose={handleClosePanel}
        slug={selectedGymSlug}
      />
    </div>
  );
}
