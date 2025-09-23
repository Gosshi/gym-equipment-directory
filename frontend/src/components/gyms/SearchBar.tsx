import { useMemo } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DISTANCE_STEP_KM,
  MAX_DISTANCE_KM,
  MIN_DISTANCE_KM,
} from "@/lib/searchParams";
import { cn } from "@/lib/utils";
import type {
  EquipmentCategoryOption,
  PrefectureOption,
} from "@/types/meta";

type SearchBarProps = {
  keyword: string;
  prefecture: string;
  categories: string[];
  distance: number;
  prefectures: PrefectureOption[];
  categoryOptions: EquipmentCategoryOption[];
  isMetaLoading: boolean;
  metaError: string | null;
  onKeywordChange: (value: string) => void;
  onPrefectureChange: (value: string) => void;
  onCategoriesChange: (values: string[]) => void;
  onDistanceChange: (value: number) => void;
  onReloadMeta: () => void;
  onClear: () => void;
};

export function SearchBar({
  keyword,
  prefecture,
  categories,
  distance,
  prefectures,
  categoryOptions,
  isMetaLoading,
  metaError,
  onKeywordChange,
  onPrefectureChange,
  onCategoriesChange,
  onDistanceChange,
  onReloadMeta,
  onClear,
}: SearchBarProps) {
  const sortedPrefectures = useMemo(
    () => [...prefectures].sort((a, b) => a.label.localeCompare(b.label, "ja")),
    [prefectures],
  );

  const sortedCategories = useMemo(
    () => [...categoryOptions].sort((a, b) => a.label.localeCompare(b.label, "ja")),
    [categoryOptions],
  );

  const handleCategoryToggle = (value: string) => {
    if (categories.includes(value)) {
      onCategoriesChange(categories.filter((item) => item !== value));
      return;
    }
    onCategoriesChange([...categories, value]);
  };

  return (
    <section aria-label="検索条件" className="space-y-4">
      <form
        className="space-y-6 rounded-lg border bg-card p-6 shadow-sm"
        onSubmit={(event) => event.preventDefault()}
      >
        <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_220px_auto] md:items-end">
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="gym-search-keyword">
              キーワード
            </label>
            <Input
              aria-label="検索キーワード"
              autoComplete="off"
              id="gym-search-keyword"
              placeholder="設備やジム名で検索"
              type="search"
              value={keyword}
              onChange={(event) => onKeywordChange(event.target.value)}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="gym-search-prefecture">
              都道府県
            </label>
            <select
              aria-label="都道府県を選択"
              className={cn(
                "h-10 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              )}
              disabled={isMetaLoading && sortedPrefectures.length === 0}
              id="gym-search-prefecture"
              value={prefecture}
              onChange={(event) => onPrefectureChange(event.target.value)}
            >
              <option value="">指定しない</option>
              {sortedPrefectures.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex justify-end">
            <Button onClick={onClear} type="button" variant="outline">
              条件をクリア
            </Button>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm font-medium" id="gym-search-categories-label">
              設備カテゴリ
            </span>
            {isMetaLoading ? (
              <span className="text-xs text-muted-foreground">読み込み中...</span>
            ) : null}
          </div>
          <div
            aria-label="設備カテゴリを選択"
            aria-labelledby="gym-search-categories-label"
            className="flex flex-wrap gap-2"
            role="group"
          >
            {sortedCategories.map((category) => {
              const selected = categories.includes(category.value);
              return (
                <button
                  key={category.value}
                  aria-label={`${category.label}カテゴリを${selected ? "解除" : "選択"}`}
                  aria-pressed={selected}
                  className={cn(
                    "rounded-full border px-3 py-1 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    selected
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-input bg-background hover:bg-accent hover:text-accent-foreground",
                  )}
                  onClick={() => handleCategoryToggle(category.value)}
                  type="button"
                >
                  {category.label}
                </button>
              );
            })}
            {sortedCategories.length === 0 && !isMetaLoading ? (
              <span className="text-xs text-muted-foreground">カテゴリが見つかりません。</span>
            ) : null}
          </div>
        </div>

        <div className="space-y-3">
          <label className="text-sm font-medium" htmlFor="gym-search-distance">
            距離（km）
          </label>
          <input
            aria-label="現在地からの検索距離"
            aria-valuemax={MAX_DISTANCE_KM}
            aria-valuemin={MIN_DISTANCE_KM}
            aria-valuenow={distance}
            className="w-full"
            id="gym-search-distance"
            max={MAX_DISTANCE_KM}
            min={MIN_DISTANCE_KM}
            onChange={(event) =>
              onDistanceChange(Number.parseInt(event.target.value, 10))
            }
            step={DISTANCE_STEP_KM}
            type="range"
            value={distance}
          />
          <p className="text-xs text-muted-foreground">
            現在地から約 {distance}km 圏内のジムを検索します。
          </p>
        </div>
      </form>

      {metaError ? (
        <div
          className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive"
          role="alert"
        >
          <span>{metaError}</span>
          <Button onClick={onReloadMeta} size="sm" type="button" variant="outline">
            再読み込み
          </Button>
        </div>
      ) : null}
    </section>
  );
}
