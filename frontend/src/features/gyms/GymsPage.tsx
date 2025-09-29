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
    equipmentCategories,
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

  return (
    <div className="flex min-h-screen w-full flex-col bg-muted/10">
      <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-7 px-4 pb-16 pt-6 sm:gap-10 sm:px-6 sm:pt-10 lg:px-8 xl:px-0">
        <a
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-primary focus:px-5 focus:py-2 focus:text-sm focus:text-primary-foreground focus:shadow-lg"
          href="#gym-search-results"
        >
          検索結果一覧へスキップ
        </a>
        <header className="space-y-3 sm:space-y-4">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground sm:text-sm">
            Gym Directory
          </p>
          <h1
            className="text-3xl font-bold tracking-tight sm:text-4xl"
            role="heading"
            aria-level={1}
          >
            ジム一覧・検索
          </h1>
          <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground sm:text-base">
            設備カテゴリやエリアで絞り込み、URL 共有で同じ検索条件を再現できます。
          </p>
        </header>
        <div className="grid gap-6 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)] lg:items-start xl:grid-cols-[minmax(0,380px)_minmax(0,1fr)] xl:gap-8">
          <SearchFilters
            categories={equipmentCategories}
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
          <div className="flex flex-col gap-6">
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
