"use client";

import { ChangeEvent, useMemo } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useGymSearch } from "@/hooks/useGymSearch";
import { cn } from "@/lib/utils";
import type { GymSummary } from "@/types/gym";
import type { EquipmentCategoryOption, PrefectureOption } from "@/types/meta";

const PER_PAGE_OPTIONS = [12, 24, 36];

const formatSlug = (value: string) =>
  value
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");

const formatDate = (value: string | null | undefined) => {
  if (!value) {
    return undefined;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleDateString();
};

const GymsSkeleton = () => (
  <div aria-hidden className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" role="presentation">
    {Array.from({ length: 6 }).map((_, index) => (
      <Card key={index} className="overflow-hidden">
        <Skeleton className="h-40 w-full" />
        <CardContent className="space-y-3">
          <Skeleton className="h-6 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <div className="flex gap-2">
            <Skeleton className="h-6 w-16 rounded-full" />
            <Skeleton className="h-6 w-16 rounded-full" />
            <Skeleton className="h-6 w-16 rounded-full" />
          </div>
        </CardContent>
      </Card>
    ))}
  </div>
);

const GymCard = ({ gym }: { gym: GymSummary }) => (
  <Link
    className="group block focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    href={`/gyms/${gym.slug}`}
  >
    <Card className="flex h-full flex-col overflow-hidden transition group-hover:border-primary">
      <div className="flex h-40 items-center justify-center bg-muted text-sm text-muted-foreground">
        {gym.thumbnailUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            alt={gym.name}
            className="h-full w-full object-cover transition group-hover:scale-[1.02]"
            src={gym.thumbnailUrl}
          />
        ) : (
          <span>画像なし</span>
        )}
      </div>
      <CardHeader className="space-y-2">
        <CardTitle className="text-xl group-hover:text-primary">{gym.name}</CardTitle>
        <CardDescription className="text-sm text-muted-foreground">
          {gym.prefecture ? formatSlug(gym.prefecture) : "エリア未設定"}
          {gym.city ? ` / ${formatSlug(gym.city)}` : null}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-4">
        {gym.equipments && gym.equipments.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {gym.equipments.slice(0, 6).map((equipment) => (
              <span
                key={equipment}
                className="rounded-full bg-secondary px-2 py-1 text-xs text-secondary-foreground"
              >
                {equipment}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            設備情報はまだ登録されていません。
          </p>
        )}
        {formatDate(gym.lastVerifiedAt) ? (
          <p className="mt-auto text-xs text-muted-foreground">
            最終更新: {formatDate(gym.lastVerifiedAt)}
          </p>
        ) : null}
      </CardContent>
    </Card>
  </Link>
);

type PaginationControlsProps = {
  page: number;
  hasNext: boolean;
  isLoading: boolean;
  onChange: (nextPage: number) => void;
};

const PaginationControls = ({
  page,
  hasNext,
  isLoading,
  onChange,
}: PaginationControlsProps) => (
  <nav aria-label="ページネーション" className="mt-8 flex justify-center">
    <div className="flex items-center gap-3">
      <Button
        aria-label="前のページ"
        disabled={isLoading || page <= 1}
        onClick={() => onChange(page - 1)}
        type="button"
        variant="outline"
      >
        前へ
      </Button>
      <span className="text-sm text-muted-foreground">ページ {page}</span>
      <Button
        aria-label="次のページ"
        disabled={isLoading || !hasNext}
        onClick={() => onChange(page + 1)}
        type="button"
      >
        次へ
      </Button>
    </div>
  </nav>
);

type SearchPanelProps = {
  formState: {
    q: string;
    prefecture: string;
    city: string;
    equipments: string[];
    sort: string;
  };
  prefectures: PrefectureOption[];
  equipmentCategories: EquipmentCategoryOption[];
  isMetaLoading: boolean;
  metaError: string | null;
  onKeywordChange: (value: string) => void;
  onPrefectureChange: (value: string) => void;
  onCityChange: (value: string) => void;
  onEquipmentsChange: (values: string[]) => void;
  onSortChange: (value: string) => void;
  onClear: () => void;
  onReloadMeta: () => void;
};

const SORT_OPTIONS: { value: string; label: string }[] = [
  { value: "score", label: "総合スコア" },
  { value: "freshness", label: "最新順" },
  { value: "richness", label: "充実度" },
  { value: "gym_name", label: "名称昇順" },
  { value: "created_at", label: "作成日時" },
];

const SearchPanel = ({
  formState,
  prefectures,
  equipmentCategories,
  isMetaLoading,
  metaError,
  onKeywordChange,
  onPrefectureChange,
  onCityChange,
  onEquipmentsChange,
  onSortChange,
  onClear,
  onReloadMeta,
}: SearchPanelProps) => {
  const sortedPrefectures = useMemo(
    () => [...prefectures].sort((a, b) => a.label.localeCompare(b.label, "ja")),
    [prefectures],
  );
  const sortedEquipmentCategories = useMemo(
    () => [...equipmentCategories].sort((a, b) => a.label.localeCompare(b.label, "ja")),
    [equipmentCategories],
  );

  const handleKeywordChange = (event: ChangeEvent<HTMLInputElement>) => {
    onKeywordChange(event.target.value);
  };

  const handlePrefectureChange = (event: ChangeEvent<HTMLSelectElement>) => {
    onPrefectureChange(event.target.value);
  };

  const handleEquipmentsChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const values = Array.from(event.target.selectedOptions).map((option) => option.value);
    onEquipmentsChange(values);
  };

  return (
    <aside className="space-y-4">
      <form
        className="space-y-5 rounded-lg border bg-card p-6 shadow-sm"
        onSubmit={(event) => event.preventDefault()}
      >
        <div className="grid gap-2">
          <label className="text-sm font-medium" htmlFor="gym-search-keyword">
            検索キーワード
          </label>
          <input
            autoComplete="off"
            className={cn(
              "h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            )}
            id="gym-search-keyword"
            name="keyword"
            onChange={handleKeywordChange}
            placeholder="設備やジム名で検索"
            type="search"
            value={formState.q}
          />
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-medium" htmlFor="gym-search-prefecture">
            都道府県
          </label>
          <select
            className={cn(
              "h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            )}
            disabled={isMetaLoading && sortedPrefectures.length === 0}
            id="gym-search-prefecture"
            name="prefecture"
            onChange={handlePrefectureChange}
            value={formState.prefecture}
          >
            <option value="">指定しない</option>
            {sortedPrefectures.map((prefecture) => (
              <option key={prefecture.value} value={prefecture.value}>
                {prefecture.label}
              </option>
            ))}
          </select>
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-medium" htmlFor="gym-search-city">
            市区町村
          </label>
            <input
              autoComplete="off"
              className={cn(
                "h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              )}
              disabled={!formState.prefecture}
              id="gym-search-city"
              name="city"
              onChange={(e) => onCityChange(e.target.value)}
              placeholder="例: funabashi"
              type="text"
              value={formState.city}
            />
          <p className="text-xs text-muted-foreground">
            都道府県選択後にスラッグ形式で入力（将来サジェスト予定）
          </p>
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-medium" htmlFor="gym-search-equipments">
            設備カテゴリ
          </label>
          <select
            aria-describedby="gym-search-equipments-help"
            className={cn(
              "min-h-[120px] rounded-md border border-input bg-background",
              "px-3 py-2 text-sm shadow-sm",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            )}
            disabled={isMetaLoading && sortedEquipmentCategories.length === 0}
            id="gym-search-equipments"
            multiple
            name="equipments"
            onChange={handleEquipmentsChange}
            size={Math.min(6, Math.max(4, sortedEquipmentCategories.length))}
            value={formState.equipments}
          >
            {sortedEquipmentCategories.map((category) => (
              <option key={category.value} value={category.value}>
                {category.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-muted-foreground" id="gym-search-equipments-help">
            ⌘/Ctrl キーを押しながら複数選択できます。
          </p>
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-medium" htmlFor="gym-search-sort">
            並び順
          </label>
          <select
            className={cn(
              "h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            )}
            id="gym-search-sort"
            name="sort"
            onChange={(e) => onSortChange(e.target.value)}
            value={formState.sort}
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-medium" htmlFor="gym-search-distance">
            距離 (プレースホルダ)
          </label>
          <input
            aria-describedby="gym-search-distance-help"
            className="w-full"
            defaultValue={5}
            id="gym-search-distance"
            max={30}
            min={1}
            step={1}
            type="range"
          />
          <p className="text-xs text-muted-foreground" id="gym-search-distance-help">
            現在 API 未連携
          </p>
        </div>
        <div className="flex flex-wrap justify-end gap-3">
          <Button onClick={onClear} type="button" variant="outline">
            条件をリセット
          </Button>
        </div>
      </form>
      {metaError ? (
        <div
          className={cn(
            "rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm",
            "text-destructive",
          )}
        >
          <div className="flex items-start justify-between gap-3">
            <span>{metaError}</span>
            <Button onClick={onReloadMeta} size="sm" type="button" variant="outline">
              再読み込み
            </Button>
          </div>
        </div>
      ) : null}
    </aside>
  );
};

export function GymsPage() {
  const {
    formState,
    appliedFilters,
    updateKeyword,
    updatePrefecture,
    updateCity,
    updateEquipments,
    updateSort,
    clearFilters,
    page,
    perPage,
    setPage,
    setPerPage,
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

  const showSkeleton = isInitialLoading;
  const showEmpty = !error && !showSkeleton && items.length === 0;
  const totalPages = Math.max(1, Math.ceil((meta.total || 0) / Math.max(perPage, 1)));

  return (
    <div className="flex min-h-screen w-full flex-col gap-10 px-4 py-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <header className="space-y-2">
          <p className="text-sm uppercase tracking-wide text-muted-foreground">Gym Directory</p>
          <h1 className="text-3xl font-bold sm:text-4xl">ジム一覧</h1>
          <p className="text-sm text-muted-foreground">
            キーワード・都道府県・設備カテゴリで絞り込み、URL の共有で同じ検索条件を再現できます。
          </p>
        </header>
        <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
          <SearchPanel
            equipmentCategories={equipmentCategories}
            formState={formState}
            isMetaLoading={isMetaLoading}
            metaError={metaError}
            onClear={clearFilters}
            onEquipmentsChange={updateEquipments}
            onKeywordChange={updateKeyword}
            onPrefectureChange={updatePrefecture}
            onCityChange={updateCity}
            onSortChange={updateSort}
            onReloadMeta={reloadMeta}
            prefectures={prefectures}
          />
          <section
            aria-busy={isLoading}
            aria-live="polite"
            className="rounded-lg border bg-background p-6 shadow-sm"
          >
            <div className="flex flex-wrap items-center justify-between gap-4 pb-4">
              <div>
                <h2 className="text-xl font-semibold">検索結果</h2>
                <p className="text-sm text-muted-foreground">
                  {meta.total} 件のジムが見つかりました。
                  {totalPages > 1 ? `（全 ${totalPages} ページ）` : ""}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm text-muted-foreground" htmlFor="gym-search-per-page">
                  表示件数
                </label>
                <select
                  className={cn(
                    "h-9 rounded-md border border-input bg-background px-2 text-sm shadow-sm",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  )}
                  id="gym-search-per-page"
                  onChange={(event) => setPerPage(Number.parseInt(event.target.value, 10))}
                  value={perPage}
                >
                  {PER_PAGE_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option} 件
                    </option>
                  ))}
                </select>
              </div>
            </div>
            {error ? (
              <div
                className={cn(
                  "flex flex-col items-center gap-4 rounded-md",
                  "border border-destructive/40 bg-destructive/10 p-6 text-center",
                )}
              >
                <p className="text-sm text-destructive">{error}</p>
                <Button onClick={retry} type="button" variant="outline">
                  もう一度試す
                </Button>
              </div>
            ) : showSkeleton ? (
              <GymsSkeleton />
            ) : showEmpty ? (
              <p className="rounded-md bg-muted/40 p-4 text-center text-sm text-muted-foreground">
                条件に一致するジムが見つかりませんでした。
              </p>
            ) : (
              <div className={cn("grid gap-4", "sm:grid-cols-2", "xl:grid-cols-3")}>
                {items.map((gym) => (
                  <GymCard key={gym.id} gym={gym} />
                ))}
              </div>
            )}
            {!error && !showEmpty ? (
              <div className="mt-4 flex flex-col gap-3 text-sm text-muted-foreground">
                <span>
                  {meta.total} 件中 {(page - 1) * perPage + 1} -
                  {Math.min(page * perPage, meta.total)} 件を表示
                </span>
              </div>
            ) : null}
            {!error && (items.length > 0 || appliedFilters.page > 1 || meta.hasNext) ? (
              <PaginationControls
                hasNext={meta.hasNext}
                isLoading={isLoading}
                onChange={setPage}
                page={page}
              />
            ) : null}
          </section>
        </div>
      </div>
    </div>
  );
}
