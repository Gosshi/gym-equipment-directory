"use client";

import { useCallback, useEffect, useMemo } from "react";

import { useShallow } from "zustand/react/shallow";

import { GymDetailModal } from "@/components/gym/GymDetailModal";
import { SearchFilters } from "@/components/gyms/SearchFilters";
import { GymDetailPanel } from "@/components/gyms/GymDetailPanel";
import { GymList } from "@/components/gyms/GymList";
import { MapView } from "@/components/gyms/MapView";
import { useGymDirectoryData } from "@/hooks/useGymDirectoryData";
import { useGymFilterControls } from "@/hooks/useGymFilterControls";
import { useUrlSync } from "@/hooks/useUrlSync";
import { useGymSearchStore } from "@/store/searchStore";
import type { GymSearchMeta, GymSummary, NearbyGym } from "@/types/gym";

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
  const filterControls = useGymFilterControls();

  const { page, limit, selectedGymSlug, rightPanelOpen } = useGymSearchStore(
    useShallow(state => ({
      page: state.page,
      limit: state.limit,
      selectedGymSlug: state.selectedGymSlug,
      rightPanelOpen: state.rightPanelOpen,
    })),
  );

  const setPage = useGymSearchStore(state => state.setPagination);
  const setLimit = useGymSearchStore(state => state.setLimit);
  const setSelectedGym = useGymSearchStore(state => state.setSelectedGym);
  const setRightPanelOpenState = useGymSearchStore(state => state.setRightPanelOpen);
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

        <SearchFilters
          state={filterControls.state}
          prefectures={filterControls.prefectures}
          cities={filterControls.cities}
          categories={filterControls.categories}
          isMetaLoading={filterControls.isMetaLoading}
          isCityLoading={filterControls.isCityLoading}
          metaError={filterControls.metaError}
          cityError={filterControls.cityError}
          location={filterControls.location}
          isSearchLoading={isLoading}
          onKeywordChange={filterControls.onKeywordChange}
          onPrefectureChange={filterControls.onPrefectureChange}
          onCityChange={filterControls.onCityChange}
          onCategoriesChange={filterControls.onCategoriesChange}
          onSortChange={(nextSort, nextOrder) => filterControls.onSortChange(nextSort, nextOrder)}
          onDistanceChange={filterControls.onDistanceChange}
          onClear={filterControls.onClear}
          onRequestLocation={filterControls.onRequestLocation}
          onUseFallbackLocation={filterControls.onUseFallbackLocation}
          onClearLocation={filterControls.onClearLocation}
          onManualLocationChange={filterControls.onManualLocationChange}
          onReloadMeta={filterControls.onReloadMeta}
          onReloadCities={filterControls.onReloadCities}
          onSubmitSearch={() => searchQuery.refetch()}
        />

        <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] xl:items-start xl:gap-8">
          <div className="flex flex-col gap-6">
            <GymList
              error={searchError}
              gyms={gyms}
              isInitialLoading={isInitialLoading}
              isLoading={isLoading}
              limit={limit}
              meta={effectiveMeta}
              onClearFilters={filterControls.onClear}
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
