"use client";

import { useCallback, useEffect, useState } from "react";

import { SearchFilters } from "@/components/gyms/SearchFilters";
import { GymList } from "@/components/gyms/GymList";
import { GymDetailPanel } from "@/components/gyms/GymDetailPanel";
import { useGymSearch } from "@/hooks/useGymSearch";
import { cn } from "@/lib/utils";

export function GymsPage() {
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
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
    setSelectedSlug(previous => (previous === slug ? previous : slug));
  }, []);

  const handleClosePanel = useCallback(() => {
    setSelectedSlug(null);
  }, []);

  const showDetailPanel = Boolean(selectedSlug);

  useEffect(() => {
    if (!isLoading && items.length === 0) {
      setSelectedSlug(null);
    }
  }, [isLoading, items.length]);

  return (
    <div className="flex min-h-screen w-full flex-col bg-muted/10">
      <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 px-4 pb-16 pt-8 sm:gap-10 sm:pt-12 lg:px-6 xl:px-0">
        <header className="space-y-3 sm:space-y-4">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground sm:text-sm">
            Gym Directory
          </p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">ジム一覧・検索</h1>
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
          <div
            className={cn(
              "flex flex-col gap-6",
              showDetailPanel
                ? "xl:grid xl:grid-cols-[minmax(0,1fr)_minmax(0,360px)] xl:items-start"
                : undefined,
            )}
          >
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
            {showDetailPanel ? (
              <GymDetailPanel className="xl:ml-2" onClose={handleClosePanel} slug={selectedSlug} />
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
