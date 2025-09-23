"use client";

import { SearchFilters } from "@/components/gyms/SearchFilters";
import { GymList } from "@/components/gyms/GymList";
import { useGymSearch } from "@/hooks/useGymSearch";

export function GymsPage() {
  const {
    formState,
    updateKeyword,
    updatePrefecture,
    updateCity,
    updateCategories,
    updateSort,
    updateDistance,
    clearFilters,
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

  return (
    <div className="flex min-h-screen w-full flex-col gap-10 px-4 py-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <header className="space-y-2">
          <p className="text-sm uppercase tracking-wide text-muted-foreground">Gym Directory</p>
          <h1 className="text-3xl font-bold sm:text-4xl">ジム一覧・検索</h1>
          <p className="text-sm text-muted-foreground">
            設備カテゴリやエリアで絞り込み、URL 共有で同じ検索条件を再現できます。
          </p>
        </header>
        <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
          <SearchFilters
            categories={equipmentCategories}
            cities={cities}
            cityError={cityError}
            isCityLoading={isCityLoading}
            isMetaLoading={isMetaLoading}
            metaError={metaError}
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
            location={location}
            prefectures={prefectures}
            state={formState}
          />
          <GymList
            error={error}
            gyms={items}
            isInitialLoading={isInitialLoading}
            isLoading={isLoading}
            limit={limit}
            meta={meta}
            onLimitChange={setLimit}
            onPageChange={setPage}
            onRetry={retry}
            page={page}
          />
        </div>
      </div>
    </div>
  );
}
