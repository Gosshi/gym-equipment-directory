"use client";

import { useCallback, useEffect, useState } from "react";

import { SearchFilters } from "@/components/gyms/SearchFilters";
import { GymList } from "@/components/gyms/GymList";
import { GymDetailModal } from "@/components/gym/GymDetailModal";
import { useGymSearch } from "@/hooks/useGymSearch";

export function GymsPage() {
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [isDetailModalOpen, setDetailModalOpen] = useState(false);
  const {
    formState,
    updateKeyword,
    updatePrefecture,
    updateCity,
    updateCategories,
    updateSort,
    updateDistance,
    clearFilters,
    submitSearch,
    location,
    requestLocation,
    clearLocation,
    useFallbackLocation,
    setManualLocation,
    page,
    limit,
    setPage,
    setLimit,
    items,
    meta,
    isLoading,
    isInitialLoading,
    error,
    retry,
    prefectures,
    cities,
    equipmentOptions,
    isMetaLoading,
    metaError,
    reloadMeta,
    isCityLoading,
    cityError,
    reloadCities,
  } = useGymSearch();

  const handleSelectGym = useCallback((slug: string) => {
    setSelectedSlug(slug);
    setDetailModalOpen(true);
  }, []);

  const handleClosePanel = useCallback(() => {
    setSelectedSlug(null);
    setDetailModalOpen(false);
  }, []);

  useEffect(() => {
    if (isLoading) {
      return;
    }
    if (items.length === 0) {
      setSelectedSlug(null);
      setDetailModalOpen(false);
      return;
    }
    if (!selectedSlug) {
      return;
    }
    const isSelectedVisible = items.some(item => item.slug === selectedSlug);
    if (!isSelectedVisible) {
      setSelectedSlug(null);
      setDetailModalOpen(false);
    }
  }, [isLoading, items, selectedSlug]);

  useEffect(() => {
    if (!selectedSlug) {
      setDetailModalOpen(false);
    }
  }, [selectedSlug]);

  const [isDesktop, setIsDesktop] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(min-width: 1024px)");
    setIsDesktop(media.matches);
    const listener = (e: MediaQueryListEvent) => setIsDesktop(e.matches);
    media.addEventListener("change", listener);
    return () => media.removeEventListener("change", listener);
  }, []);

  return (
    <div className="flex min-h-screen w-full flex-col bg-background">
      {/* Background Grid */}
      <div className="fixed inset-0 z-0 bg-grid-pattern opacity-10 pointer-events-none" />

      <div className="relative z-10 mx-auto flex w-full max-w-7xl flex-1 flex-col gap-8 px-4 pb-16 pt-8 sm:px-6 lg:px-8">
        <a
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-accent focus:px-5 focus:py-2 focus:font-mono focus:text-sm focus:font-bold focus:text-accent-foreground"
          href="#gym-search-results"
        >
          SKIP TO RESULTS
        </a>

        <header className="space-y-2 border-b border-border pb-6">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 bg-accent" />
            <p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-accent">
              ジム検索
            </p>
          </div>
          <h1
            className="font-heading text-4xl font-black uppercase tracking-tighter text-foreground sm:text-5xl md:text-6xl"
            role="heading"
            aria-level={1}
          >
            ジム一覧
          </h1>
          <p className="max-w-3xl font-mono text-sm text-muted-foreground">
            {"// 設備・エリア・距離で絞り込み"}
          </p>
        </header>

        <div className="grid gap-8 lg:grid-cols-[320px_1fr] lg:items-start">
          {isDesktop ? (
            <aside className="sticky top-24 z-20 hidden lg:block">
              <SearchFilters
                categories={equipmentOptions}
                cities={cities}
                cityError={cityError}
                isCityLoading={isCityLoading}
                isMetaLoading={isMetaLoading}
                metaError={metaError}
                isSearchLoading={isLoading}
                onCategoriesChange={updateCategories}
                onCityChange={updateCity}
                onClear={clearFilters}
                onDistanceChange={updateDistance}
                onKeywordChange={updateKeyword}
                onPrefectureChange={updatePrefecture}
                onRequestLocation={requestLocation}
                onUseFallbackLocation={useFallbackLocation}
                onClearLocation={clearLocation}
                onManualLocationChange={setManualLocation}
                onReloadCities={reloadCities}
                onReloadMeta={reloadMeta}
                onSortChange={updateSort}
                onSubmitSearch={submitSearch}
                location={location}
                prefectures={prefectures}
                state={formState}
              />
            </aside>
          ) : (
            <div className="lg:hidden">
              <SearchFilters
                categories={equipmentOptions}
                cities={cities}
                cityError={cityError}
                isCityLoading={isCityLoading}
                isMetaLoading={isMetaLoading}
                metaError={metaError}
                isSearchLoading={isLoading}
                onCategoriesChange={updateCategories}
                onCityChange={updateCity}
                onClear={clearFilters}
                onDistanceChange={updateDistance}
                onKeywordChange={updateKeyword}
                onPrefectureChange={updatePrefecture}
                onRequestLocation={requestLocation}
                onUseFallbackLocation={useFallbackLocation}
                onClearLocation={clearLocation}
                onManualLocationChange={setManualLocation}
                onReloadCities={reloadCities}
                onReloadMeta={reloadMeta}
                onSortChange={updateSort}
                onSubmitSearch={submitSearch}
                location={location}
                prefectures={prefectures}
                state={formState}
              />
            </div>
          )}

          <div className="flex flex-col gap-6 min-w-0">
            <GymList
              error={error}
              gyms={items}
              isInitialLoading={isInitialLoading}
              isLoading={isLoading}
              limit={limit}
              meta={meta}
              onClearFilters={clearFilters}
              onLimitChange={setLimit}
              onPageChange={setPage}
              onRetry={retry}
              page={page}
              onGymSelect={handleSelectGym}
              selectedSlug={selectedSlug}
            />
          </div>
        </div>
      </div>
      <GymDetailModal
        open={isDetailModalOpen && Boolean(selectedSlug)}
        onOpenChange={setDetailModalOpen}
        onRequestClose={handleClosePanel}
        slug={selectedSlug}
      />
    </div>
  );
}
