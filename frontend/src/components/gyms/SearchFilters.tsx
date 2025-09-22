import { useMemo } from "react";

import { Button } from "@/components/ui/button";
import {
  DISTANCE_STEP_KM,
  MAX_DISTANCE_KM,
  MIN_DISTANCE_KM,
  SORT_OPTIONS,
  type SortOption,
} from "@/lib/searchParams";
import { cn } from "@/lib/utils";
import type {
  CityOption,
  EquipmentCategoryOption,
  PrefectureOption,
} from "@/types/meta";

const SORT_LABELS: Record<SortOption, string> = {
  distance: "距離が近い順",
  popular: "人気順",
  fresh: "更新が新しい順",
  newest: "新着順",
};

type SearchFiltersProps = {
  state: {
    q: string;
    prefecture: string;
    city: string;
    categories: string[];
    sort: SortOption;
    distance: number;
  };
  prefectures: PrefectureOption[];
  cities: CityOption[];
  categories: EquipmentCategoryOption[];
  isMetaLoading: boolean;
  isCityLoading: boolean;
  metaError: string | null;
  cityError: string | null;
  onKeywordChange: (value: string) => void;
  onPrefectureChange: (value: string) => void;
  onCityChange: (value: string) => void;
  onCategoriesChange: (values: string[]) => void;
  onSortChange: (value: SortOption) => void;
  onDistanceChange: (value: number) => void;
  onClear: () => void;
  onReloadMeta: () => void;
  onReloadCities: () => void;
};

export function SearchFilters({
  state,
  prefectures,
  cities,
  categories,
  isMetaLoading,
  isCityLoading,
  metaError,
  cityError,
  onKeywordChange,
  onPrefectureChange,
  onCityChange,
  onCategoriesChange,
  onSortChange,
  onDistanceChange,
  onClear,
  onReloadMeta,
  onReloadCities,
}: SearchFiltersProps) {
  const sortedPrefectures = useMemo(
    () => [...prefectures].sort((a, b) => a.label.localeCompare(b.label, "ja")),
    [prefectures],
  );
  const sortedCategories = useMemo(
    () => [...categories].sort((a, b) => a.label.localeCompare(b.label, "ja")),
    [categories],
  );
  const sortedCities = useMemo(
    () => [...cities].sort((a, b) => a.label.localeCompare(b.label, "ja")),
    [cities],
  );

  const handleCategoryToggle = (value: string) => {
    const isSelected = state.categories.includes(value);
    if (isSelected) {
      onCategoriesChange(state.categories.filter((item) => item !== value));
    } else {
      onCategoriesChange([...state.categories, value]);
    }
  };

  return (
    <aside className="space-y-4">
      <form
        className="space-y-6 rounded-lg border bg-card p-6 shadow-sm"
        onSubmit={(event) => event.preventDefault()}
      >
        <div className="grid gap-2">
          <label className="text-sm font-medium" htmlFor="gym-search-keyword">
            キーワード
          </label>
          <input
            autoComplete="off"
            className={cn(
              "h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            )}
            id="gym-search-keyword"
            name="keyword"
            onChange={(event) => onKeywordChange(event.target.value)}
            placeholder="設備やジム名で検索"
            type="search"
            value={state.q}
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
            onChange={(event) => onPrefectureChange(event.target.value)}
            value={state.prefecture}
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
          <select
            className={cn(
              "h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            )}
            disabled={!state.prefecture || (isCityLoading && sortedCities.length === 0)}
            id="gym-search-city"
            name="city"
            onChange={(event) => onCityChange(event.target.value)}
            value={state.city}
          >
            <option value="">指定しない</option>
            {sortedCities.map((city) => (
              <option key={city.value} value={city.value}>
                {city.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-muted-foreground">
            都道府県を選択すると市区町村を絞り込めます。
          </p>
        </div>

        <fieldset className="space-y-3">
          <legend className="text-sm font-medium">設備カテゴリ</legend>
          <div className="flex flex-wrap gap-2">
            {sortedCategories.map((category) => {
              const checked = state.categories.includes(category.value);
              return (
                <label
                  key={category.value}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm",
                    checked
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-input bg-background",
                  )}
                >
                  <input
                    checked={checked}
                    className="sr-only"
                    onChange={() => handleCategoryToggle(category.value)}
                    type="checkbox"
                    value={category.value}
                  />
                  <span>{category.label}</span>
                </label>
              );
            })}
            {sortedCategories.length === 0 ? (
              <span className="text-xs text-muted-foreground">
                設備カテゴリが読み込み中です…
              </span>
            ) : null}
          </div>
        </fieldset>

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
            onChange={(event) => onSortChange(event.target.value as SortOption)}
            value={state.sort}
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {SORT_LABELS[option]}
              </option>
            ))}
          </select>
        </div>

        <div className="grid gap-2">
          <label className="text-sm font-medium" htmlFor="gym-search-distance">
            距離（km）
          </label>
          <input
            aria-valuemin={MIN_DISTANCE_KM}
            aria-valuemax={MAX_DISTANCE_KM}
            aria-valuenow={state.distance}
            className="w-full"
            id="gym-search-distance"
            max={MAX_DISTANCE_KM}
            min={MIN_DISTANCE_KM}
            onChange={(event) =>
              onDistanceChange(Number.parseInt(event.target.value, 10))
            }
            step={DISTANCE_STEP_KM}
            type="range"
            value={state.distance}
          />
          <span className="text-xs text-muted-foreground">
            現在の距離: 約 {state.distance}km（将来的に近隣検索と連携予定）
          </span>
        </div>

        <div className="flex flex-wrap justify-end gap-3">
          <Button onClick={onClear} type="button" variant="outline">
            条件をクリア
          </Button>
        </div>
      </form>

      {metaError ? (
        <div
          aria-live="polite"
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

      {cityError ? (
        <div
          aria-live="polite"
          className={cn(
            "rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm",
            "text-destructive",
          )}
        >
          <div className="flex items-start justify-between gap-3">
            <span>{cityError}</span>
            <Button onClick={onReloadCities} size="sm" type="button" variant="outline">
              再読み込み
            </Button>
          </div>
        </div>
      ) : null}
    </aside>
  );
}
