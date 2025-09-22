import { useEffect, useRef, type ReactNode } from "react";
import Link from "next/link";

import { InfiniteLoader } from "@/components/gyms/InfiniteLoader";
import { Pagination } from "@/components/gyms/Pagination";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { GymSearchMeta, GymSummary } from "@/types/gym";

const PAGE_SIZE_OPTIONS = [20, 40, 60];

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
  onLoadMore: () => void;
  enableInfiniteScroll?: boolean;
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
  onLoadMore,
  enableInfiniteScroll = true,
}: GymListProps) {
  const showSkeleton = isInitialLoading;
  const showEmpty = !error && !showSkeleton && gyms.length === 0;
  const isAppending = isLoading && !isInitialLoading;
  const limitValue = Math.max(limit, 1);
  const totalFromMeta = meta.total > 0 ? Math.ceil(meta.total / limitValue) : 0;
  const totalFromCount = gyms.length > 0 ? Math.ceil(gyms.length / limitValue) : 0;
  const totalPages = Math.max(1, totalFromMeta, totalFromCount, page + (meta.hasNext ? 1 : 0));
  const aggregated = gyms.length > limitValue;
  const totalCount = meta.total > 0 ? meta.total : gyms.length;
  const displayedStart = gyms.length === 0 ? 0 : aggregated || meta.total === 0 ? 1 : (page - 1) * limit + 1;
  const displayedEnd =
    gyms.length === 0
      ? 0
      : aggregated
        ? meta.total > 0
          ? Math.min(gyms.length, meta.total)
          : gyms.length
        : meta.total > 0
          ? Math.min(page * limit, meta.total)
          : gyms.length;

  const resultSectionRef = useRef<HTMLElement | null>(null);
  const previousPageRef = useRef(page);

  useEffect(() => {
    if (previousPageRef.current !== page && resultSectionRef.current) {
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

  const showPagination = !error && (totalPages > 1 || meta.hasNext || page > 1);

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
            onChange={(event) => onLimitChange(Number.parseInt(event.target.value, 10))}
            value={limit}
          >
            {PAGE_SIZE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option} 件
              </option>
            ))}
          </select>
        </div>
      </div>

      {content}

      {!error && !showEmpty ? (
        <div className="mt-4 flex flex-col gap-3 text-sm text-muted-foreground">
          <span>
            {totalCount} 件中 {displayedStart}-{displayedEnd} 件を表示
          </span>
          {enableInfiniteScroll && meta.hasNext ? (
            <span className="text-xs text-muted-foreground">
              下までスクロールすると自動で次のページを読み込みます。
            </span>
          ) : null}
        </div>
      ) : null}

      {isAppending ? (
        <div className="mt-4 flex justify-center text-sm text-muted-foreground">
          <span>読み込み中...</span>
        </div>
      ) : null}

      {showPagination ? (
        <div className="mt-8">
          <Pagination
            currentPage={page}
            hasNextPage={meta.hasNext}
            isLoading={isLoading}
            onChange={onPageChange}
            totalPages={totalPages}
          />
        </div>
      ) : null}

      {enableInfiniteScroll && !error && gyms.length > 0 ? (
        <InfiniteLoader
          enabled={enableInfiniteScroll}
          hasNextPage={meta.hasNext}
          isLoading={isLoading}
          onLoadMore={onLoadMore}
        />
      ) : null}
    </section>
  );
}
