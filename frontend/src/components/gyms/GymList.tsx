import { useEffect, useId, useRef, type ReactNode } from "react";

import { GymCard } from "@/components/gyms/GymCard";
import { Pagination } from "@/components/gyms/Pagination";
import { SearchEmpty } from "@/components/search/SearchEmpty";
import { SearchError } from "@/components/search/SearchError";
import { SearchSkeleton } from "@/components/search/SearchSkeleton";
import { useSearchResultState } from "@/components/search/useSearchResultState";
import { cn } from "@/lib/utils";
import type { GymSearchMeta, GymSummary } from "@/types/gym";

const PAGE_SIZE_OPTIONS = [10, 20, 50];

type GymListProps = {
  gyms: GymSummary[];
  meta: GymSearchMeta;
  page: number;
  limit: number;
  isLoading: boolean;
  isInitialLoading: boolean;
  error: string | null;
  onRetry: () => void;
  onPageChange: (page: number) => void;
  onLimitChange: (limit: number) => void;
  onClearFilters?: () => void;
};

export function GymList({
  gyms,
  meta,
  page,
  limit,
  isLoading,
  isInitialLoading,
  error,
  onRetry,
  onPageChange,
  onLimitChange,
  onClearFilters,
}: GymListProps) {
  const resultState = useSearchResultState({ isLoading, error, items: gyms });
  const isPageLoading = isLoading && !isInitialLoading;

  const limitValue = Math.max(limit, 1);
  const metaPerPage = meta.perPage > 0 ? meta.perPage : limitValue;
  const perPageValue = Math.max(metaPerPage, 1);
  const metaPage = meta.page > 0 ? meta.page : page;
  const currentPage = Math.max(metaPage, 1);
  const hasExactTotal = typeof meta.total === "number" && meta.total >= 0;
  const totalCount = hasExactTotal ? meta.total : gyms.length;
  const totalPages =
    hasExactTotal && (totalCount ?? 0) > 0
      ? Math.max(Math.ceil((totalCount as number) / perPageValue), currentPage)
      : null;
  const hasMore = Boolean(meta.hasMore ?? meta.hasNext);
  const hasResults = gyms.length > 0;
  const baseRangeStart = hasResults ? (currentPage - 1) * perPageValue + 1 : 0;
  const baseRangeEnd = hasResults ? baseRangeStart + gyms.length - 1 : 0;
  const safeTotalForRange = typeof totalCount === "number" ? totalCount : 0;
  const rangeStart = hasExactTotal
    ? Math.min(baseRangeStart, safeTotalForRange)
    : baseRangeStart;
  const rangeEnd = hasExactTotal ? Math.min(baseRangeEnd, safeTotalForRange) : baseRangeEnd;
  const totalLabel = hasExactTotal
    ? `${totalCount}件`
    : `${rangeEnd}${meta.hasNext ? "+" : ""}件`;
  const perPageOptions = Array.from(new Set([...PAGE_SIZE_OPTIONS, perPageValue])).sort(
    (a, b) => a - b,
  );
  const skeletonCount = Math.max(perPageValue, gyms.length || 0);
  const paginationTotalPages = totalPages ?? Math.max(currentPage, 1);

  const resultSectionRef = useRef<HTMLElement | null>(null);
  const previousPageRef = useRef(page);
  const headerDescriptionId = useId();
  const paginationSummaryId = useId();

  useEffect(() => {
    if (previousPageRef.current !== page && resultSectionRef.current) {
      resultSectionRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
      resultSectionRef.current.focus();
    }
    previousPageRef.current = page;
  }, [page]);

  let content: ReactNode;
  switch (resultState.status) {
    case "error":
      content = <SearchError message={error} onRetry={onRetry} />;
      break;
    case "loading":
      content = <SearchSkeleton count={skeletonCount} />;
      break;
    case "empty":
      content = <SearchEmpty onResetFilters={onClearFilters} />;
      break;
    default:
      content = (
        <div
          className={cn(
            "grid gap-4",
            "sm:grid-cols-2 sm:gap-6",
            "lg:grid-cols-2",
            "xl:grid-cols-3 xl:gap-7",
            "2xl:grid-cols-4",
          )}
        >
          {gyms.map((gym) => (
            <GymCard key={gym.id} gym={gym} />
          ))}
        </div>
      );
      break;
  }

  const paginationSummary = resultState.isSuccess
    ? `${rangeStart}–${rangeEnd} / ${totalLabel}`
    : resultState.isLoading
    ? "検索結果を読み込み中です…"
    : "0件";

  const showPagination =
    resultState.isSuccess && ((totalCount ?? 0) > 0 || hasMore || currentPage > 1);

  const headerDescription = (() => {
    if (resultState.isLoading) {
      return "検索結果を読み込み中です…";
    }
    if (resultState.isError) {
      return "検索結果の取得に失敗しました。";
    }
    if (resultState.isEmpty) {
      return "条件に一致するジムは見つかりませんでした。";
    }
    return `${totalLabel.replace("件", "件のジムが見つかりました。")}`.concat(
      totalPages ? `（全 ${totalPages} ページ）` : "",
    );
  })();

  return (
    <section
      aria-busy={resultState.isLoading}
      aria-describedby={headerDescriptionId}
      aria-labelledby="gym-search-results-heading"
      aria-live="polite"
      className="rounded-2xl border border-border/80 bg-card/95 p-6 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/80 sm:p-8"
      ref={resultSectionRef}
      tabIndex={-1}
    >
      <div className="flex flex-col gap-4 pb-6 sm:flex-row sm:items-end sm:justify-between sm:gap-6">
        <div className="space-y-1.5">
          <h2 className="text-2xl font-semibold tracking-tight" id="gym-search-results-heading">
            検索結果
          </h2>
          <p className="text-sm leading-relaxed text-muted-foreground" id={headerDescriptionId}>
            {headerDescription}
          </p>
        </div>
        {resultState.isSuccess ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="font-medium text-foreground">{totalLabel}</span>
            <span className="hidden sm:inline">が見つかりました</span>
          </div>
        ) : null}
      </div>

      {content}

      {showPagination ? (
        <div className="mt-10 border-t border-border/70 pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <p aria-live="polite" className="text-sm text-muted-foreground" id={paginationSummaryId}>
              {paginationSummary}
            </p>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end sm:gap-4">
              <div className="flex items-center gap-2">
                <label className="text-sm text-muted-foreground" htmlFor="gym-search-limit">
                  表示件数
                </label>
                <select
                  aria-label="1ページあたりの表示件数を変更"
                  className={cn(
                    "h-9 rounded-md border border-input bg-background px-2 text-sm shadow-sm",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  )}
                  id="gym-search-limit"
                  onChange={(event) => {
                    const next = Number.parseInt(event.target.value, 10);
                    if (!Number.isNaN(next)) {
                      onLimitChange(next);
                    }
                  }}
                  value={perPageValue}
                >
                  {perPageOptions.map((option) => (
                    <option key={option} value={option}>
                      {option} 件
                    </option>
                  ))}
                </select>
              </div>
              <Pagination
                ariaDescribedBy={paginationSummaryId}
                currentPage={currentPage}
                totalPages={paginationTotalPages}
                hasNextPage={hasMore}
                onChange={onPageChange}
                isLoading={isPageLoading}
              />
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
