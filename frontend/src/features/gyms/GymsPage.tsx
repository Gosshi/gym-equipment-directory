"use client";

import { useEffect, useRef } from "react";

import { SearchBar } from "@/components/gyms/SearchBar";
import { GymList } from "@/components/gyms/GymList";
import { useToast } from "@/components/ui/use-toast";
import { useGymSearch } from "@/hooks/useGymSearch";

export function GymsPage() {
  const {
    formState,
    updateKeyword,
    updatePrefecture,
    updateCategories,
    clearFilters,
    page,
    limit,
    setPage,
    setLimit,
    loadNextPage,
    items,
    meta,
    isLoading,
    isInitialLoading,
    error,
    retry,
    prefectures,
    equipmentCategories,
    isMetaLoading,
    metaError,
    reloadMeta,
  } = useGymSearch();

  const { toast } = useToast();
  const lastErrorKeyRef = useRef<string | null>(null);

  useEffect(() => {
    if (!error || error.type !== "server") {
      lastErrorKeyRef.current = null;
      return;
    }
    const key = `${error.type}-${error.status ?? ""}-${error.message}`;
    if (lastErrorKeyRef.current === key) {
      return;
    }
    lastErrorKeyRef.current = key;
    toast({
      variant: "destructive",
      title: "検索に失敗しました",
      description: error.message,
    });
  }, [error, toast]);

  return (
    <div className="flex min-h-screen w-full flex-col gap-10 px-4 py-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8">
        <header className="space-y-2">
          <p className="text-sm uppercase tracking-wide text-muted-foreground">Gym Directory</p>
          <h1 className="text-3xl font-bold sm:text-4xl">ジム一覧・検索</h1>
          <p className="text-sm text-muted-foreground">
            設備カテゴリやエリアで絞り込み、URL 共有で同じ検索条件を再現できます。
          </p>
        </header>

        <SearchBar
          categories={formState.categories}
          categoryOptions={equipmentCategories}
          isMetaLoading={isMetaLoading}
          keyword={formState.q}
          metaError={metaError}
          onCategoriesChange={updateCategories}
          onClear={clearFilters}
          onKeywordChange={updateKeyword}
          onPrefectureChange={updatePrefecture}
          onReloadMeta={reloadMeta}
          prefecture={formState.prefecture}
          prefectures={prefectures}
        />

        <GymList
          error={error}
          gyms={items}
          isInitialLoading={isInitialLoading}
          isLoading={isLoading}
          limit={limit}
          meta={meta}
          onLoadMore={loadNextPage}
          onLimitChange={setLimit}
          onPageChange={setPage}
          onRetry={retry}
          page={page}
        />
      </div>
    </div>
  );
}
