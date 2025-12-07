import { useEffect, useId, useMemo, useRef, useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";

import { SearchBar } from "@/components/common/SearchBar";
import { SearchDistanceBadge } from "@/components/search/SearchDistanceBadge";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import {
  DISTANCE_STEP_KM,
  MAX_DISTANCE_KM,
  MIN_DISTANCE_KM,
  MAX_LATITUDE,
  MAX_LONGITUDE,
  MIN_LATITUDE,
  MIN_LONGITUDE,
  type SortOption,
  type SortOrder,
  CONDITION_OPTIONS,
} from "@/lib/searchParams";
import { cn } from "@/lib/utils";
import { ApiError } from "@/lib/apiClient";
import { FALLBACK_LOCATION, type LocationState } from "@/hooks/useGymSearch";
import { suggestGyms, type GymSuggestItem } from "@/services/suggest";
import type { CityOption, EquipmentOption, PrefectureOption } from "@/types/meta";

const SORT_SELECT_OPTIONS: Array<{
  value: string;
  sort: SortOption;
  order: SortOrder;
  label: string;
  requiresLocation?: boolean;
}> = [
  {
    value: "distance:asc",
    sort: "distance",
    order: "asc",
    label: "距離（近い順）",
    requiresLocation: true,
  },
  { value: "name:asc", sort: "name", order: "asc", label: "名前（A→Z）" },
  { value: "rating:desc", sort: "rating", order: "desc", label: "評価（高い順）" },
  { value: "reviews:desc", sort: "reviews", order: "desc", label: "口コミ数（多い順）" },
];

const DISTANCE_PRESET_OPTIONS = [1, 3, 5, 10, 15, 20, 25, 30];

type SearchFiltersProps = {
  state: {
    q: string;
    prefecture: string;
    city: string;
    categories: string[];
    conditions: string[];
    sort: SortOption;
    order: SortOrder;
    distance: number;
  };
  prefectures: PrefectureOption[];
  cities: CityOption[];
  categories: EquipmentOption[];
  isMetaLoading: boolean;
  isCityLoading: boolean;
  metaError: string | null;
  cityError: string | null;
  location: LocationState;
  isSearchLoading: boolean;
  onKeywordChange: (value: string) => void;
  onPrefectureChange: (value: string) => void;
  onCityChange: (value: string) => void;
  onCategoriesChange: (values: string[]) => void;
  onConditionsChange: (values: string[]) => void;
  onSortChange: (sort: SortOption, order: SortOrder) => void;
  onDistanceChange: (value: number) => void;
  onClear: () => void;
  onRequestLocation: () => void;
  onUseFallbackLocation: () => void;
  onClearLocation: () => void;
  onManualLocationChange: (lat: number | null, lng: number | null) => void;
  onReloadMeta: () => void;
  onReloadCities: () => void;
  onSubmitSearch: () => void;
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
  isSearchLoading,
  onKeywordChange,
  onPrefectureChange,
  onCityChange,
  onCategoriesChange,
  onConditionsChange,
  onSortChange,
  onDistanceChange,
  onClear,
  onRequestLocation,
  onUseFallbackLocation,
  onClearLocation,
  onManualLocationChange,
  onReloadMeta,
  onReloadCities,
  onSubmitSearch,
}: SearchFiltersProps) {
  const [suggestions, setSuggestions] = useState<GymSuggestItem[]>([]);
  const [isSuggestLoading, setIsSuggestLoading] = useState(false);
  const [suggestError, setSuggestError] = useState<string | null>(null);
  const suggestAbortRef = useRef<AbortController | null>(null);
  const suggestTimerRef = useRef<NodeJS.Timeout | null>(null);
  // SSR -> CSR の hydration で geolocation サポート可否が
  // サーバとクライアントで異なり得るため、初回マウント前は常に
  // "現在地は利用不可" 側のラベルで固定し mismatch を回避する。
  const [mounted, setMounted] = useState(false);

  const [latInput, setLatInput] = useState<string>("");
  const [lngInput, setLngInput] = useState<string>("");
  const [manualError, setManualError] = useState<string | null>(null);
  const { toast } = useToast();
  const keywordInputRef = useRef<HTMLInputElement | null>(null);
  const lastLocationToastRef = useRef<string | null>(null);
  const locationSummaryId = useId();
  const manualLocationHintId = useId();
  const manualLocationErrorId = useId();
  const distanceHelpTextId = useId();
  const prefectureHelpTextId = useId();
  const cityHelpTextId = useId();
  const keywordHelpTextId = useId();

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
    const message = location.error;
    if (!message || location.status !== "error") {
      if (!message) {
        lastLocationToastRef.current = null;
      }
      return;
    }
    if (lastLocationToastRef.current === message) {
      return;
    }
    lastLocationToastRef.current = message;
    toast({
      title: "位置情報を取得できませんでした",
      description: message,
      variant: "destructive",
    });
  }, [location.error, location.status, toast]);

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
    // クライアントマウント後にフラグを立て、以降は実際のサポート状況に応じたラベルへ切替。
    setMounted(true);
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
        .then(items => {
          setSuggestions(items);
        })
        .catch(error => {
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
  const distanceOptions = useMemo(
    () =>
      Array.from(new Set([...DISTANCE_PRESET_OPTIONS, state.distance]))
        .filter(value => value >= MIN_DISTANCE_KM && value <= MAX_DISTANCE_KM)
        .sort((a, b) => a - b),
    [state.distance],
  );

  const hasLocation = location.lat != null && location.lng != null;
  const isLocating = location.status === "loading";
  const canApplyManual = latInput.trim().length > 0 && lngInput.trim().length > 0;
  const coordinateLabel = hasLocation
    ? `${location.lat!.toFixed(4)}, ${location.lng!.toFixed(4)}`
    : "";
  const locationSummary = (() => {
    if (hasLocation) {
      if (location.isFallback) {
        return `デフォルト地点（${location.fallbackLabel ?? FALLBACK_LOCATION.label}）を使用中（${coordinateLabel}）`;
      }
      return `${location.mode === "auto" ? "現在地を使用中" : "手入力した地点を使用中"}（${coordinateLabel}）`;
    }
    if (!location.hasResolvedSupport) {
      return "現在地の利用可否を確認しています…";
    }
    return location.isSupported
      ? `現在地を取得するか「デフォルト地点（${FALLBACK_LOCATION.label}）」を利用できます。`
      : "この環境では位置情報を取得できません。緯度・経度を手入力してください。";
  })();

  const handleCategoryToggle = (value: string) => {
    const isSelected = state.categories.includes(value);
    if (isSelected) {
      onCategoriesChange(state.categories.filter(item => item !== value));
    } else {
      onCategoriesChange([...state.categories, value]);
    }
  };

  const handleConditionToggle = (value: string) => {
    const isSelected = state.conditions.includes(value);
    if (isSelected) {
      onConditionsChange(state.conditions.filter(item => item !== value));
    } else {
      onConditionsChange([...state.conditions, value]);
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

  const handleUseFallbackLocation = () => {
    setLatInput(FALLBACK_LOCATION.lat.toFixed(5));
    setLngInput(FALLBACK_LOCATION.lng.toFixed(5));
    setManualError(null);
    onUseFallbackLocation();
  };

  const handleClearLocation = () => {
    setLatInput("");
    setLngInput("");
    setManualError(null);
    onClearLocation();
  };

  const manualLocationDescriptionIds = manualError
    ? `${manualLocationHintId} ${manualLocationErrorId}`
    : manualLocationHintId;

  return (
    <aside className="space-y-4 lg:sticky lg:top-28 lg:max-h-[calc(100vh-7rem)] lg:space-y-6 lg:overflow-y-auto lg:pr-3">
      <form
        className="flex flex-col gap-6 rounded-3xl border border-border/80 bg-card/95 p-5 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/80 sm:p-7"
        onSubmit={event => {
          event.preventDefault();
          onSubmitSearch();
        }}
      >
        <div className="sticky top-[5.25rem] z-10 -mx-5 -mt-5 space-y-4 rounded-t-3xl border-b border-border/60 bg-card/95 px-5 pb-4 pt-5 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/80 sm:static sm:-mx-0 sm:-mt-0 sm:space-y-6 sm:border-none sm:bg-transparent sm:px-0 sm:py-0 sm:shadow-none">
          <SearchBar
            id="gym-search-keyword"
            inputProps={{
              name: "keyword",
              "aria-describedby": keywordHelpTextId,
            }}
            inputRef={keywordInputRef}
            label="キーワード"
            onChange={onKeywordChange}
            placeholder="設備やジム名で検索"
            value={state.q}
          >
            <p className="text-xs text-muted-foreground" id={keywordHelpTextId}>
              キーワードは2文字以上入力すると候補が表示されます。
            </p>
            {state.q.trim().length >= 2 ? (
              <div className="space-y-1">
                {isSuggestLoading ? (
                  <p className="text-xs text-muted-foreground">候補を検索中です…</p>
                ) : null}
                {suggestError ? <p className="text-xs text-destructive">{suggestError}</p> : null}
                {suggestions.length > 0 ? (
                  <ul className="divide-y overflow-hidden rounded-md border bg-background text-sm shadow-sm">
                    {suggestions.map(item => (
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
          </SearchBar>
          <div className="flex flex-wrap items-center justify-end gap-3">
            <Button
              aria-label="検索を実行"
              className="w-full sm:w-auto"
              disabled={isSearchLoading}
              type="submit"
            >
              {isSearchLoading ? (
                <span className="flex items-center gap-2">
                  <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
                  検索中…
                </span>
              ) : (
                "検索"
              )}
            </Button>
            <Button className="w-full sm:w-auto" onClick={onClear} type="button" variant="outline">
              条件をクリア
            </Button>
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
            onChange={event => onPrefectureChange(event.target.value)}
            value={state.prefecture}
            aria-describedby={prefectureHelpTextId}
          >
            <option value="">指定しない</option>
            {sortedPrefectures.map(prefecture => (
              <option key={prefecture.value} value={prefecture.value}>
                {prefecture.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-muted-foreground" id={prefectureHelpTextId}>
            未選択の場合は全国から検索します。
          </p>
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
            onChange={event => onCityChange(event.target.value)}
            value={state.city}
            aria-describedby={cityHelpTextId}
          >
            <option value="">指定しない</option>
            {sortedCities.map(city => (
              <option key={city.value} value={city.value}>
                {city.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-muted-foreground" id={cityHelpTextId}>
            都道府県を選択すると市区町村を絞り込めます。
          </p>
        </div>

        <fieldset className="space-y-4">
          <legend className="text-sm font-medium">設備</legend>
          {Object.entries(
            sortedCategories.reduce(
              (acc, category) => {
                const group = category.category || "その他";
                if (!acc[group]) {
                  acc[group] = [];
                }
                acc[group].push(category);
                return acc;
              },
              {} as Record<string, typeof sortedCategories>,
            ),
          ).map(([groupName, groupCategories]) => (
            <div key={groupName} className="space-y-2">
              <h4 className="text-xs font-medium text-muted-foreground">{groupName}</h4>
              <div className="flex flex-wrap gap-2">
                {groupCategories.map(category => {
                  const checked = state.categories.includes(category.value);
                  return (
                    <label
                      key={category.value}
                      className={cn(
                        "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm",
                        "focus-within:outline focus-within:outline-2 focus-within:outline-ring",
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
              </div>
            </div>
          ))}
          {sortedCategories.length === 0 ? (
            <span className="text-xs text-muted-foreground">設備が読み込み中です…</span>
          ) : null}
        </fieldset>

        <fieldset className="space-y-4">
          <legend className="text-sm font-medium">利用条件</legend>
          <div className="flex flex-wrap gap-2">
            {CONDITION_OPTIONS.map(condition => {
              const checked = state.conditions.includes(condition.value);
              return (
                <label
                  key={condition.value}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm",
                    "focus-within:outline focus-within:outline-2 focus-within:outline-ring",
                    checked
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-input bg-background",
                  )}
                >
                  <input
                    checked={checked}
                    className="sr-only"
                    onChange={() => handleConditionToggle(condition.value)}
                    type="checkbox"
                    value={condition.value}
                  />
                  <span>{condition.label}</span>
                </label>
              );
            })}
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
            onChange={event => {
              const [sort, order] = event.target.value.split(":");
              onSortChange(sort as SortOption, (order as SortOrder) ?? "asc");
            }}
            value={`${state.sort}:${state.order}`}
          >
            {SORT_SELECT_OPTIONS.map(option => {
              const disabled =
                option.requiresLocation &&
                !(location.lat != null && location.lng != null) &&
                `${state.sort}:${state.order}` !== option.value;
              return (
                <option key={option.value} disabled={disabled} value={option.value}>
                  {option.label}
                </option>
              );
            })}
          </select>
          {location.lat == null && location.lng == null ? (
            <p className="text-xs text-muted-foreground">
              位置情報が未設定のため、距離順は選択できません。
            </p>
          ) : null}
        </div>

        <section
          aria-labelledby="gym-search-location-heading"
          className="space-y-4 rounded-xl border border-dashed border-border/70 bg-muted/20 p-4"
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex min-w-0 flex-col gap-2">
              <h3 className="text-sm font-semibold" id="gym-search-location-heading">
                現在地の設定
              </h3>
              <p
                aria-live="polite"
                className="flex items-start gap-2 text-xs leading-relaxed text-muted-foreground"
                id={locationSummaryId}
              >
                {isLocating ? (
                  <Loader2 aria-hidden="true" className="mt-0.5 h-3.5 w-3.5 animate-spin" />
                ) : null}
                {location.status === "error" ? (
                  <AlertTriangle aria-hidden="true" className="mt-0.5 h-3.5 w-3.5 text-amber-500" />
                ) : null}
                <span className="break-words">{locationSummary}</span>
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                disabled={isLocating || (location.hasResolvedSupport && !location.isSupported)}
                onClick={onRequestLocation}
                size="sm"
                type="button"
              >
                {isLocating ? (
                  <span className="flex items-center gap-2">
                    <Loader2 aria-hidden="true" className="h-3.5 w-3.5 animate-spin" />
                    取得中…
                  </span>
                ) : mounted ? (
                  // マウント後は実際のサポート状況に基づいて表示
                  location.hasResolvedSupport && !location.isSupported ? (
                    "現在地は利用不可"
                  ) : (
                    "現在地を再取得"
                  )
                ) : (
                  // SSR と初回 CSR を一致させるため固定表示
                  "現在地は利用不可"
                )}
              </Button>
              <Button
                disabled={location.isFallback && location.status !== "error"}
                onClick={handleUseFallbackLocation}
                size="sm"
                type="button"
                variant="outline"
              >
                デフォルト地点を使用
              </Button>
              <Button
                disabled={!hasLocation}
                onClick={handleClearLocation}
                size="sm"
                type="button"
                variant="ghost"
              >
                位置情報をクリア
              </Button>
            </div>
          </div>
          {location.status === "error" && location.error ? (
            <div
              className="space-y-2 rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive shadow-sm"
              role="alert"
            >
              <div className="flex items-start gap-2 text-sm">
                <AlertTriangle aria-hidden="true" className="mt-0.5 h-4 w-4" />
                <span>{location.error}</span>
              </div>
              <button
                className="text-left text-xs font-medium text-primary underline-offset-4 hover:underline"
                onClick={() => {
                  keywordInputRef.current?.focus();
                  keywordInputRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
                }}
                type="button"
              >
                住所や駅名で検索する
              </button>
            </div>
          ) : null}
          <div className="space-y-3 rounded-lg border border-border/60 bg-background/80 p-3 shadow-sm">
            <p className="text-xs text-muted-foreground" id={manualLocationHintId}>
              緯度・経度を直接入力して検索範囲の中心を指定できます（例: 35.6895 / 139.6917）。
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="grid min-w-0 gap-1">
                <label className="text-xs font-medium text-muted-foreground" htmlFor="manual-lat">
                  緯度（-90〜90）
                </label>
                <input
                  aria-describedby={manualLocationDescriptionIds}
                  autoComplete="off"
                  className={cn(
                    "h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  )}
                  id="manual-lat"
                  inputMode="decimal"
                  onChange={event => {
                    setLatInput(event.target.value);
                    setManualError(null);
                  }}
                  placeholder="35.6895"
                  value={latInput}
                />
              </div>
              <div className="grid min-w-0 gap-1">
                <label className="text-xs font-medium text-muted-foreground" htmlFor="manual-lng">
                  経度（-180〜180）
                </label>
                <input
                  aria-describedby={manualLocationDescriptionIds}
                  autoComplete="off"
                  className={cn(
                    "h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  )}
                  id="manual-lng"
                  inputMode="decimal"
                  onChange={event => {
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
                <span className="break-words text-xs text-muted-foreground">
                  適用中: {coordinateLabel}
                </span>
              ) : null}
            </div>
            {manualError ? (
              <p className="text-xs text-destructive" id={manualLocationErrorId} role="alert">
                {manualError}
              </p>
            ) : null}
          </div>
        </section>

        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <label className="text-sm font-medium" htmlFor="gym-search-distance">
              検索半径（km）
            </label>
            <SearchDistanceBadge distanceKm={state.distance} />
          </div>
          <div className="grid gap-2">
            <input
              aria-describedby={distanceHelpTextId}
              aria-label="検索半径（キロメートル）"
              aria-valuemax={MAX_DISTANCE_KM}
              aria-valuemin={MIN_DISTANCE_KM}
              aria-valuenow={state.distance}
              aria-valuetext={`約${state.distance}キロメートル`}
              className={cn("hidden w-full sm:block", !hasLocation && "opacity-50")}
              disabled={!hasLocation}
              id="gym-search-distance"
              max={MAX_DISTANCE_KM}
              min={MIN_DISTANCE_KM}
              onChange={event => onDistanceChange(Number.parseInt(event.target.value, 10))}
              onInput={event =>
                onDistanceChange(Number.parseInt((event.target as HTMLInputElement).value, 10))
              }
              step={DISTANCE_STEP_KM}
              type="range"
              value={state.distance}
            />
            <select
              aria-describedby={distanceHelpTextId}
              className={cn(
                "h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm sm:hidden",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              )}
              disabled={!hasLocation}
              id="gym-search-distance-select"
              onChange={event => {
                const next = Number.parseInt(event.target.value, 10);
                if (!Number.isNaN(next)) {
                  onDistanceChange(next);
                }
              }}
              onInput={event => {
                const next = Number.parseInt((event.target as HTMLSelectElement).value, 10);
                if (!Number.isNaN(next)) {
                  onDistanceChange(next);
                }
              }}
              value={state.distance}
            >
              {distanceOptions.map(option => (
                <option key={option} value={option}>
                  半径 {option}km
                </option>
              ))}
            </select>
          </div>
          <p className="text-xs leading-relaxed text-muted-foreground" id={distanceHelpTextId}>
            {hasLocation
              ? "現在の地点から検索する範囲を調整できます。"
              : `デフォルト地点（${FALLBACK_LOCATION.label}）または現在地を設定すると距離フィルタを利用できます。`}
          </p>
        </div>
      </form>

      {metaError ? (
        <div
          aria-live="polite"
          className={cn(
            "rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm shadow-sm",
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
            "rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm shadow-sm",
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
