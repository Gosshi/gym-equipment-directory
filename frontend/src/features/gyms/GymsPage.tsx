"use client";

import dynamic from "next/dynamic";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { GymDetailPanel } from "@/components/gyms/GymDetailPanel";
import { GymList } from "@/components/gyms/GymList";
import { SearchFilters } from "@/components/gyms/SearchFilters";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useGymSearch } from "@/hooks/useGymSearch";
import {
  clearSelectedFromSearchParams,
  getSelectedFromSearchParams,
  setSelectedOnSearchParams,
} from "@/lib/urlState";
import { cn } from "@/lib/utils";

const SearchResultsMap = dynamic(() => import("@/components/map/Map").then(mod => mod.SearchResultsMap), {
  ssr: false,
  loading: () => <div className="h-[360px] w-full animate-pulse rounded-2xl bg-muted" />,
});

export function GymsPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const searchParamsSnapshot = searchParams.toString();
  const skipNextSearchSyncRef = useRef(false);

  const [selectedSlug, setSelectedSlug] = useState<string | null>(() =>
    getSelectedFromSearchParams(searchParamsSnapshot),
  );
  const [hoveredSlug, setHoveredSlug] = useState<string | null>(null);

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

  const handleHoverGym = useCallback((slug: string | null) => {
    setHoveredSlug(slug);
  }, []);

  const showDetailPanel = Boolean(selectedSlug);

  useEffect(() => {
    if (skipNextSearchSyncRef.current) {
      skipNextSearchSyncRef.current = false;
      return;
    }
    const value = getSelectedFromSearchParams(searchParamsSnapshot);
    setSelectedSlug(previous => (previous === value ? previous : value));
  }, [searchParamsSnapshot]);

  useEffect(() => {
    if (!pathname) {
      return;
    }
    const current = getSelectedFromSearchParams(searchParamsSnapshot);
    if (current === selectedSlug) {
      return;
    }
    const nextSearch = selectedSlug
      ? setSelectedOnSearchParams(searchParamsSnapshot, selectedSlug)
      : clearSelectedFromSearchParams(searchParamsSnapshot);
    skipNextSearchSyncRef.current = true;
    const nextUrl = nextSearch ? `${pathname}?${nextSearch}` : pathname;
    router.replace(nextUrl, { scroll: false });
  }, [pathname, router, searchParamsSnapshot, selectedSlug]);

  useEffect(() => {
    if (hoveredSlug && !items.some(gym => gym.slug === hoveredSlug)) {
      setHoveredSlug(null);
    }
  }, [hoveredSlug, items]);

  useEffect(() => {
    if (!selectedSlug) {
      return;
    }
    if (!items.some(gym => gym.slug === selectedSlug)) {
      setSelectedSlug(null);
    }
  }, [items, selectedSlug]);

  useEffect(() => {
    if (!isLoading && items.length === 0) {
      setSelectedSlug(null);
    }
  }, [isLoading, items.length]);

  const mapGyms = useMemo(() => items, [items]);

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
                ? "xl:grid xl:grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)] xl:items-start xl:gap-6"
                : undefined,
            )}
          >
            <div className="flex flex-col gap-6">
              <Card className="overflow-hidden">
                <CardHeader className="space-y-1">
                  <CardTitle className="text-lg font-semibold">地図</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    ピン・一覧・詳細パネルが同期します。操作した場所のジムに地図がフォーカスします。
                  </p>
                </CardHeader>
                <CardContent className="p-0">
                  <SearchResultsMap
                    className="h-[360px] w-full"
                    gyms={mapGyms}
                    hoveredGymId={hoveredSlug}
                    onHover={handleHoverGym}
                    onSelect={handleSelectGym}
                    selectedGymId={selectedSlug}
                  />
                </CardContent>
              </Card>
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
                onGymHover={handleHoverGym}
                selectedSlug={selectedSlug}
                hoveredSlug={hoveredSlug}
              />
            </div>
            {showDetailPanel ? (
              <GymDetailPanel className="xl:ml-2" onClose={handleClosePanel} slug={selectedSlug} />
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
