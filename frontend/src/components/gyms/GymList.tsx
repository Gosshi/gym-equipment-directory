import { useEffect, useRef, type ReactNode } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { GymSearchMeta, GymSummary } from "@/types/gym";

const PAGE_SIZE_OPTIONS = [10, 20, 50];

const GymListLoadingState = () => (
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

const GymListEmptyState = () => (
  <p className="rounded-md bg-muted/40 p-4 text-center text-sm text-muted-foreground">
    条件に一致するジムが見つかりませんでした。
  </p>
);

const GymListErrorState = ({ message, onRetry }: { message: string; onRetry: () => void }) => (
  <div
    className={cn(
      "flex flex-col items-center gap-4 rounded-md",
      "border border-destructive/40 bg-destructive/10 p-6 text-center",
    )}
  >
    <p className="text-sm text-destructive">{message}</p>
    <Button onClick={onRetry} type="button" variant="outline">
      もう一度試す
    </Button>
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
          {gym.prefecture ? gym.prefecture : "エリア未設定"}
          {gym.city ? ` / ${gym.city}` : null}
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
          <p className="text-sm text-muted-foreground">設備情報はまだ登録されていません。</p>
        )}
      </CardContent>
    </Card>
  </Link>
);

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
}: GymListProps) {
  const showSkeleton = isInitialLoading;
  const showEmpty = !error && !showSkeleton && gyms.length === 0;
  const isPageLoading = isLoading && !isInitialLoading;

  const limitValue = Math.max(limit, 1);
  const metaPerPage = meta.perPage > 0 ? meta.perPage : limitValue;
  const perPageValue = Math.max(metaPerPage, 1);
  const metaPage = meta.page > 0 ? meta.page : page;
  const currentPage = Math.max(metaPage, 1);
  const totalCount = meta.total > 0 ? meta.total : gyms.length;
  const totalPages =
    totalCount > 0 ? Math.max(Math.ceil(totalCount / perPageValue), currentPage) : 0;
  const rangeStart =
    totalCount === 0 ? 0 : Math.min((currentPage - 1) * perPageValue + 1, totalCount);
  const rangeEnd = totalCount === 0 ? 0 : Math.min(currentPage * perPageValue, totalCount);

  const resultSectionRef = useRef<HTMLElement | null>(null);
  const previousPageRef = useRef(page);

  useEffect(() => {
    if (previousPageRef.current !== page && resultSectionRef.current) {
      resultSectionRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
      resultSectionRef.current.focus();
    }
    previousPageRef.current = page;
  }, [page]);

  let content: ReactNode;
  if (error) {
    content = <GymListErrorState message={error} onRetry={onRetry} />;
  } else if (showSkeleton) {
    content = <GymListLoadingState />;
  } else if (showEmpty) {
    content = <GymListEmptyState />;
  } else {
    content = (
      <div className={cn("grid gap-4", "sm:grid-cols-2", "xl:grid-cols-3")}> 
        {gyms.map((gym) => (
          <GymCard key={gym.id} gym={gym} />
        ))}
      </div>
    );
  }

  const showPagination = !error && totalCount > 0;
  const perPageOptions = Array.from(new Set([...PAGE_SIZE_OPTIONS, perPageValue])).sort(
    (a, b) => a - b,
  );
  const isPrevDisabled = isPageLoading || !meta.hasPrev;
  const isNextDisabled = isPageLoading || !meta.hasNext;

  const handlePrev = () => {
    if (isPrevDisabled) {
      return;
    }
    onPageChange(Math.max(currentPage - 1, 1));
  };

  const handleNext = () => {
    if (isNextDisabled) {
      return;
    }
    onPageChange(currentPage + 1);
  };

  return (
    <section
      aria-busy={isLoading}
      aria-labelledby="gym-search-results-heading"
      aria-live="polite"
      className="rounded-lg border bg-background p-6 shadow-sm"
      ref={resultSectionRef}
      tabIndex={-1}
    >
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4">
        <div>
          <h2 className="text-xl font-semibold" id="gym-search-results-heading">
            検索結果
          </h2>
          <p className="text-sm text-muted-foreground">
            {totalCount} 件のジムが見つかりました。
            {totalPages > 1 ? `（全 ${totalPages} ページ）` : ""}
          </p>
        </div>
      </div>

      {content}

      {showPagination ? (
        <div className="mt-8 border-t pt-4">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <p aria-live="polite" className="text-sm text-muted-foreground">
              {`${rangeStart}–${rangeEnd} / ${totalCount}件`}
            </p>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
              <div className="flex items-center gap-2">
                <label className="text-sm text-muted-foreground" htmlFor="gym-search-limit">
                  表示件数
                </label>
                <select
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
              <div className="flex items-center gap-2">
                <Button
                  aria-label="前のページ"
                  disabled={isPrevDisabled}
                  onClick={handlePrev}
                  type="button"
                  variant="outline"
                >
                  前へ
                </Button>
                <Button
                  aria-label="次のページ"
                  disabled={isNextDisabled}
                  onClick={handleNext}
                  type="button"
                >
                  次へ
                </Button>
              </div>
            </div>
          </div>
          {isPageLoading ? (
            <div className="mt-3 text-sm text-muted-foreground" role="status">
              読み込み中...
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
