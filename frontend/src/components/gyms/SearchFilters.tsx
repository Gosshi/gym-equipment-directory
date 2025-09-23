import { useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  DISTANCE_STEP_KM,
  MAX_DISTANCE_KM,
  MIN_DISTANCE_KM,
  MAX_LATITUDE,
  MAX_LONGITUDE,
  MIN_LATITUDE,
  MIN_LONGITUDE,
  SORT_OPTIONS,
  type SortOption,
} from "@/lib/searchParams";
import { cn } from "@/lib/utils";
import { ApiError } from "@/lib/apiClient";
import type { LocationState } from "@/hooks/useGymSearch";
import { suggestGyms, type GymSuggestItem } from "@/services/suggest";
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
  location: LocationState;
  onKeywordChange: (value: string) => void;
  onPrefectureChange: (value: string) => void;
  onCityChange: (value: string) => void;
  onCategoriesChange: (values: string[]) => void;
  onSortChange: (value: SortOption) => void;
  onDistanceChange: (value: number) => void;
  onClear: () => void;
  onRequestLocation: () => void;
  onClearLocation: () => void;
  onManualLocationChange: (lat: number | null, lng: number | null) => void;
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
  location,
  onKeywordChange,
  onPrefectureChange,
  onCityChange,
  onCategoriesChange,
  onSortChange,
  onDistanceChange,
  onClear,
  onRequestLocation,
  onClearLocation,
  onManualLocationChange,
  onReloadMeta,
  onReloadCities,
}: SearchFiltersProps) {
  const [suggestions, setSuggestions] = useState<GymSuggestItem[]>([]);
  const [isSuggestLoading, setIsSuggestLoading] = useState(false);
  const [suggestError, setSuggestError] = useState<string | null>(null);
  const suggestAbortRef = useRef<AbortController | null>(null);
  const suggestTimerRef = useRef<NodeJS.Timeout | null>(null);

  const [latInput, setLatInput] = useState<string>("");
  const [lngInput, setLngInput] = useState<string>("");
  const [manualError, setManualError] = useState<string | null>(null);

  useEffect(() => {
    if (location.lat != null) {
      setLatInput(location.lat.toFixed(5));
    } else {
      setLatInput("");
    }
    if (location.lng != null) {
      setLngInput(location.lng.toFixed(5));
    } else {
      setLngInput("");
    }
    setManualError(null);
  }, [location.lat, location.lng]);

  useEffect(() => {
    return () => {
      if (suggestTimerRef.current) {
        clearTimeout(suggestTimerRef.current);
        suggestTimerRef.current = null;
      }
      if (suggestAbortRef.current) {
        suggestAbortRef.current.abort();
        suggestAbortRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    const keyword = state.q.trim();
    if (suggestTimerRef.current) {
      clearTimeout(suggestTimerRef.current);
      suggestTimerRef.current = null;
    }
    if (keyword.length < 2) {
      if (suggestAbortRef.current) {
        suggestAbortRef.current.abort();
        suggestAbortRef.current = null;
      }
      setIsSuggestLoading(false);
      setSuggestError(null);
      setSuggestions([]);
      return;
    }
    suggestTimerRef.current = setTimeout(() => {
      suggestTimerRef.current = null;
      if (suggestAbortRef.current) {
        suggestAbortRef.current.abort();
      }
      const controller = new AbortController();
      suggestAbortRef.current = controller;
      setIsSuggestLoading(true);
      setSuggestError(null);
      suggestGyms(keyword, {
        pref: state.prefecture || undefined,
        signal: controller.signal,
      })
        .then((items) => {
          setSuggestions(items);
        })
        .catch((error) => {
          if (controller.signal.aborted) {
            return;
          }
          const message =
            error instanceof ApiError
              ? error.message || "候補の取得に失敗しました"
              : error instanceof Error
              ? error.message
              : "候補の取得に失敗しました";
          setSuggestError(message);
          setSuggestions([]);
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setIsSuggestLoading(false);
          }
        });
    }, 350);

    return () => {
      if (suggestTimerRef.current) {
        clearTimeout(suggestTimerRef.current);
        suggestTimerRef.current = null;
      }
    };
  }, [state.q, state.prefecture]);

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

  const hasLocation = location.lat != null && location.lng != null;
  const isLocating = location.status === "loading";
  const canApplyManual = latInput.trim().length > 0 && lngInput.trim().length > 0;
  const coordinateLabel = hasLocation
    ? `${location.lat!.toFixed(4)}, ${location.lng!.toFixed(4)}`
    : "";
  const locationSummary = hasLocation
    ? `${location.mode === "auto" ? "現在地を使用中" : "手入力した地点を使用中"}（${coordinateLabel}）`
    : location.isSupported
    ? "現在地を取得すると距離フィルタが有効になります。"
    : "この環境では位置情報を取得できません。緯度・経度を手入力してください。";

  const handleCategoryToggle = (value: string) => {
    const isSelected = state.categories.includes(value);
    if (isSelected) {
      onCategoriesChange(state.categories.filter((item) => item !== value));
    } else {
      onCategoriesChange([...state.categories, value]);
    }
  };

  const handleSuggestionSelect = (item: GymSuggestItem) => {
    onKeywordChange(item.name);
    setSuggestions([]);
    setSuggestError(null);
  };

  const handleManualLocationApply = () => {
    if (!canApplyManual) {
      setManualError("緯度と経度を入力してください。");
      return;
    }
    const latValue = Number.parseFloat(latInput);
    const lngValue = Number.parseFloat(lngInput);
    if (!Number.isFinite(latValue) || latValue < MIN_LATITUDE || latValue > MAX_LATITUDE) {
      setManualError(`緯度は ${MIN_LATITUDE} 〜 ${MAX_LATITUDE} の範囲で入力してください。`);
      return;
    }
    if (!Number.isFinite(lngValue) || lngValue < MIN_LONGITUDE || lngValue > MAX_LONGITUDE) {
      setManualError(`経度は ${MIN_LONGITUDE} 〜 ${MAX_LONGITUDE} の範囲で入力してください。`);
      return;
    }
    setManualError(null);
    onManualLocationChange(latValue, lngValue);
  };

  const handleClearLocation = () => {
    setLatInput("");
    setLngInput("");
    setManualError(null);
    onClearLocation();
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
          <div className="space-y-2">
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
            {state.q.trim().length >= 2 ? (
              <div className="space-y-1">
                {isSuggestLoading ? (
                  <p className="text-xs text-muted-foreground">候補を検索中です…</p>
                ) : null}
                {suggestError ? (
                  <p className="text-xs text-destructive">{suggestError}</p>
                ) : null}
                {suggestions.length > 0 ? (
                  <ul className="divide-y overflow-hidden rounded-md border bg-background text-sm">
                    {suggestions.map((item) => (
                      <li key={item.slug}>
                        <button
                          className={cn(
                            "flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left",
                            "transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                          )}
                          onClick={() => handleSuggestionSelect(item)}
                          type="button"
                        >
                          <span className="font-medium">{item.name}</span>
                          <span className="text-xs text-muted-foreground">
                            {[item.pref, item.city].filter(Boolean).join(" / ") || "地域情報なし"}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : null}
          </div>
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

        <div className="space-y-3 rounded-lg border border-dashed p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <p className="text-sm font-medium">現在地と距離</p>
              <p className="text-xs text-muted-foreground">{locationSummary}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button onClick={onRequestLocation} size="sm" type="button" disabled={isLocating}>
                {isLocating ? "取得中..." : "現在地を取得"}
              </Button>
              <Button
                onClick={handleClearLocation}
                size="sm"
                type="button"
                variant="outline"
                disabled={!hasLocation && latInput.trim() === "" && lngInput.trim() === ""}
              >
                現在地を解除
              </Button>
            </div>
          </div>
          {location.status === "error" && location.error ? (
            <p className="text-xs text-destructive">{location.error}</p>
          ) : null}
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="grid gap-1">
              <label className="text-xs font-medium text-muted-foreground" htmlFor="manual-lat">
                緯度（-90〜90）
              </label>
              <input
                autoComplete="off"
                className={cn(
                  "h-9 rounded-md border border-input bg-background px-3 text-sm shadow-sm",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                )}
                id="manual-lat"
                inputMode="decimal"
                onChange={(event) => {
                  setLatInput(event.target.value);
                  setManualError(null);
                }}
                placeholder="35.6895"
                value={latInput}
              />
            </div>
            <div className="grid gap-1">
              <label className="text-xs font-medium text-muted-foreground" htmlFor="manual-lng">
                経度（-180〜180）
              </label>
              <input
                autoComplete="off"
                className={cn(
                  "h-9 rounded-md border border-input bg-background px-3 text-sm shadow-sm",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                )}
                id="manual-lng"
                inputMode="decimal"
                onChange={(event) => {
                  setLngInput(event.target.value);
                  setManualError(null);
                }}
                placeholder="139.6917"
                value={lngInput}
              />
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              disabled={!canApplyManual}
              onClick={handleManualLocationApply}
              size="sm"
              type="button"
            >
              この座標で検索
            </Button>
            {hasLocation ? (
              <span className="text-xs text-muted-foreground">適用中: {coordinateLabel}</span>
            ) : null}
          </div>
          {manualError ? <p className="text-xs text-destructive">{manualError}</p> : null}
        </div>

        <div className="grid gap-2">
          <label className="text-sm font-medium" htmlFor="gym-search-distance">
            距離（km）
          </label>
          <input
            aria-valuemin={MIN_DISTANCE_KM}
            aria-valuemax={MAX_DISTANCE_KM}
            aria-valuenow={state.distance}
            className={cn("w-full", !hasLocation && "opacity-50")}
            id="gym-search-distance"
            max={MAX_DISTANCE_KM}
            min={MIN_DISTANCE_KM}
            onChange={(event) =>
              onDistanceChange(Number.parseInt(event.target.value, 10))
            }
            step={DISTANCE_STEP_KM}
            type="range"
            value={state.distance}
            disabled={!hasLocation}
          />
          <span className="text-xs text-muted-foreground">
            {hasLocation
              ? `現在の距離: 約 ${state.distance}km`
              : "現在地を設定すると距離フィルタを利用できます。"}
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
